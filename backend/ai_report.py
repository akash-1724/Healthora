import csv
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from ai_nl2sql import build_graph, clear_store, execute_with_retry, generate_sql, get_rag_stats, introspect_database, load_store, run_pipeline
from audit import log_action
from database import get_db
from deps import get_current_user, require_permission
from models import User

router = APIRouter(prefix="/api/ai-report", tags=["ai-report"])

_SCHEMA = None
_GRAPH = None

REPORT_STORE_PATH = Path(__file__).with_name("ai_reports_store.json")
REPORT_FILES_DIR = Path(__file__).with_name("generated_reports")


class QueryRequest(BaseModel):
    question: str


class DownloadRequest(BaseModel):
    format: str


class QueryResponse(BaseModel):
    question: str
    sql: str
    columns: list[str]
    rows: list[list]
    count: int
    success: bool
    cached: bool = False


def _ensure_loaded() -> tuple[dict, object]:
    global _SCHEMA, _GRAPH
    if _SCHEMA is None:
        _SCHEMA = introspect_database()
        _GRAPH = build_graph(_SCHEMA)
    assert _SCHEMA is not None
    assert _GRAPH is not None
    return _SCHEMA, _GRAPH


def _is_cached(question: str, sql: str) -> bool:
    for entry in load_store():
        if entry.get("query", "").lower() == question.lower() and entry.get("sql") == sql:
            return True
    return False


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _is_numeric(value) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_iso_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "")).date()
        except ValueError:
            return None
    return None


def _pick_metric_column(columns: list[str], rows: list[dict]) -> str | None:
    preferred = ["revenue", "amount", "total", "sales", "quantity", "count", "price"]
    numeric_columns = []
    for col in columns:
        if any(_is_numeric(row.get(col)) for row in rows):
            numeric_columns.append(col)
    if not numeric_columns:
        return None

    for key in preferred:
        for col in numeric_columns:
            if key in col.lower():
                return col
    return numeric_columns[0]


def _pick_date_column(columns: list[str], rows: list[dict]) -> str | None:
    preferred = ["date", "time", "month", "year", "created", "dispensed", "ordered"]
    candidates = []
    for col in columns:
        if any(_parse_iso_date(row.get(col)) for row in rows):
            candidates.append(col)
    if not candidates:
        return None
    for key in preferred:
        for col in candidates:
            if key in col.lower():
                return col
    return candidates[0]


def _build_charts(columns: list[str], rows: list[dict]) -> list[dict]:
    charts = []
    if not rows:
        return charts

    metric = _pick_metric_column(columns, rows)
    date_col = _pick_date_column(columns, rows)

    if metric and date_col:
        monthly = {}
        for row in rows:
            parsed = _parse_iso_date(row.get(date_col))
            value = row.get(metric)
            if not parsed:
                continue
            bucket = parsed.strftime("%Y-%m")
            numeric_value = _to_float(value)
            if numeric_value is None:
                continue
            monthly[bucket] = monthly.get(bucket, 0.0) + numeric_value
        if monthly:
            labels = sorted(monthly.keys())
            charts.append(
                {
                    "type": "line",
                    "title": f"Monthly trend of {metric}",
                    "labels": labels,
                    "series": [{"name": metric, "values": [round(monthly[label], 2) for label in labels]}],
                }
            )

    if metric:
        category = None
        for col in columns:
            if col == metric:
                continue
            if any(isinstance(row.get(col), str) and row.get(col) for row in rows):
                category = col
                break
        if category:
            grouped = {}
            for row in rows:
                key = str(row.get(category) or "Unknown")
                value = row.get(metric)
                numeric_value = _to_float(value)
                if numeric_value is None:
                    continue
                grouped[key] = grouped.get(key, 0.0) + numeric_value
            if grouped:
                top = sorted(grouped.items(), key=lambda pair: pair[1], reverse=True)[:8]
                charts.append(
                    {
                        "type": "bar",
                        "title": f"Top {category} by {metric}",
                        "labels": [name for name, _ in top],
                        "series": [{"name": metric, "values": [round(val, 2) for _, val in top]}],
                    }
                )

    return charts


def _build_kpis(columns: list[str], rows: list[dict]) -> list[dict]:
    kpis = [{"label": "Rows", "value": len(rows)}]
    metric = _pick_metric_column(columns, rows)
    if metric:
        values = []
        for row in rows:
            value = row.get(metric)
            numeric_value = _to_float(value)
            if numeric_value is None:
                continue
            values.append(numeric_value)
        if values:
            kpis.extend(
                [
                    {"label": f"Total {metric}", "value": round(sum(values), 2)},
                    {"label": f"Average {metric}", "value": round(mean(values), 2)},
                    {"label": f"Peak {metric}", "value": round(max(values), 2)},
                ]
            )
    return kpis


def _build_summary(question: str, rows: list[dict], kpis: list[dict], charts: list[dict]) -> str:
    lines = []
    lines.append(f"Report generated for query: '{question}'.")
    lines.append(f"The dataset contains {len(rows)} rows after applying current filters.")
    if rows and all((r.get("units_sold") == 0 or r.get("units_sold") is None) for r in rows if isinstance(r, dict)):
        lines.append("No sales were recorded for the selected filter window, so totals are zero.")

    total_kpi = next((k for k in kpis if str(k["label"]).lower().startswith("total ")), None)
    if total_kpi:
        lines.append(f"The aggregate {total_kpi['label'].split(' ', 1)[1]} is {total_kpi['value']}.")

    if charts:
        lines.append(f"Preview includes {len(charts)} chart(s) for trend and distribution analysis.")

    return " ".join(lines)


def _load_report_store() -> dict:
    if not REPORT_STORE_PATH.exists():
        return {}
    try:
        return json.loads(REPORT_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_report_store(store: dict) -> None:
    REPORT_STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _save_report_payload(payload: dict) -> None:
    store = _load_report_store()
    store[payload["report_id"]] = payload
    _save_report_store(store)


def _get_report_payload(report_id: str) -> dict:
    store = _load_report_store()
    payload = store.get(report_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Report not found")
    return payload


def _build_report_payload(question: str, sql: str, columns: list[str], rows: list[tuple], cached: bool) -> dict:
    safe_rows = [{col: _json_safe(row[idx]) for idx, col in enumerate(columns)} for row in rows]
    kpis = _build_kpis(columns, safe_rows)
    charts = _build_charts(columns, safe_rows)
    summary = _build_summary(question, safe_rows, kpis, charts)

    report_id = str(uuid4())
    return {
        "report_id": report_id,
        "title": f"AI Report - {question[:80]}",
        "question": question,
        "generated_at": datetime.utcnow().isoformat(),
        "sql": sql,
        "count": len(safe_rows),
        "cached": cached,
        "summary_text": summary,
        "kpis": kpis,
        "charts": charts,
        "columns": columns,
        "rows": [[_json_safe(value) for value in row] for row in rows],
        "formats": ["pdf", "csv"],
    }


def _export_csv(payload: dict) -> Path:
    REPORT_FILES_DIR.mkdir(parents=True, exist_ok=True)
    file_path = REPORT_FILES_DIR / f"{payload['report_id']}.csv"
    with file_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(payload.get("columns", []))
        for row in payload.get("rows", []):
            writer.writerow(row)
    return file_path


def _pdf_line(pdf: canvas.Canvas, text_line: str, x: int, y: int) -> int:
    if y < 60:
        pdf.showPage()
        pdf.setFont("Helvetica", 10)
        return 800
    pdf.drawString(x, y, text_line)
    return y - 14


def _export_pdf(payload: dict) -> Path:
    REPORT_FILES_DIR.mkdir(parents=True, exist_ok=True)
    file_path = REPORT_FILES_DIR / f"{payload['report_id']}.pdf"

    pdf = canvas.Canvas(str(file_path), pagesize=A4)
    pdf.setTitle(payload.get("title", "AI Report"))
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, 810, payload.get("title", "AI Report"))

    pdf.setFont("Helvetica", 10)
    y = 790
    y = _pdf_line(pdf, f"Generated: {payload.get('generated_at', '')}", 40, y)
    y = _pdf_line(pdf, f"Question: {payload.get('question', '')}", 40, y)
    y = _pdf_line(pdf, f"Rows: {payload.get('count', 0)}", 40, y)
    y -= 10
    y = _pdf_line(pdf, "Executive Summary:", 40, y)
    for part in str(payload.get("summary_text", "")).split("."):
        part = part.strip()
        if part:
            y = _pdf_line(pdf, f"- {part}.", 50, y)

    y -= 6
    y = _pdf_line(pdf, "KPIs:", 40, y)
    for kpi in payload.get("kpis", []):
        y = _pdf_line(pdf, f"- {kpi.get('label')}: {kpi.get('value')}", 50, y)

    y -= 6
    y = _pdf_line(pdf, "Charts in preview:", 40, y)
    for chart in payload.get("charts", []):
        y = _pdf_line(pdf, f"- {chart.get('title', 'Chart')}", 50, y)

    y -= 10
    y = _pdf_line(pdf, "Result sample:", 40, y)
    columns = payload.get("columns", [])
    rows = payload.get("rows", [])[:20]
    if columns:
        y = _pdf_line(pdf, " | ".join(str(c) for c in columns), 50, y)
        for row in rows:
            row_text = " | ".join(str(v) for v in row)
            y = _pdf_line(pdf, row_text[:170], 50, y)

    pdf.save()
    return file_path


@router.get("", dependencies=[Depends(require_permission("view_ai_report"))])
def ai_report_status():
    schema, _ = _ensure_loaded()
    return {"message": "AI report ready", "tables": len(schema), "formats": ["pdf", "csv"]}


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(require_permission("view_ai_report"))])
def ai_report_query(payload: QueryRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    schema, graph = _ensure_loaded()
    best_path = run_pipeline(question, schema, graph)
    if not best_path:
        raise HTTPException(status_code=422, detail="Could not map this question to database tables")

    try:
        sql = generate_sql(question, best_path, schema, graph)
        cached = _is_cached(question, sql)
        result = execute_with_retry(db, question, sql, schema, best_path)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI query failed: {exc}") from exc

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    log_action(
        db,
        "ai_query",
        actor_user_id=current_user.user_id,
        target_table="ai_report",
        detail={"question": question, "rows": result["count"], "cached": cached},
    )
    db.commit()

    return QueryResponse(
        question=question,
        sql=result["sql"],
        columns=result["columns"],
        rows=[[_json_safe(value) for value in row] for row in result["rows"]],
        count=result["count"],
        success=True,
        cached=cached,
    )


@router.post("/generate-report", dependencies=[Depends(require_permission("view_ai_report"))])
def generate_report(payload: QueryRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    schema, graph = _ensure_loaded()
    best_path = run_pipeline(question, schema, graph)
    if not best_path:
        raise HTTPException(status_code=422, detail="Could not map this question to database tables")

    try:
        sql = generate_sql(question, best_path, schema, graph)
        cached = _is_cached(question, sql)
        result = execute_with_retry(db, question, sql, schema, best_path)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI report generation failed: {exc}") from exc

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    report_payload = _build_report_payload(
        question=question,
        sql=result["sql"],
        columns=result["columns"],
        rows=result["rows"],
        cached=cached,
    )
    _save_report_payload(report_payload)

    log_action(
        db,
        "ai_generate_report",
        actor_user_id=current_user.user_id,
        target_table="ai_report",
        detail={"question": question, "report_id": report_payload["report_id"], "rows": report_payload["count"]},
    )
    db.commit()
    return report_payload


@router.get("/{report_id}/preview", dependencies=[Depends(require_permission("view_ai_report"))])
def preview_report(report_id: str):
    return _get_report_payload(report_id)


@router.post("/{report_id}/download", dependencies=[Depends(require_permission("view_ai_report"))])
def download_report(report_id: str, payload: DownloadRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = _get_report_payload(report_id)
    fmt = payload.format.lower().strip()
    if fmt not in {"pdf", "csv"}:
        raise HTTPException(status_code=400, detail="Only pdf and csv are supported")

    if fmt == "pdf":
        file_path = _export_pdf(report)
        media_type = "application/pdf"
    else:
        file_path = _export_csv(report)
        media_type = "text/csv"

    log_action(
        db,
        "ai_download_report",
        actor_user_id=current_user.user_id,
        target_table="ai_report",
        detail={"report_id": report_id, "format": fmt},
    )
    db.commit()
    return FileResponse(path=str(file_path), filename=file_path.name, media_type=media_type)


@router.get("/rag/stats", dependencies=[Depends(require_permission("view_ai_report"))])
def ai_rag_stats():
    return get_rag_stats()


@router.delete("/rag/clear", dependencies=[Depends(require_permission("manage_users"))])
def ai_rag_clear():
    clear_store()
    return {"message": "RAG store cleared"}

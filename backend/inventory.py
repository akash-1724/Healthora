import csv
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from audit import log_action
from database import get_db
from deps import get_current_user, require_permission
from models import Drug, DrugBatch, Patient, Supplier, User
from schemas import (
    DrugBatchCreate,
    DrugBatchRead,
    DrugCreate,
    DrugRead,
    DrugUpdate,
    InventoryUpdate,
    PatientCreate,
    PatientRead,
    PatientUpdate,
)

router = APIRouter(prefix="/api", tags=["inventory"])


REQUIRED_BULK_COLUMNS = {
    "drug_name",
    "batch_no",
    "expiry_date",
    "purchase_price",
    "selling_price",
    "quantity_available",
}


def _normalize_row_keys(row: dict[str, str]) -> dict[str, str]:
    normalized = {}
    for key, value in row.items():
        norm = (key or "").strip().lower().replace(" ", "_")
        normalized[norm] = (value or "").strip()
    return normalized


def _parse_date(value: str) -> date:
    value = value.strip()
    if value.replace(".", "", 1).isdigit():
        serial = int(float(value))
        return date(1899, 12, 30) + timedelta(days=serial)
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date '{value}'. Use YYYY-MM-DD")


def _parse_csv(content: bytes) -> list[dict[str, str]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        return []
    return [_normalize_row_keys(row) for row in reader]


def _xlsx_shared_strings(archive: ZipFile) -> list[str]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join((t.text or "") for t in item.findall(".//m:t", ns)) for item in root.findall("m:si", ns)]


def _parse_xlsx(content: bytes) -> list[dict[str, str]]:
    ns = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    with ZipFile(BytesIO(content)) as archive:
        shared = _xlsx_shared_strings(archive)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {node.attrib["Id"]: node.attrib["Target"] for node in rels}
        sheet = workbook.find("m:sheets/m:sheet", ns)
        if sheet is None:
            return []
        rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        target = rel_map[rid].lstrip("/")
        sheet_path = target if target.startswith("xl/") else f"xl/{target}"
        root = ET.fromstring(archive.read(sheet_path))

        rows: list[list[str]] = []
        for row in root.findall(".//m:sheetData/m:row", ns):
            values: list[str] = []
            for cell in row.findall("m:c", ns):
                node = cell.find("m:v", ns)
                if node is None:
                    values.append("")
                    continue
                raw = node.text or ""
                if cell.attrib.get("t") == "s":
                    idx = int(raw) if raw else 0
                    values.append(shared[idx] if idx < len(shared) else "")
                else:
                    values.append(raw)
            if any(values):
                rows.append(values)

    if not rows:
        return []
    headers = [h.strip().lower().replace(" ", "_") for h in rows[0]]
    out: list[dict[str, str]] = []
    for row in rows[1:]:
        row_map = {}
        for idx, head in enumerate(headers):
            if not head:
                continue
            row_map[head] = row[idx].strip() if idx < len(row) else ""
        out.append(row_map)
    return out


def to_batch_read(batch: DrugBatch) -> DrugBatchRead:
    return DrugBatchRead(
        batch_id=batch.batch_id,
        drug_id=batch.drug_id,
        drug_name=batch.drug.drug_name,
        batch_no=batch.batch_no,
        expiry_date=batch.expiry_date,
        purchase_price=float(batch.purchase_price),
        selling_price=float(batch.selling_price),
        quantity_available=batch.quantity_available,
        is_expired=batch.is_expired,
        supplier_id=batch.supplier_id,
        supplier_name=batch.supplier.name if batch.supplier else None,
    )


def to_patient_read(patient: Patient, creator_username: str | None = None) -> PatientRead:
    return PatientRead(
        patient_id=patient.patient_id,
        name=patient.name,
        address=patient.address,
        gender=patient.gender,
        contact=patient.contact,
        dob=patient.dob,
        blood_group=patient.blood_group,
        created_by_user_id=patient.created_by_user_id,
        created_by=creator_username,
        created_at=patient.created_at,
        is_archived=patient.is_archived,
    )


def to_drug_read(drug: Drug, total_quantity: int = 0, active_batches: int = 0) -> DrugRead:
    return DrugRead(
        drug_id=drug.drug_id,
        drug_name=drug.drug_name,
        generic_name=drug.generic_name,
        formulation=drug.formulation,
        strength=drug.strength,
        schedule_type=drug.schedule_type,
        is_active=drug.is_active,
        low_stock_threshold=drug.low_stock_threshold,
        total_quantity=total_quantity,
        active_batches=active_batches,
    )


@router.get("/inventory", response_model=list[DrugBatchRead], dependencies=[Depends(require_permission("view_inventory"))])
def get_inventory(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    batches = db.query(DrugBatch).join(Drug).order_by(DrugBatch.batch_id.asc()).offset(skip).limit(limit).all()
    return [to_batch_read(batch) for batch in batches]


@router.get("/drugs", response_model=list[DrugRead], dependencies=[Depends(require_permission("view_drugs"))])
def list_drugs(db: Session = Depends(get_db)):
    drugs = db.query(Drug).order_by(Drug.drug_id.asc()).all()
    batches = db.query(DrugBatch).all()
    stats: dict[int, tuple[int, int]] = {}
    for batch in batches:
        total_qty, active_count = stats.get(batch.drug_id, (0, 0))
        total_qty += batch.quantity_available
        if not batch.is_expired and batch.quantity_available > 0:
            active_count += 1
        stats[batch.drug_id] = (total_qty, active_count)
    return [to_drug_read(drug, *(stats.get(drug.drug_id, (0, 0)))) for drug in drugs]


@router.post("/drugs", response_model=DrugRead, dependencies=[Depends(require_permission("add_drug"))])
def add_drug(payload: DrugCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    drug = Drug(
        drug_name=payload.drug_name,
        generic_name=payload.generic_name,
        formulation=payload.formulation,
        strength=payload.strength,
        schedule_type=payload.schedule_type,
        low_stock_threshold=payload.low_stock_threshold,
        is_active=True,
    )
    db.add(drug)
    db.flush()
    log_action(db, "add_drug", actor_user_id=current_user.user_id, target_table="drugs", target_id=drug.drug_id, detail={"drug_name": drug.drug_name})
    db.commit()
    db.refresh(drug)
    return to_drug_read(drug)


@router.put("/drugs/{drug_id}", response_model=DrugRead, dependencies=[Depends(require_permission("add_drug"))])
def update_drug(drug_id: int, payload: DrugUpdate, db: Session = Depends(get_db)):
    drug = db.query(Drug).filter(Drug.drug_id == drug_id).first()
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")

    if payload.drug_name is not None:
        drug.drug_name = payload.drug_name
    if payload.generic_name is not None:
        drug.generic_name = payload.generic_name
    if payload.formulation is not None:
        drug.formulation = payload.formulation
    if payload.strength is not None:
        drug.strength = payload.strength
    if payload.schedule_type is not None:
        drug.schedule_type = payload.schedule_type
    if payload.low_stock_threshold is not None:
        drug.low_stock_threshold = payload.low_stock_threshold
    if payload.is_active is not None:
        drug.is_active = payload.is_active

    db.commit()
    db.refresh(drug)
    related = db.query(DrugBatch).filter(DrugBatch.drug_id == drug.drug_id).all()
    total_qty = sum(row.quantity_available for row in related)
    active_count = sum(1 for row in related if not row.is_expired and row.quantity_available > 0)
    return to_drug_read(drug, total_qty, active_count)


@router.patch("/drugs/{drug_id}/disable", response_model=DrugRead, dependencies=[Depends(require_permission("add_drug"))])
def disable_drug(drug_id: int, db: Session = Depends(get_db)):
    drug = db.query(Drug).filter(Drug.drug_id == drug_id).first()
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    drug.is_active = False
    db.commit()
    db.refresh(drug)
    related = db.query(DrugBatch).filter(DrugBatch.drug_id == drug.drug_id).all()
    total_qty = sum(row.quantity_available for row in related)
    active_count = sum(1 for row in related if not row.is_expired and row.quantity_available > 0)
    return to_drug_read(drug, total_qty, active_count)


@router.post("/drug-batches", response_model=DrugBatchRead, dependencies=[Depends(require_permission("add_batch"))])
def add_batch(payload: DrugBatchCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    drug = db.query(Drug).filter(Drug.drug_id == payload.drug_id).first()
    if not drug:
        raise HTTPException(status_code=400, detail="Invalid drug_id")

    exists = db.query(DrugBatch).filter(DrugBatch.batch_no == payload.batch_no).first()
    if exists:
        raise HTTPException(status_code=400, detail="batch_no already exists")

    batch = DrugBatch(
        drug_id=payload.drug_id,
        batch_no=payload.batch_no,
        expiry_date=payload.expiry_date,
        purchase_price=payload.purchase_price,
        selling_price=payload.selling_price,
        quantity_available=payload.quantity_available,
        supplier_id=payload.supplier_id,
        is_expired=False,
    )
    db.add(batch)
    db.flush()
    log_action(db, "add_batch", actor_user_id=current_user.user_id, target_table="drug_batches", target_id=batch.batch_id, detail={"drug_id": payload.drug_id, "batch_no": payload.batch_no})
    db.commit()
    db.refresh(batch)
    return to_batch_read(batch)


@router.post("/drug-batches/bulk-upload", dependencies=[Depends(require_permission("add_batch"))])
async def bulk_upload_batches(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = (file.filename or "").lower()
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if name.endswith(".csv"):
        rows = _parse_csv(content)
    elif name.endswith(".xlsx"):
        try:
            rows = _parse_xlsx(content)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid XLSX format: {exc}") from exc
    else:
        raise HTTPException(status_code=400, detail="Only .csv or .xlsx files are supported")

    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found")

    missing_columns = REQUIRED_BULK_COLUMNS - set(rows[0].keys())
    if missing_columns:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(sorted(missing_columns))}")

    created_batches = 0
    created_drugs = 0
    created_suppliers = 0
    errors: list[dict[str, str]] = []
    seen_batch_nos: set[str] = set()

    for idx, raw in enumerate(rows, start=2):
        try:
            drug_name = raw.get("drug_name", "").strip()
            batch_no = raw.get("batch_no", "").strip()
            expiry_raw = raw.get("expiry_date", "").strip()
            purchase_raw = raw.get("purchase_price", "").strip()
            selling_raw = raw.get("selling_price", "").strip()
            qty_raw = raw.get("quantity_available", "").strip()

            if not drug_name:
                raise ValueError("drug_name is required")
            if not batch_no:
                raise ValueError("batch_no is required")
            if batch_no in seen_batch_nos:
                raise ValueError("duplicate batch_no in file")
            seen_batch_nos.add(batch_no)

            existing_batch = db.query(DrugBatch).filter(DrugBatch.batch_no == batch_no).first()
            if existing_batch:
                raise ValueError("batch_no already exists")

            expiry_date = _parse_date(expiry_raw)
            purchase_price = float(purchase_raw)
            selling_price = float(selling_raw)
            quantity_available = int(float(qty_raw))
            if purchase_price < 0 or selling_price < 0 or quantity_available < 0:
                raise ValueError("price/quantity cannot be negative")

            drug = db.query(Drug).filter(Drug.drug_name.ilike(drug_name)).first()
            if not drug:
                drug = Drug(
                    drug_name=drug_name,
                    generic_name=raw.get("generic_name") or None,
                    formulation=raw.get("formulation") or "Tablet",
                    strength=raw.get("strength") or None,
                    schedule_type=raw.get("schedule_type") or "OTC",
                    low_stock_threshold=int(raw.get("low_stock_threshold") or 50),
                    is_active=True,
                )
                db.add(drug)
                db.flush()
                created_drugs += 1

            supplier_id: int | None = None
            supplier_id_raw = raw.get("supplier_id", "").strip()
            supplier_name_raw = raw.get("supplier_name", "").strip()
            if supplier_id_raw:
                supplier = db.query(Supplier).filter(Supplier.supplier_id == int(float(supplier_id_raw))).first()
                if not supplier:
                    raise ValueError(f"supplier_id {supplier_id_raw} not found")
                supplier_id = supplier.supplier_id
            elif supplier_name_raw:
                supplier = db.query(Supplier).filter(Supplier.name.ilike(supplier_name_raw)).first()
                if not supplier:
                    supplier = Supplier(name=supplier_name_raw, is_active=True)
                    db.add(supplier)
                    db.flush()
                    created_suppliers += 1
                supplier_id = supplier.supplier_id

            batch = DrugBatch(
                drug_id=drug.drug_id,
                batch_no=batch_no,
                expiry_date=expiry_date,
                purchase_price=purchase_price,
                selling_price=selling_price,
                quantity_available=quantity_available,
                supplier_id=supplier_id,
                is_expired=False,
            )
            db.add(batch)
            db.flush()
            created_batches += 1
            log_action(
                db,
                "bulk_add_batch",
                actor_user_id=current_user.user_id,
                target_table="drug_batches",
                target_id=batch.batch_id,
                detail={"batch_no": batch.batch_no, "drug_name": drug.drug_name},
            )
        except Exception as exc:
            errors.append({"row": str(idx), "error": str(exc)})

    db.commit()
    return {
        "total_rows": len(rows),
        "created_batches": created_batches,
        "created_drugs": created_drugs,
        "created_suppliers": created_suppliers,
        "failed_rows": len(errors),
        "errors": errors[:100],
    }


@router.patch("/drug-batches/{batch_id}/mark-expired", response_model=DrugBatchRead, dependencies=[Depends(require_permission("add_batch"))])
def mark_batch_expired(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(DrugBatch).filter(DrugBatch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    batch.is_expired = True
    db.commit()
    db.refresh(batch)
    return to_batch_read(batch)


@router.put("/inventory/{batch_id}", response_model=DrugBatchRead, dependencies=[Depends(require_permission("update_inventory"))])
def update_inventory(batch_id: int, payload: InventoryUpdate, db: Session = Depends(get_db)):
    batch = db.query(DrugBatch).filter(DrugBatch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    batch.quantity_available = payload.quantity_available
    db.commit()
    db.refresh(batch)
    return to_batch_read(batch)


@router.get("/patients", response_model=list[PatientRead], dependencies=[Depends(require_permission("view_patients"))])
def list_patients(db: Session = Depends(get_db)):
    patients = db.query(Patient).filter(Patient.is_archived.is_(False)).order_by(Patient.patient_id.asc()).all()
    creator_ids = {row.created_by_user_id for row in patients if row.created_by_user_id is not None}
    creators = db.query(User).filter(User.user_id.in_(creator_ids)).all() if creator_ids else []
    creator_map = {user.user_id: user.username for user in creators}
    return [to_patient_read(row, creator_map.get(row.created_by_user_id)) for row in patients]


@router.post("/patients", response_model=PatientRead, dependencies=[Depends(require_permission("add_patients"))])
def add_patient(payload: PatientCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    max_patient = db.query(Patient.patient_id).order_by(Patient.patient_id.desc()).first()
    next_patient_id = (max_patient[0] if max_patient else 10000) + 1
    patient = Patient(
        patient_id=next_patient_id,
        name=payload.name,
        address=payload.address,
        gender=payload.gender,
        contact=payload.contact,
        dob=payload.dob,
        blood_group=payload.blood_group,
        created_by_user_id=current_user.user_id,
        is_archived=False,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return to_patient_read(patient, current_user.username)


@router.put("/patients/{patient_id}", response_model=PatientRead, dependencies=[Depends(require_permission("view_patients"))])
def edit_patient(patient_id: int, payload: PatientUpdate, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if payload.name is not None:
        patient.name = payload.name
    if payload.address is not None:
        patient.address = payload.address
    if payload.gender is not None:
        patient.gender = payload.gender
    if payload.contact is not None:
        patient.contact = payload.contact
    if payload.dob is not None:
        patient.dob = payload.dob
    if payload.blood_group is not None:
        patient.blood_group = payload.blood_group
    db.commit()
    db.refresh(patient)
    creator = db.query(User).filter(User.user_id == patient.created_by_user_id).first() if patient.created_by_user_id else None
    return to_patient_read(patient, creator.username if creator else None)


@router.patch("/patients/{patient_id}/archive", response_model=PatientRead, dependencies=[Depends(require_permission("view_patients"))])
def archive_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.is_archived = True
    db.commit()
    db.refresh(patient)
    creator = db.query(User).filter(User.user_id == patient.created_by_user_id).first() if patient.created_by_user_id else None
    return to_patient_read(patient, creator.username if creator else None)


@router.get("/ai-report", dependencies=[Depends(require_permission("view_ai_report"))])
def ai_report_stub():
    return {"message": "Coming soon"}


def count_expiry_risk(batches: list[DrugBatch]) -> int:
    today = date.today()
    return sum(1 for row in batches if not row.is_expired and 0 <= (row.expiry_date - today).days <= 60)


@router.get("/dashboard-summary", dependencies=[Depends(require_permission("view_dashboard_summary"))])
def dashboard_summary(db: Session = Depends(get_db)):
    batches = db.query(DrugBatch).all()
    usable_stock = sum(row.quantity_available for row in batches if not row.is_expired)
    total_stock = len(batches)
    expiry_risk = count_expiry_risk(batches)

    drugs = db.query(Drug).all()
    by_drug = {}
    for row in batches:
        by_drug[row.drug_id] = by_drug.get(row.drug_id, 0) + row.quantity_available
    low_stock_alerts = sum(1 for drug in drugs if by_drug.get(drug.drug_id, 0) < drug.low_stock_threshold)

    total_patients = db.query(Patient).filter(Patient.is_archived.is_(False)).count()
    return {
        "usable_stock": usable_stock,
        "total_stock": total_stock,
        "expiry_risk": expiry_risk,
        "low_stock_alerts": low_stock_alerts,
        "total_patients": total_patients,
    }

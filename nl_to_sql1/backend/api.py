from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from db_introspection import introspect_database
from graph_builder import build_graph
from pipeline import run_pipeline
from sql_generator import generate_sql
from sql_executor import execute_with_retry
from rag import get_rag_stats, load_store

load_dotenv()

# ── Startup: load schema + graph once ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading schema and graph...")
    app.state.schema = introspect_database(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    app.state.G = build_graph(app.state.schema)
    print(f"Ready — {len(app.state.schema)} tables loaded.")
    yield

app = FastAPI(
    title="NL-to-SQL API",
    description="Ask questions in plain English, get SQL results from hospital DB",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response models ──────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    question: str
    sql: str
    columns: list
    rows: list
    count: int
    success: bool
    cached: bool = False


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "NL-to-SQL API is running", "docs": "/docs"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    schema = app.state.schema
    G = app.state.G

    # Run pipeline
    best_path = run_pipeline(question, schema, G)
    if not best_path:
        raise HTTPException(status_code=422, detail="Could not find a relevant path for this question")

    # Generate SQL
    sql = generate_sql(question, best_path, schema, G)

    # Execute
    result = execute_with_retry(question, sql, schema, best_path)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    # Check if result came from RAG cache
    store = load_store()
    cached = any(entry["query"].lower() == question.lower() and entry["sql"] == result["sql"]
                 for entry in store)

    return QueryResponse(
        question=question,
        sql=result["sql"],
        columns=result["columns"],
        rows=[list(row) for row in result["rows"][:100]],
        count=result["count"],
        success=True,
        cached=cached
    )


@app.get("/rag/stats")
def rag_stats():
    store = load_store()
    if not store:
        return {"total": 0, "entries": []}

    return {
        "total": len(store),
        "entries": [
            {
                "query": e["query"],
                "path": e["best_path"]["path"],
                "use_count": e.get("use_count", 1),
                "result_count": e["result_count"],
                "saved_at": e["saved_at"]
            }
            for e in store
        ]
    }


@app.delete("/rag/clear")
def clear_rag():
    from rag import clear_store
    clear_store()
    return {"message": "RAG store cleared"}

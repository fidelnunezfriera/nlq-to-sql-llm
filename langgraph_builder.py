from langgraph.graph import StateGraph, END
from pydantic import BaseModel
from modules.extract_intent import extract_intent
from modules.generate_sql import generate_sql
from modules.validate_sql import validate_sql
from modules.execute_sql import execute_sql

import time
import logging
import json
import re
from pathlib import Path
from logging import FileHandler
from datetime import datetime

# Logs para métricas (solo a archivo)
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

metrics_logger = logging.getLogger("metrics")
metrics_logger.setLevel(logging.INFO)
fh = FileHandler(LOG_DIR / "queries.log", encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
metrics_logger.propagate = False
metrics_logger.addHandler(fh)

# >>> JSON LOG: carpeta por NLQ
JSON_DIR = LOG_DIR / "json"
JSON_DIR.mkdir(exist_ok=True)

def _slug(s: str, maxlen: int = 80) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_-]", "", s)
    return s[:maxlen] if s else "nlq"

def _preview(x: str, n: int = 200) -> str:
    if x is None:
        return ""
    s = str(x)
    return s if len(s) <= n else s[:n] + "…"

def _total_ms(state) -> int | None:
    parts = [state.t_intent_ms, state.t_sql_ms, state.t_validate_ms, state.t_execute_ms]
    xs = [x for x in parts if isinstance(x, int)]
    return sum(xs) if xs else None

def _write_json_record(state, status: str):
    """Escribe una línea JSON en logs/json/<slug_nlq>.jsonl"""
    rec = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "status": status,  # "ok" | "error"
        "nlq": state.query,
        "intent": state.intent,
        "sql": state.sql,
        "result_preview": _preview(state.result, 200) if status == "ok" else "",
        "result_len": len(str(state.result)) if (status == "ok" and state.result is not None) else 0,
        "error": state.error if status == "error" else "",
        "times_ms": {
            "intent": state.t_intent_ms,
            "sql": state.t_sql_ms,
            "validate": state.t_validate_ms,
            "execute": state.t_execute_ms,
            "total": _total_ms(state),
        },
    }
    fname = JSON_DIR / f"{_slug(state.query)}.jsonl"
    with fname.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# Estado
class State(BaseModel):
    query: str
    intent: str = ""
    sql: str = ""
    error: str = ""
    result: str = ""

    # Métricas
    t_intent_ms: int | None = None
    t_sql_ms: int | None = None
    t_validate_ms: int | None = None
    t_execute_ms: int | None = None

# Nodos
def node_extract_intent(state: State) -> State:
    t0 = time.perf_counter()
    state.intent = extract_intent(state.query)
    state.t_intent_ms = int((time.perf_counter() - t0) * 1000)
    return state

def node_generate_sql(state: State) -> State:
    t0 = time.perf_counter()
    state.sql = generate_sql(state.intent, state.query)
    state.t_sql_ms = int((time.perf_counter() - t0) * 1000)
    return state

def node_validate_sql(state: State) -> State:
    t0 = time.perf_counter()
    is_valid, error_msg = validate_sql(state.sql)
    state.t_validate_ms = int((time.perf_counter() - t0) * 1000)
    if not is_valid:
        state.error = error_msg
    return state

def node_execute_sql(state: State) -> State:
    t0 = time.perf_counter()
    state.result = execute_sql(state.sql)
    state.t_execute_ms = int((time.perf_counter() - t0) * 1000)
    return state

def node_on_error(state: State) -> State:
    metrics_logger.warning(
        "status=error | NLQ=%r | intent=%r | sql=%r | error=%r | "
        "times_ms: intent=%s, sql=%s, validate=%s, execute=%s, total=%s",
        state.query, _preview(state.intent), _preview(state.sql), _preview(state.error, 500),
        state.t_intent_ms, state.t_sql_ms, state.t_validate_ms, state.t_execute_ms, _total_ms(state),
    )
    _write_json_record(state, status="error")
    return state

def node_exit(state: State) -> State:
    metrics_logger.info(
        "status=ok | NLQ=%r | intent=%r | sql=%r | result=%r | "
        "times_ms: intent=%s, sql=%s, validate=%s, execute=%s, total=%s",
        state.query, _preview(state.intent), _preview(state.sql), _preview(state.result),
        state.t_intent_ms, state.t_sql_ms, state.t_validate_ms, state.t_execute_ms, _total_ms(state),
    )
    _write_json_record(state, status="ok")
    return state

def route_next(state: State) -> str:
    return "exit" if state.error == "" else "error"

# Grafo
builder = StateGraph(State)
builder.add_node("extract_intent", node_extract_intent)
builder.add_node("generate_sql", node_generate_sql)
builder.add_node("validate_sql", node_validate_sql)
builder.add_node("execute_sql", node_execute_sql)
builder.add_node("on_error", node_on_error)
builder.add_node("exit", node_exit)

builder.set_entry_point("extract_intent")
builder.add_edge("extract_intent", "generate_sql")
builder.add_edge("generate_sql", "validate_sql")
builder.add_conditional_edges("validate_sql", route_next, {"exit": "execute_sql", "error": "on_error"})
builder.add_edge("execute_sql", "exit")
builder.add_edge("on_error", END)
builder.add_edge("exit", END)

graph = builder.compile()

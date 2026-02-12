import psycopg2
from psycopg2 import sql, OperationalError, ProgrammingError
from config import DB_CONFIG

def validate_sql(query: str) -> tuple[bool, str | None]:
    """
    Valida que la SQL empiece con SELECT y que sea sintácticamente correcta.
    Usa EXPLAIN para validar sin ejecutar.
    """
    stripped_query = query.strip().lower()
    if not stripped_query.startswith("select"):
        return False, "Only SELECT queries are allowed."
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"EXPLAIN {query}")  # Valida sin ejecutar
        cursor.close()
        conn.close()
        return True, None
    except (ProgrammingError, OperationalError) as e:
        safe_message = repr(e)
        return False, safe_message

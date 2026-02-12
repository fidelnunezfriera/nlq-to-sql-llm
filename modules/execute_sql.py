import psycopg2
from psycopg2 import OperationalError
from config import DB_CONFIG

def execute_sql(query: str) -> str:
    """
    Ejecuta la consulta SQL en PostgreSQL y devuelve el primer valor de la primera fila,
    ideal para respuestas como '¿cuántas vacas hay?' → 94
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result is None:
            return "No results"
        
        return ", ".join(str(val) for val in result)

    except OperationalError as e:
        return f"Connection error: {repr(e)}"
    except Exception as e:
        return f"Execution error: {repr(e)}"

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pathlib import Path
from config import OPENAI_API_KEY


# Carga el prompt desde el archivo
prompt_path = Path(__file__).parent / "prompts" / "sql_prompt.txt"
prompt_text = prompt_path.read_text(encoding="utf-8")


# Define el prompt con dos variables
sql_prompt = PromptTemplate(
    input_variables=["intent", "query"],
    template=prompt_text
)

# Modelo
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model="gpt-4o-mini",
    extra_body={"store": True}
)

# Chain final
sql_chain = sql_prompt | llm | (lambda x: x.content)

# Función directa
def generate_sql(intent: str, query: str) -> str:
    return sql_chain.invoke({"intent": intent, "query": query})

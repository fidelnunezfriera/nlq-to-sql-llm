from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, RunnableMap
from pathlib import Path
from config import OPENAI_API_KEY


# Carga el prompt desde el archivo
prompt_path = Path(__file__).parent / "prompts" / "intent_prompt.txt"
prompt_text = prompt_path.read_text(encoding="utf-8")

# Define el prompt
intent_prompt = PromptTemplate(
    input_variables=["query"],
    template=prompt_text
)

# Modelo
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model="gpt-4o-mini",
    extra_body={"store": True}
)

# Chain final
intent_chain = intent_prompt | llm | (lambda x: x.content)

# Función directa
def extract_intent(query: str) -> str:
    return intent_chain.invoke({"query": query})


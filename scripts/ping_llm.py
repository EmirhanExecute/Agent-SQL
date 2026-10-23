import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()
m = os.getenv("MODEL_NAME", "gemini-3.5-flash-lite")
r = ChatGoogleGenerativeAI(model=m, temperature=0).invoke("Say OK")
print(m, "->", r.content, r.usage_metadata)

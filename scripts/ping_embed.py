from dotenv import load_dotenv

load_dotenv()
from langchain_google_genai import GoogleGenerativeAIEmbeddings

for m in ["gemini-embedding-001", "models/gemini-embedding-001", "text-embedding-004"]:
    try:
        v = GoogleGenerativeAIEmbeddings(model=m).embed_documents(["hello", "merhaba"])
        print(m, "OK", len(v), len(v[0]))
        break
    except Exception as ex:
        print(m, "ERR", str(ex)[:150])

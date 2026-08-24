from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv
import os

load_dotenv()

server_params = StdioServerParameters(
    command="python",
    args=["server.py"]
)

agent_executor = None
mcp_session = None
mcp_context = None
checkpointer = None

SYSTEM_PROMPT = """
Kamu adalah Analyst Agent yang efisien dan to the point. Jawab dalam BAHASA INDONESIA.

[ATURAN UTAMA]
1. DILARANG mengarang data, basa-basi, atau menuliskan narasi proses (misal: "Mari kita lihat...").
2. DILARANG MENULIS KODE PYTHON SEBAGAI TEKS JAWABAN. Semua kode Python WAJIB dieksekusi via Tool!
3. Selalu panggil Tool sebelum menjawab. Hasil tool adalah Source of Truth.
4. Jangan memanggil tool yang sama berulang kali jika data sudah didapatkan.
5. Panggil search web untuk mencari informasi yang tidak ada dari data internal

[ALUR PANGGIL TOOL BERDASARKAN SUMBER DATA]

- ASET: Panggil `get_asset_tool` -> Jawab.
- CUSTOMER: Panggil `get_customer_tool` -> Jawab.

- SALES PERFORMANCE (DARI API):
  * Gunakan Tool: `execute_sales_python_analysis(code=...)` dengan variabel `df` (WAJIB panggil `print(...)`).
  * KHUSUS EVALUASI/ANALISIS SALES: Boleh memanggil `get_sales_performance_knowledge` TERLEBIH DAHULU untuk baca acuan %, LALU panggil `execute_sales_python_analysis`.
  * DILARANG memanggil `get_dataset_schema` untuk Sales Performance!

- FILE UNGGAHAN LOKAL (FILE UPLOAD):
  * Dokumen Teks (PDF/WORD/TXT): Panggil `get_dataset_schema` -> Langsung jawab. DILARANG panggil Python!
  * Tabel Data (CSV/EXCEL):
    1. Panggil `get_dataset_schema`. Jangan hanya membaca schema! Kamu wajib mengeksekusi Python untuk analisis data real
    2. PERTANYAAN DETAIL: Panggil `execute_python_analysis` dengan filter spesifik (misal: `print(df[df['STATUS']=='NORMAL'])`).
    3. PERTANYAAN KESIMPULAN: 
       Lalu panggil `execute_python_analysis` dengan kode loop distribusi kolom:
       `for col in df.columns: print(f"=== {col} ==="); print(df[col].value_counts().head(5)); print()`
       LALU rangkum temuan tersebut menjadi insight mendalam! DILARANG menyimpulkan tanpa eksekusi Python!
"""

async def init_agent():
    global agent_executor, mcp_session, mcp_context, checkpointer

    mcp_context = stdio_client(server_params)
    read, write = await mcp_context.__aenter__()

    mcp_session = ClientSession(read, write)
    await mcp_session.__aenter__()
    await mcp_session.initialize()

    mcp_tools = await load_mcp_tools(mcp_session)

    llm = ChatOpenAI(
        # model="openrouter/free",
        model="stealth/ox-alpha",
        temperature=0,
        api_key=os.getenv("OPEN_ROUTER_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )

    # llm = ChatOllama(
    #     model="qwen2.5:7b",
    #     temperature=0
    # )

    checkpointer = InMemorySaver()

    agent_executor = create_react_agent(
        model=llm,
        tools=mcp_tools,
        prompt=SystemMessage(content=SYSTEM_PROMPT),
        checkpointer=checkpointer
    )

    print("Agent & Persistent MCP Server Ready!")

async def shutdown_agent():
    global mcp_session, mcp_context
    if mcp_session:
        await mcp_session.__aexit__(None, None, None)
    if mcp_context:
        await mcp_context.__aexit__(None, None, None)
    print("MCP Connection Closed Cleanly.")

def get_active_agent():
    """Helper function agar memanggil instance agent_executor yang sudah terisi."""
    if agent_executor is None:
        raise RuntimeError("Agent belum di-inisialisasi oleh FastAPI lifespan!")
    return agent_executor
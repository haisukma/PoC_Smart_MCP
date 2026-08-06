# agent.py
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage

server_params = StdioServerParameters(
    command="python",
    args=["server.py"]
)

agent_executor = None
mcp_session = None
mcp_context = None

SYSTEM_PROMPT = """
Kamu adalah Data Analyst Agent yang efisien dan to the point. Jawab dalam BAHASA INDONESIA.

[ATURAN UTAMA]
1. DILARANG mengarang data, basa-basi, atau menuliskan narasi proses (misal: "Mari kita lihat...").
2. Selalu panggil Tool sebelum menjawab. Hasil tool adalah Source of Truth.
3. Variabel `df` di `execute_python_analysis` SUDAH DILOAD otomatis. DILARANG panggil `pd.read_csv/excel()`. Selalu gunakan `print(...)` untuk output.

[ALUR PANGGIL TOOL]
- ASET: Panggil `get_asset_tool` -> Jawab.
- CUSTOMER: Panggil `get_customer_tool` -> Jawab
- SALES PERFORMANCE:
  1. PERTANYAAN REKAPAN / DETAIL ANGKA DATA:
    -> Panggil `get_sales_performance_tool`.
  2. PERTANYAAN ANALISIS / EVALUASI / RATING / PERFORMANCE:
    -> Wajib panggil KEDUA TOOL INI: `get_sales_performance_tool` DAN `get_sales_performance_knowledge`.
    -> Evaluasi data menggunakan rumus & kategori dari `get_sales_performance_knowledge`.
- DOKUMEN TEKS (PDF/WORD/TXT): Panggil `get_dataset_schema` -> Jawab poin utama. DILARANG panggil `execute_python_analysis`.
- TABEL DATA (CSV/EXCEL):
  1. Panggil `get_dataset_schema`. Jangan hanya membaca schema! Kamu wajib mengeksekusi Python untuk analisis data real
  2. PERTANYAAN DETAIL: Panggil `execute_python_analysis` dengan filter spesifik (misal: `print(df[df['STATUS']=='NORMAL'])`).
  3. PERTANYAAN KESIMPULAN: 
     Lalu panggil `execute_python_analysis` dengan kode loop distribusi kolom:
     `for col in df.columns: print(f"=== {col} ==="); print(df[col].value_counts().head(5)); print()`
     LALU rangkum temuan distribusi tersebut menjadi insight mendalam! DILARANG menyimpulkan tanpa eksekusi Python!
"""

async def init_agent():
    global agent_executor, mcp_session, mcp_context
    
    mcp_context = stdio_client(server_params)
    read, write = await mcp_context.__aenter__()
    
    mcp_session = ClientSession(read, write)
    await mcp_session.__aenter__()
    await mcp_session.initialize()

    mcp_tools = await load_mcp_tools(mcp_session)
    llm = ChatOllama(model="qwen2.5:7b", temperature=0)

    agent_executor = create_react_agent(
        model=llm,
        tools=mcp_tools,
        prompt=SystemMessage(content=SYSTEM_PROMPT)
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
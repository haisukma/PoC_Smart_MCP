import asyncio
import json
from pathlib import Path
import sys
import time
from ollama import AsyncClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

mcp_session = None
stdio_context = None
ollama_tools = None

init_lock = asyncio.Lock()
client = AsyncClient()

server_params = StdioServerParameters(
    command="python",
    args=["server.py"],
)

SYSTEM_PROMPT = """
Kamu adalah Analyst Agent yang efisien dan to the point. Jawab dalam BAHASA INDONESIA.

[ATURAN UTAMA]
1. DILARANG mengarang data, basa-basi, atau menuliskan narasi proses (misal: "Mari kita lihat...").
2. Selalu panggil Tool sebelum menjawab. Hasil tool adalah Source of Truth.
3. Variabel `df` di `execute_python_analysis` SUDAH DILOAD otomatis. DILARANG panggil `pd.read_csv/excel()`. Selalu gunakan `print(...)` untuk output.

[ALUR PANGGIL TOOL]
- ASET: Panggil `get_asset_tool` -> Jawab
- CUSTOMER: Panggil `get_customer_tool` -> Jawab
- SALES PERFORMANCE: Panggil `get_sales_performance_tool -> Jawab
- DOKUMEN TEKS (PDF/WORD/TXT): Panggil `get_dataset_schema` -> Jawab poin utama. DILARANG panggil `execute_python_analysis`.
- TABEL DATA (CSV/EXCEL):
  1. Panggil `get_dataset_schema`. Jangan hanya membaca schema! Kamu wajib mengeksekusi Python untuk analisis data real
  2. PERTANYAAN DETAIL: Panggil `execute_python_analysis` dengan filter spesifik (misal: `print(df[df['STATUS']=='NORMAL'])`).
  3. PERTANYAAN KESIMPULAN/ANALISIS MENDALAM: 
     Lalu panggil `execute_python_analysis` dengan kode loop distribusi kolom:
     `for col in df.columns: print(f"=== {col} ==="); print(df[col].value_counts().head(5)); print()`
     LALU rangkum temuan distribusi tersebut menjadi insight mendalam! DILARANG menyimpulkan tanpa eksekusi Python!
"""

async def initialize_mcp():
    global mcp_session, stdio_context, ollama_tools

    if mcp_session is not None:
        return

    async with init_lock:
        if mcp_session is not None:
            return

        stdio_context = stdio_client(server_params)
        read, write = await stdio_context.__aenter__()
        mcp_session = ClientSession(read, write)
        await mcp_session.__aenter__()
        await mcp_session.initialize()

        tools_result = await mcp_session.list_tools()
        ollama_tools = convert_mcp_tools_to_ollama(tools_result.tools)
        print("MCP initialized")

def convert_mcp_tools_to_ollama(tools):
    ollama_tools = []
    for tool in tools:
        schema = tool.inputSchema
        if hasattr(schema, "model_dump"):
            schema = schema.model_dump()
        elif not isinstance(schema, dict):
            schema = dict(schema)

        ollama_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or f"Tool untuk {tool.name}",
                "parameters": schema
            }
        })
    return ollama_tools
async def chat(user_input: str, filename: str | None = None, doc_chunks: list[str] | None = None):
    total_start = time.time()
    await initialize_mcp()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    has_file = bool(filename and isinstance(filename, str) and filename.strip())
    
    active_tools = []
    if ollama_tools:
        if has_file:
            active_tools = ollama_tools
            messages.append({
                "role": "system",
                "content": (
                    f"[INFO SISTEM]: Pengguna mengunggah file data '{filename}'.\n"
                    f"1. Kamu WAJIB memanggil `get_dataset_schema(filename='{filename}')` terlebih dahulu.\n"
                    f"2. Setelah skema didapat, kamu WAJIB memanggil `execute_python_analysis`."
                )
            })
        else:
            file_tools = {"get_dataset_schema", "execute_python_analysis"}
            active_tools = [t for t in ollama_tools if t["function"]["name"] not in file_tools]

    messages.append({"role": "user", "content": user_input})

    max_iterations = 4

    for iteration in range(max_iterations):
        print(f"\nITERATION {iteration + 1}")

        response_stream = await client.chat(
            model="qwen2.5:7b",
            messages=messages,
            tools=active_tools if active_tools else None,
            stream=True
        )

        full_text = ""
        raw_tool_calls = []

        async for chunk in response_stream:
            # Catch tool calls jika ada
            if chunk.message.tool_calls:
                raw_tool_calls.extend(chunk.message.tool_calls)

            if chunk.message.content:
                text = chunk.message.content
                full_text += text
                yield text

        unique_tool_calls = []
        seen_calls = set()
        for call in raw_tool_calls:
            args_str = json.dumps(call.function.arguments, sort_keys=True) if isinstance(call.function.arguments, dict) else str(call.function.arguments)
            call_key = (call.function.name, args_str)
            if call_key not in seen_calls:
                seen_calls.add(call_key)
                unique_tool_calls.append(call)

        if unique_tool_calls:
            messages.append({
                "role": "assistant",
                "content": full_text,
                "tool_calls": unique_tool_calls
            })

            for call in unique_tool_calls:
                tool_name = call.function.name
                tool_args = call.function.arguments

                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except json.JSONDecodeError:
                        yield "\n[Error: Arguments tool bukan JSON yang valid.]"
                        return

                print("\nMCP TOOL CALL")
                print("Tool:", tool_name)
                print("Arguments:", json.dumps(tool_args, indent=2, ensure_ascii=False))

                try:
                    result = await mcp_session.call_tool(tool_name, arguments=tool_args)
                    result_text = "".join([c.text for c in result.content if hasattr(c, "text")])
                except Exception as e:
                    result_text = f"Error ketika memanggil tool {tool_name}: {str(e)}"

                tool_response = (
                    f"Hasil eksekusi {tool_name}:\n{result_text}\n\n"
                    f"[INSTRUKSI WAJIB]: Data di atas sudah lengkap. DILARANG memanggil tool yang sama lagi! "
                    f"Jawab dan analisis data tersebut HANYA dalam Bahasa Indonesia!"
                )

                messages.append({
                    "role": "tool",
                    "content": tool_response
                })

        else:
            print(f"\n[Selesai dalam {round(time.time() - total_start, 2)} detik]")
            return

    yield "\n[Batas maksimum tool calls tercapai.]"
    
async def close_mcp():
    global mcp_session, stdio_context, ollama_tools

    if mcp_session:
        try:
            await mcp_session.__aexit__(None, None, None)
        except Exception as e:
            print(f"Error closing MCP session: {e}")
        mcp_session = None

    if stdio_context:
        try:
            await stdio_context.__aexit__(None, None, None)
        except Exception as e:
            print(f"Error closing Stdio context: {e}")
        stdio_context = None

    ollama_tools = None
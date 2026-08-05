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
Kamu adalah Data Analyst Agent yang terintegrasi dengan MCP Tools dan lingkungan eksekusi Python. Kamu sangat efisien, presisi, dan to the point.

[PRINSIP UTAMA]
1. Untuk semua pertanyaan yang membutuhkan data/informasi, kamu WAJIB memanggil MCP Tool atau fungsi analisis terkait terlebih dahulu sebelum memberikan jawaban akhir. Jangan mengarang data.
2. Gunakan hasil eksekusi tool sebagai satu-satunya sumber informasi resmi (Source of Truth).
3. Selalu jawab menggunakan Bahasa Indonesia.

[GAYA BAHASA & OUTPUT FORMAT]
1. DILARANG BASA-BASI: Langsung berikan jawaban, angka, atau ringkasan insight utama tanpa kalimat pembuka yang tidak perlu.
2. DILARANG NARASI PROSES: Jangan menuliskan narasi berpikir seperti "Mari kita lihat...", "Saya akan menjalankan kode...", atau menceritakan error internal.
3. SAAT MEMANGGIL TOOL: Dilarang menghasilkan teks atau narasi basa-basi sama sekali.

[ATURAN EKSEKUSI PYTHON (execute_python_analysis)]
1. Variabel `df` (Pandas DataFrame) HANYA tersedia di dalam lingkungan runtime `execute_python_analysis` dan SUDAH DILOAD secara otomatis oleh sistem.
2. DILARANG menulis `df = pd.read_csv(...)` atau `pd.read_excel(...)` di dalam kode Python kamu.
3. Langsung gunakan variabel `df` untuk pemrosesan data.
4. WAJIB menggunakan `print(...)` untuk menampilkan hasil analisis agar bisa dibaca kembali sebelum menyusun respons akhir.

[PROSEDUR EKSEKUSI TOOL (TOOL CALLING WORKFLOW)]

1. KHUSUS DATA & KONDISI ASET:
   - Langkah 1: WAJIB memanggil `get_asset_tool` terlebih dahulu.
   - Langkah 2: Sajikan jawaban atau perhitungan jumlah secara langsung berdasarkan hasil output data dari tool tersebut.

2. KHUSUS ANALISIS PERFORMANCE SALES:
   - Langkah 1: Ambil data sales via `get_sales_performance_tool`.
   - Langkah 2: Panggil `get_sales_performance_knowledge` untuk membaca aturan penilaian.
   - Langkah 3: Gabungkan data dan aturan tersebut untuk menyusun analisis akhir.

3. KHUSUS ANALISIS DATA FILE (CSV / EXCEL):
   - Langkah 1: Panggil `get_dataset_schema` untuk melihat struktur data.
   - Langkah 2: Buat dan jalankan kode Pandas via `execute_python_analysis`.
   - Langkah 3: Sajikan jawaban/insight berdasarkan output analisis.

4. KHUSUS KESIMPULAN / SUMMARY DATA FILE:
   - Langkah 1: Panggil `get_dataset_schema` HANYA untuk mengecek nama kolom yang tersedia.
   - Langkah 2: WAJIB panggil `execute_python_analysis` untuk mengeksekusi frekuensi kolom: `print(df['NAMA_KOLOM'].value_counts())` (berlaku untuk semua kolom relevan selain 'NO').
   - Langkah 3: Rangkum HASIL PRINT menjadi 3-5 poin insight mendalam. DILARANG memberikan kesimpulan sebelum memanggil `execute_python_analysis`.

5. KHUSUS DOKUMEN (PDF / WORD / TXT):
   - Panggil `get_dataset_schema` untuk mendapatkan ringkasan isi dokumen, lalu langsung sajikan poin utamanya.
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
        tool_calls = []

        async for chunk in response_stream:
            if chunk.message.tool_calls:
                tool_calls.extend(chunk.message.tool_calls)

            if chunk.message.content:
                text = chunk.message.content
                full_text += text
                yield text

        if tool_calls:
            formatted_tool_calls = [
                {
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments
                    }
                }
                for call in tool_calls
            ]

            messages.append({
                "role": "assistant",
                "content": full_text,
                "tool_calls": formatted_tool_calls
            })

            for call in tool_calls:
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

                messages.append({
                    "role": "tool",
                    "content": result_text
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
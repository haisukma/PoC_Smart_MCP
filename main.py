# import time
# import shutil
# from pathlib import Path
# from contextlib import asynccontextmanager
# from fastapi import FastAPI, Form, UploadFile, File
# from fastapi.responses import StreamingResponse
# import agent as agent_module

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await agent_module.init_agent()
#     yield
#     await agent_module.shutdown_agent()

# app = FastAPI(lifespan=lifespan)

# DATA_DIR = Path("data_storage")
# DATA_DIR.mkdir(parents=True, exist_ok=True)

# async def stream_agent_response(
#     user_input: str,
#     thread_id: str,
#     filename: str | None = None
# ):
#     start_time = time.perf_counter()

#     print(f"\nRAG sedang mencocokkan tool untuk query: '{user_input}'...")
#     relevant_tool_names = agent_module.router_rag.get_relevant_tool_names(user_input, k=2)
#     print(f"Tool Terpilih oleh RAG: {relevant_tool_names}")

#     selected_tools = []
    
#     print("\nDEBUG: DAFTAR TOOL YANG TERSEDIA DI MCP SERVER")
#     for tool in agent_module.ALL_MCP_TOOLS:
#         print(f"-> Nama Tool Asli MCP: '{tool.name}'") 

#         is_matched_rag = any(name in tool.name for name in relevant_tool_names)
        
#         if is_matched_rag:
#             selected_tools.append(tool)
#             print(f"   [Lolos] Cocok dengan rekomendasi RAG!")
#         elif "web_search" in tool.name or "file" in tool.name:
#             selected_tools.append(tool)
#             print(f"   [Lolos] Tool Global (Web/File)")
#         elif filename and "python_analysis" in tool.name and "asset" not in tool.name and "sales" not in tool.name:
#             selected_tools.append(tool)
#             print(f"   [Lolos] Tool Python File Lokal")

#     if not selected_tools:
#         print("WARNING: selected_tools kosong! Menggunakan semua master tools sebagai fallback.")
#         selected_tools = agent_module.ALL_MCP_TOOLS

#     print(f"Jumlah tool yang disuntikkan ke Agent: {len(selected_tools)}")

#     agent = agent_module.create_dynamic_agent(selected_tools)

#     messages = []
#     if filename:
#         messages.append((
#             "system",
#             f"[INFO SISTEM]: Pengguna mengunggah file '{filename}'.\n"
#             f"Gunakan `get_dataset_schema(filename='{filename}')` jika perlu."
#         ))

#     messages.append(("user", user_input))
#     inputs = {"messages": messages}
#     config = {"configurable": {"thread_id": thread_id}}

#     try:
#         async for event in agent.astream_events(inputs, config=config, version="v2"):
#             kind = event["event"]
#             if kind == "on_chat_model_stream":
#                 content = event["data"]["chunk"].content
#                 if content:
#                     yield content
#             elif kind == "on_tool_start":
#                 print(f"\n[MCP TOOL DIPANGGIL BY AGENT]: {event['name']}")
#     except Exception as agent_err:
#         print(f"\nError terjadi saat running LangGraph Agent: {str(agent_err)}")
#         yield f"Maaf, terjadi kendala teknis pada LLM: {str(agent_err)}"

#     execution_time = time.perf_counter() - start_time
#     print(f"\nTOTAL WAKTU EKSEKUSI: {execution_time:.2f} detik")

# @app.post("/chat")
# async def chat_endpoint(
#     message: str = Form(...),
#     thread_id: str = Form(...),
#     file: UploadFile | None = File(None)
# ):
#     saved_filename = None

#     if file and file.filename and file.filename.strip():
#         saved_filename = file.filename.strip()
#         file_path = DATA_DIR / saved_filename

#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#     return StreamingResponse(
#         stream_agent_response(
#             user_input=message,
#             thread_id=thread_id,
#             filename=saved_filename
#         ),
#         media_type="text/event-stream"
#     )

# langchain
import time
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import StreamingResponse
from agent import init_agent, shutdown_agent, get_active_agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_agent()
    yield
    await shutdown_agent()

app = FastAPI(lifespan=lifespan)

DATA_DIR = Path("data_storage")
DATA_DIR.mkdir(parents=True, exist_ok=True)

async def stream_agent_response(
    user_input: str,
    thread_id: str,
    filename: str | None = None
):
    start_time = time.perf_counter()
    agent = get_active_agent()
    messages = []

    if filename:
        messages.append((
            "system",
            f"[INFO SISTEM]: Pengguna mengunggah file '{filename}'.\n"
            f"Gunakan `get_dataset_schema(filename='{filename}')` jika perlu."
        ))

    messages.append(("user", user_input))
    inputs = {"messages": messages}

    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "recursion_limit": 25
    }

    try:
        async for event in agent.astream_events(
            inputs,
            config=config,
            version="v2"
        ):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield content

            elif kind == "on_tool_start":
                print(f"\n[MCP TOOL DIPANGGIL]: {event['name']}")
                
    except Exception as e:
        if "recursion limit" in str(e).lower():
            warning_msg = (
                "\n\nSistem Memotong Eksekusi Paksa:\n"
                "Proses analisis data terlalu panjang dan berputar-putar. "
                "Mohon berikan pertanyaan yang lebih spesifik atau periksa kembali format data Anda."
            )
            print("\n[PERINGATAN SISTEM]: Agent dihentikan paksa karena menyentuh recursion_limit.")
            yield warning_msg
        else:
            yield f"\n\n[Sistem Error]: {str(e)}"

    execution_time = time.perf_counter() - start_time
    print(f"\nTOTAL WAKTU EKSEKUSI: {execution_time:.2f} detik")


# async def stream_agent_response(
#     user_input: str,
#     thread_id: str,
#     filename: str | None = None
# ):
#     start_time = time.perf_counter()

#     agent = get_active_agent()

#     messages = []

#     if filename:
#         messages.append((
#             "system",
#             f"[INFO SISTEM]: Pengguna mengunggah file '{filename}'.\n"
#             f"Gunakan `get_dataset_schema(filename='{filename}')` jika perlu."
#         ))

#     messages.append(("user", user_input))

#     inputs = {
#         "messages": messages
#     }

#     config = {
#         "configurable": {
#             "thread_id": thread_id,
#         },
#         # "recursion_limit": 5
#     }

#     async for event in agent.astream_events(
#         inputs,
#         config=config,
#         version="v2"
#     ):
#         kind = event["event"]

#         if kind == "on_chat_model_stream":
#             content = event["data"]["chunk"].content

#             if content:
#                 yield content

#         elif kind == "on_tool_start":
#             print(f"\n[MCP TOOL DIPANGGIL]: {event['name']}")

#     execution_time = time.perf_counter() - start_time

#     print(
#         f"\nTOTAL WAKTU EKSEKUSI: "
#         f"{execution_time:.2f} detik"
#     )

@app.post("/chat")
async def chat_endpoint(
    message: str = Form(...),
    thread_id: str = Form(...),
    file: UploadFile | None = File(None)
):
    saved_filename = None

    if file and file.filename and file.filename.strip():
        saved_filename = file.filename.strip()

        file_path = DATA_DIR / saved_filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

    return StreamingResponse(
        stream_agent_response(
            user_input=message,
            thread_id=thread_id,
            filename=saved_filename
        ),
        media_type="text/event-stream"
    )
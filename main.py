import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from client import initialize_mcp, close_mcp, chat

DATA_DIR = Path("data_storage")
DATA_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing MCP session...")
    await initialize_mcp()
    yield
    print("Closing MCP session...")
    await close_mcp()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
async def chatbot(
    message: str = Form(...),
    file: UploadFile | None = File(None)
):
    saved_filename = None

    print("\nNEW REQUEST")
    print(f"[DEBUG] Message: '{message}'")
    print(f"[DEBUG] Raw File Object: {file}")
    if file:
        print(f"[DEBUG] Raw File Name: '{file.filename}'")

    if file and file.filename and file.filename.strip():
        saved_filename = file.filename.strip()
        file_path = DATA_DIR / saved_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"[DEBUG] STATUS FILE: Tersimpan sebagai '{saved_filename}'")
    else:
        print("[DEBUG] STATUS FILE: Tidak ada file yang diunggah (None/Empty)")

    return StreamingResponse(
        chat(message, filename=saved_filename),
        media_type="text/event-stream"
    )

# langchain
# import time
# import shutil
# from pathlib import Path
# from contextlib import asynccontextmanager
# from fastapi import FastAPI, Form, UploadFile, File
# from fastapi.responses import StreamingResponse
# from agent import init_agent, shutdown_agent, get_active_agent

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await init_agent()
#     yield
#     await shutdown_agent()

# app = FastAPI(lifespan=lifespan)

# DATA_DIR = Path("data_storage")
# DATA_DIR.mkdir(parents=True, exist_ok=True)

# async def stream_agent_response(user_input: str, filename: str | None = None):
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
#     inputs = {"messages": messages}

#     async for event in agent.astream_events(inputs, version="v2"):
#         kind = event["event"]

#         if kind == "on_chat_model_stream":
#             content = event["data"]["chunk"].content
#             if content:
#                 yield content

#         elif kind == "on_tool_start":
#             print(f"\n[MCP TOOL DIPANGGIL]: {event['name']}")

#     end_time = time.perf_counter()
#     execution_time = end_time - start_time

#     print(f"\nTOTAL WAKTU EKSEKUSI]: {execution_time:.2f} detik")

# @app.post("/chat")
# async def chat_endpoint(
#     message: str = Form(...),
#     file: UploadFile | None = File(None)
# ):
#     saved_filename = None

#     if file and file.filename and file.filename.strip():
#         saved_filename = file.filename.strip()
#         file_path = DATA_DIR / saved_filename
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#     return StreamingResponse(
#         stream_agent_response(message, filename=saved_filename),
#         media_type="text/event-stream"
#     )
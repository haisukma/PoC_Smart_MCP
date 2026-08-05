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
    print("[SERVER] Initializing MCP session...")
    await initialize_mcp()
    yield
    print("[SERVER] Closing MCP session...")
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
from fastapi import FastAPI, Form, File, UploadFile
from contextlib import asynccontextmanager
from services_mcp.file_service import extract_text
from client import (
    chat,
    initialize_mcp,
    close_mcp
)

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("Initializing MCP session")
    await initialize_mcp()
    yield
    print("Closing MCP session")
    await close_mcp()

app = FastAPI(lifespan=lifespan)

@app.post("/chat")
async def chatbot(
    message: str = Form(...),
    file: UploadFile | None = File(None)
):

    context = ""

    if file:
        context = await extract_text(file)

    answer = await chat(
        message,
        context=context
    )

    return {
        "success": True,
        "answer": answer
    }

# @app.post("/stream_chat")
# async def stream_chat(
#     message: str = Form(...),
#     File: UploadFile | None = File(None)
# )
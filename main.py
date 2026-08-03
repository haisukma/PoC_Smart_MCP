# from fastapi import FastAPI
# from contextlib import asynccontextmanager
# from pydantic import BaseModel


# from client import (
#     chat,
#     initialize_mcp,
#     close_mcp
# )

# # app = FastAPI()

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("Initializing MCP session")
#     await initialize_mcp()
#     yield
#     print("Closing MCP session")
#     await close_mcp()

# app = FastAPI(lifespan=lifespan)

# class ChatRequest(BaseModel):
#     message: str


# @app.post("/chat")
# async def chatbot(req: ChatRequest):

#     answer = await chat(req.message)

#     return {
#         "success": True,
#         "answer": answer
#     }

from fastapi import FastAPI, Form, File, UploadFile
from contextlib import asynccontextmanager
from pydantic import BaseModel
from services_mcp.file_service import extract_text

from client import (
    chat,
    initialize_mcp,
    close_mcp
)
# app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing MCP session")
    await initialize_mcp()
    yield
    print("Closing MCP session")
    await close_mcp()

app = FastAPI(lifespan=lifespan)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chatbot(req: ChatRequest):
    answer = await chat(req.message)
    return {
        "success": True,
        "answer": answer
    }

@app.post("/file_chat")
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
        "answer": answer
    }

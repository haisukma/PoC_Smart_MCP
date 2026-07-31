from fastapi import FastAPI
from pydantic import BaseModel

from client import chat

app = FastAPI()

class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chatbot(req: ChatRequest):

    answer = await chat(req.message)

    return {
        "success": True,
        "answer": answer
    }
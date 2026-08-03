import asyncio
import json
import os
import time
# from dotenv import load_dotenv
from ollama import Client
from mcp import (
    ClientSession,
    StdioServerParameters
)
from mcp.client.stdio import stdio_client

# load_dotenv()

mcp_session = None
stdio_context = None
ollama_tools = None

init_lock = asyncio.Lock()

# OLLAMA_HOST = os.getenv("OLLAMA_HOST")
# MODEL_NAME = "gemma4:12b"

# client = Client(host=OLLAMA_HOST)
client = Client()

server_params = StdioServerParameters(
    command="python",
    args=["server.py"],
)

SYSTEM_PROMPT = """
Kamu adalah AI assistant yang menggunakan MCP tools.

Aturan:

- Gunakan tool yang paling sesuai berdasarkan nama,
  deskripsi, dan parameter yang tersedia.
- Jangan mengarang data.
- Gunakan hasil MCP sebagai sumber informasi utama.
- Jika tool menghasilkan data, gunakan data tersebut
  untuk menjawab pertanyaan user.
- Jangan mengatakan data kosong jika tool sebenarnya
  mengembalikan data.
- Jangan memanggil tool yang tidak relevan.
- Jika user meminta analisis, evaluasi, penilaian, atau perhitungan performance sales: Ambil terlebih dahulu data performance yang relevan menggunakan tool data, Setelah data diperoleh panggil tool get_sales_performance_knowledge, Gunakan data dan aturan tersebut untuk menyusun jawaban.
- Jangan memanggil knowledge jika user hanya meminta data mentah.
- Jawab dalam bahasa Indonesia.

Berikan jawaban yang langsung, jelas, dan sesuai
dengan data yang diperoleh dari MCP.
"""

async def initialize_mcp():

    global mcp_session
    global stdio_context
    global ollama_tools

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

        ollama_tools = convert_mcp_tools_to_ollama(
            tools_result.tools
        )

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

def ask_gemma(messages, tools=None):

    start = time.time()

    kwargs = {
        "model": "qwen2.5:7b",
        "messages": messages
    }

    if tools:
        kwargs["tools"] = tools

    response = client.chat(**kwargs)

    print(
        "Gemma time:",
        round(time.time()-start,2),
        "detik"
    )

    return response

async def chat(
        user_input: str,
        context: str = ""
    ):

    total_start = time.time()

    await initialize_mcp()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    if context:
        messages.append({
            "role": "system",
            "content": f"""
    Berikut adalah isi dokumen yang diunggah user.

    {context}
    """
        })

    messages.append({
        "role": "user",
        "content": user_input
    })

    max_iterations = 4

    for iteration in range(max_iterations):

        print(f"\nITERATION {iteration + 1}")

        response = ask_gemma(
            messages,
            tools=ollama_tools
        )

        assistant_message = response.message

        formatted_assistant = {
            "role": "assistant",
            "content": assistant_message.content or ""
        }

        if assistant_message.tool_calls:

            formatted_assistant["tool_calls"] = [

                {
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments
                    }
                }

                for call in assistant_message.tool_calls

            ]

        messages.append(formatted_assistant)

        tool_calls = assistant_message.tool_calls

        if not tool_calls:

            print("\nHASIL GEMMA")
            print(assistant_message.content)

            print(
                "Total request time:",
                round(time.time()-total_start, 2),
                "detik"
            )

            return assistant_message.content

        for call in tool_calls:

            tool_name = call.function.name
            tool_args = call.function.arguments

            if isinstance(tool_args, str):

                try:
                    tool_args = json.loads(tool_args)

                except json.JSONDecodeError:

                    error = "Arguments tool bukan JSON yang valid."

                    print(error)

                    return error

            print("\nMCP TOOL CALL")
            print("Tool :", tool_name)

            print("Arguments:")
            print(json.dumps(
                tool_args,
                indent=2,
                ensure_ascii=False
            ))

            try:

                result = await mcp_session.call_tool(
                    tool_name,
                    arguments=tool_args
                )

                result_text = ""

                for content in result.content:

                    if hasattr(content, "text"):
                        result_text += content.text

                print("\n=== MCP RESULT ===")
                print(result_text)

            except Exception as e:

                result_text = (
                    f"Error ketika memanggil tool "
                    f"{tool_name}: {str(e)}"
                )

                print(result_text)

            messages.append({
                "role": "tool",
                "name": tool_name,
                "content": result_text
            })

    return "Gemma mencapai batas maksimum tool calls."

async def close_mcp():

    global mcp_session
    global stdio_context
    global ollama_tools

    if mcp_session:

        await mcp_session.__aexit__(None, None, None)
        mcp_session = None

    if stdio_context:

        await stdio_context.__aexit__(None, None, None)
        stdio_context = None

    ollama_tools = None

if __name__ == "__main__":

    user_input = input("\nApa yang ingin kamu cari?\n> ")
    result = asyncio.run(
        chat(user_input)
    )

    print(result)
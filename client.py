import asyncio
import json
import os
from ollama import Client
from mcp import (
    ClientSession,
    StdioServerParameters
)
from mcp.client.stdio import stdio_client

OLLAMA_HOST = os.getenv("OLLAMA_HOST")
MODEL_NAME = "gemma4:12b"

client = Client(host=OLLAMA_HOST)

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
- Jika data yang dikembalikan sangat banyak,
  gunakan hanya data yang relevan dengan pertanyaan user.
- Jangan memanggil tool yang tidak relevan.
- Jawab dalam bahasa Indonesia.

Berikan jawaban yang langsung, jelas, dan sesuai
dengan data yang diperoleh dari MCP.
"""


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

    kwargs = {
        "model": MODEL_NAME,
        "messages": messages
    }

    if tools:
        kwargs["tools"] = tools

    return client.chat(**kwargs)


async def chat(user_input: str):

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            tools_result = await session.list_tools()
            mcp_tools = tools_result.tools

            print("\n=== TOOLS TERSEDIA ===")
            for tool in mcp_tools:
                print(f"- {tool.name}")

            ollama_tools = convert_mcp_tools_to_ollama(
                mcp_tools
            )

            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ]

            max_iterations = 4

            for iteration in range(max_iterations):

                print(f"\n========== ITERATION {iteration + 1} ==========")

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

                    print("\n=== HASIL GEMMA ===")
                    print(assistant_message.content)

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

                    print("\n=== MCP TOOL CALL ===")
                    print("Tool :", tool_name)

                    print("Arguments:")
                    print(json.dumps(
                        tool_args,
                        indent=2,
                        ensure_ascii=False
                    ))

                    try:

                        result = await session.call_tool(
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

if __name__ == "__main__":

    user_input = input("\nApa yang ingin kamu cari?\n> ")

    result = asyncio.run(
        chat(user_input)
    )

    print(result)
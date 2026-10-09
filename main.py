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
import asyncio
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, UploadFile, File, HTTPException, status
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

PYTHON_ANALYSIS_TOOLS = {
    "execute_asset_python_analysis",
    "execute_customer_analysis",
    "execute_sales_python_analysis",
}

INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior)\s+((?:safety|security|system|operational|internal|core|original|initial|existing|given|stated|provided|defined|specified|established)\s+)?(instructions?|rules?|guidelines?|constraints?|directives?)",
    r"(?i)disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|guidelines?|constraints?|directives?)",
    r"(?i)forget\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|guidelines?|constraints?|directives?)",
    r"(?i)new\s+instructions?:",
    r"(?i)do\s+not\s+follow\s+(the\s+)?(system|developer|previous|original)",
    r"(?i)supersedes?\s+(all\s+)?(prior|previous)\s+(instructions?|rules?|guidelines?|constraints?|directives?)",
    r"(?i)(all\s+)?(previous|prior)\s+instructions?\s+(are|is)\s+(void|invalid|null|obsolete|cancelled|revoked)",
    r"(?i)you\s+are\s+now\s+(in\s+)?developer\s+mode",
    r"(?i)enter\s+(developer|admin|debug|maintenance)\s+mode",
    r"(?i)activate\s+(developer|admin|debug|jailbreak)\s+mode",
    r"(?i)\bsystem\s+override\b",
    r"(?i)override\s+(your\s+)?(instructions?|rules?|guidelines?|constraints?|directives?)",
    r"(?i)reveal\s+((?:your?|yoru|yuor|the|my|its|his|her|our|their)\s+)?((?:(?:full|hidden|complete|internal|secret|original|entire|exact|actual|real)\s+){0,2})((?:system|systme|sysetm|systemp?)\s+)?prompt\b",
    r"(?i)show\s+(me\s+)?((?:your?|yoru|yuor|the|my|its|his|her|our|their)\s+)((?:system|systme|sysetm|systemp?)\s+)?prompt\b",
    r"(?i)what\s+(are|were)\s+(your\s+)?(exact\s+)?instructions",
    r"(?i)repeat\s+(the\s+)?(text|instructions?)\s+(above|before)",
    r"(?i)output\s+(your\s+)?(initial|original|system)\s+(prompt|instructions?)",
    r"(?i)you\s+are\s+no\s+longer\s+(bound|restricted|limited)",
    r"(?i)act\s+as\s+if\s+(you('re|\s+are)\s+)?not\s+bound",
    r"(?i)pretend\s+(you('re|\s+are)\s+)?(a\s+)?different\s+(ai|assistant|model)",
    r"(?i)you\s+are\s+now\s+(?:(?:a|an)\s+)?\w+.{0,40}(without\s+(any\s+)?restrict|ignor\w*\s+(all|any|every|prev)|bypass|unrestrict|unlimit|obey\s+only|no\s+(rules|limits|restrict|boundari))",
    r"(?i)\bDAN\b.*\bdo\s+anything\s+now\b",
    r"(?i)jailbreak(ed)?\s+(mode|prompt)",
    r"(?i)bypass\s+(your\s+)?(safety|security|content|ethical)\s+(filters?|measures?|guidelines?|restrictions?)",
    r"(?i)disable\s+(your\s+)?(safety|security|content)\s+(filters?|measures?)",
    r"(?i)(ignore|disregard)\s+(all\s+)?(your\s+)?(safety|security|ethical|content)\s+(guidelines?|rules?|restrictions?|measures?|filters?|polic(?:y|ies)|protocols?)",
    r"(?i)<\s*\/?\s*system\s*\/?>",
    r"(?i)<\s*\/?\s*(assistant|developer|tool|function)\s*\/?>",
    r"(?i)\]\s*\n\s*\[?(system|assistant|user)\]?:",
    r"(?i)\[\s*(System\s*Message|System|Assistant|Internal)\s*\]",
    r"(?i)^\s*System:\s+",
    r"\[\s*(?i:SYSTEM|ASSISTANT|DEVELOPER|INTERNAL|USER)\b.*\]",
    r"(?i)<\|(?:im_start|im_end|eot_id|start_header_id|end_header_id|endoftext)\|>",
    r"(?i)<\uFF5C(?:end\u2581of\u2581sentence|begin\u2581of\u2581sentence)\uFF5C>"
]

COMPILED_INJECTION_REGEX = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

def validate_prompt_injection(user_input: str):
    """Mengecek apakah input mengandung indikasi Prompt Injection."""
    for pattern in COMPILED_INJECTION_REGEX:
        if pattern.search(user_input):
            return True
    return False
    
async def run_agent_with_timeout(
    agent,
    inputs,
    config,
    timeout_seconds=60
):
    async def collect_events():
        events = []

        async for event in agent.astream_events(
            inputs,
            config=config,
            version="v2"
        ):
            events.append(event)

        return events

    return await asyncio.wait_for(
        collect_events(),
        timeout=timeout_seconds
    )

async def stream_agent_response(
    user_input: str,
    thread_id: str,
    filename: str | None = None
):
    start_time = time.perf_counter()

    TIMEOUT_SECONDS = 120

    agent = get_active_agent()
    messages = []

    if filename:
        messages.append((
            "system",
            f"[INFO SISTEM]: Pengguna mengunggah file '{filename}'.\n"
            f"Gunakan `get_dataset_schema(filename='{filename}')` jika perlu."
        ))

    messages.append(("user", user_input))

    inputs = {
        "messages": messages
    }

    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "recursion_limit": 19
    }

    try:
        async for event in agent.astream_events(
            inputs,
            config=config,
            version="v2"
        ):

            elapsed = time.perf_counter() - start_time

            if elapsed > TIMEOUT_SECONDS:

                print(
                    f"\n[PERINGATAN]: Agent timeout "
                    f"setelah {TIMEOUT_SECONDS} detik."
                )

                yield (
                    f"\n\n[Sistem]: Proses analisis dihentikan "
                    f"karena melebihi batas waktu "
                    f"{TIMEOUT_SECONDS} detik."
                )

                break

            kind = event["event"]

            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content

                if content:
                    yield content

            elif kind == "on_tool_start":
                tool_name = event["name"]

                print(
                    f"\n[MCP TOOL DIPANGGIL]: {tool_name}"
                )

                tool_input = event["data"].get(
                    "input",
                    {}
                )

                print(
                    f"TOOL INPUT: {tool_input}"
                )

                if tool_name in PYTHON_ANALYSIS_TOOLS:
                    code = tool_input.get("code")

                    if code:

                        print("\n" + "=" * 70)
                        print("PYTHON CODE DARI LLM")
                        print("=" * 70)

                        print(code)

                        print("=" * 70)

            elif kind == "on_tool_end":

                print(
                    f"\n[MCP TOOL SELESAI]: {event['name']}"
                )

    except Exception as e:
        if "recursion limit" in str(e).lower():

            print(
                "\n[PERINGATAN SISTEM]: "
                "Agent dihentikan karena recursion_limit."
            )

            yield (
                "\n\nSistem Memotong Eksekusi Paksa:\n"
                "Proses analisis data terlalu panjang dan berputar-putar."
            )

        else:

            yield f"\n\n[Sistem Error]: {str(e)}"

    execution_time = time.perf_counter() - start_time

    print(
        f"\nTOTAL WAKTU EKSEKUSI: "
        f"{execution_time:.2f} detik"
    )

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
#         "recursion_limit": 19
#     }

#     try:

#         async for event in agent.astream_events(
#             inputs,
#             config=config,
#             version="v2"
#         ):

#             kind = event["event"]


#             if kind == "on_chat_model_stream":

#                 content = event["data"]["chunk"].content

#                 if content:
#                     yield content

#             elif kind == "on_tool_start":

#                 tool_name = event["name"]

#                 print(
#                     f"\n[MCP TOOL DIPANGGIL]: {tool_name}"
#                 )

#                 tool_input = event["data"].get(
#                     "input",
#                     {}
#                 )

#                 if tool_name in PYTHON_ANALYSIS_TOOLS:

#                     code = tool_input.get("code")

#                     if code:

#                         print("\n" + "=" * 70)
#                         print("PYTHON CODE DARI LLM")
#                         print("=" * 70)

#                         print(code)

#                         print("=" * 70)

#             elif kind == "on_tool_end":

#                 print(
#                     f"\n[MCP TOOL SELESAI]: {event['name']}"
#                 )

#     except Exception as e:

#         if "recursion limit" in str(e).lower():

#             warning_msg = (
#                 "\n\nSistem Memotong Eksekusi Paksa:\n"
#                 "Proses analisis data terlalu panjang dan berputar-putar. "
#                 "Mohon berikan pertanyaan yang lebih spesifik atau "
#                 "periksa kembali format data Anda."
#             )

#             print(
#                 "\n[PERINGATAN SISTEM]: "
#                 "Agent dihentikan paksa karena "
#                 "menyentuh recursion_limit."
#             )

#             yield warning_msg

#         else:

#             yield f"\n\n[Sistem Error]: {str(e)}"

#     execution_time = time.perf_counter() - start_time

#     print(
#         f"\nTOTAL WAKTU EKSEKUSI: "
#         f"{execution_time:.2f} detik"
#     )


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
    if validate_prompt_injection(message):
        print(f"\n[PERINGATAN]: Prompt Injection terdeteksi pada input: '{message}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permintaan ditolak: Terdeteksi indikasi Prompt Injection"
        )
    
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

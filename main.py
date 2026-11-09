import asyncio
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
import re
import shutil
import sys
import uuid
import time
from contextvars import ContextVar
from agent import get_active_agent, init_agent, shutdown_agent
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status, Request, Response
from fastapi.responses import StreamingResponse
from opentelemetry import trace, metrics 
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

load_dotenv()

@asynccontextmanager 
async def lifespan(app: FastAPI):
  await init_agent()
  yield
  await shutdown_agent()

# service_name = os.getenv("OTEL_SERVICE_NAME", "mcp-backend")
# # resource = Resource.create(attributes={"service.name": service_name})
resource = Resource.create(attributes={
    "service.name": "mcp-monitoring",
    # "deployment.environment.name": "development", 
    # "service.namespace": "default"
})

# provider = TracerProvider(resource=resource)
# trace.set_tracer_provider(provider)

otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
raw_headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")

headers_dict = {}
if "=" in raw_headers:
  key, val = raw_headers.split("=", 1)
  headers_dict[key.strip()] = val.strip()

# otlp_exporter = OTLPSpanExporter(
#     endpoint=f"{otlp_endpoint}/v1/traces",
#     headers=headers_dict,
# )
# provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# metric_exporter = OTLPMetricExporter(
#     endpoint=f"{otlp_endpoint}/v1/metrics",
#     headers=headers_dict,
# )
# metric_reader = PeriodicExportingMetricReader(metric_exporter)
# meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
# metrics.set_meter_provider(meter_provider)

# app = FastAPI(lifespan=lifespan)
# FastAPIInstrumentor.instrument_app(app)

trace_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(trace_provider)
trace_exporter = OTLPSpanExporter(
    endpoint=f"{otlp_endpoint}/v1/traces",
    headers=headers_dict,
)
trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))

meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[
        PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=f"{otlp_endpoint}/v1/metrics",
                headers=headers_dict,
            )
        )
    ],
)
metrics.set_meter_provider(meter_provider)

app = FastAPI(lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)

logger = logging.getLogger("mcp_backend")
logger.setLevel(logging.INFO)

if not logger.handlers:
  file_handler = logging.FileHandler("app_monitoring3.log", mode="a")
  file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
  file_handler.setFormatter(file_formatter)
  logger.addHandler(file_handler)

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

tool_start_times = {}

async def stream_agent_response(
    user_input: str,
    thread_id: str,
    filename: str | None = None
):
    start_time = time.perf_counter()
    TIMEOUT_SECONDS = 300

    agent = get_active_agent()
    messages = []
    tool_start_times = {}

    if filename:
        messages.append((
            "system",
            f"[INFO SISTEM]: Pengguna mengunggah file '{filename}'.\n"
            f"Gunakan `get_dataset_schema(filename='{filename}')` jika perlu"
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
                logger.warning(f"PERINGATAN: Agent timeout setelah {TIMEOUT_SECONDS} detik")
                yield (f"\n\n[Sistem]: Proses analisis dihentikan karena melebihi batas waktu {TIMEOUT_SECONDS} detik")
                break

            kind = event["event"]

            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield content

            elif kind == "on_tool_start":
                tool_name = event.get("name") or event.get("data", {}).get("name") or "unknown_tool"
                tool_start_times[tool_name] = time.perf_counter()

                logger.info(f"[MCP TOOL DIPANGGIL]: {tool_name}")
                tool_input = event["data"].get("input", {})
                logger.info(f"TOOL INPUT: {tool_input}")

                if tool_name in PYTHON_ANALYSIS_TOOLS:
                    code = tool_input.get("code")
                    if code:
                        logger.info(f"Code LLM: {code}")

            elif kind == "on_tool_end":
                tool_name = event.get("name") or event.get("data", {}).get("name") or "unknown_tool"
                start_time_tool = tool_start_times.get(tool_name)
                tool_output = event["data"].get("output", {})
                logger.info(f"TOOL OUTPUT: {tool_output}")

                if start_time_tool:
                    duration =time.perf_counter() - start_time_tool
                    logger.info(f"MCP TOOL SELESAI: {tool_name} (Durasi: {duration:.2f} detik)")
                    del tool_start_times[tool_name]
                else:
                    logger.info(f"MCP TOOL SELESAI: {tool_name}")

    except Exception as e:
        if "recursion limit" in str(e).lower():
            logger.warning(f"PERINGATAN SISTEM: Agent dihentikan karena recursion limit")
            yield ("\n\nSistem Memotong Eksekusi Paksa:\nProses analisis data terlalu panjang dan berputar-putar")
        else:
            logger.error(f"Sistem Error: {str(e)}")
            yield f"\n\n[Sistem Error]: {str(e)}"

thread_id_var: ContextVar[str] = ContextVar("thread_id_var")
@app.post("/chat")
async def chat_endpoint(
    request: Request,
    response: Response,
    message: str = Form(...),
    file: UploadFile | None = File(None)
):

    thread_id = request.cookies.get("thread_id")
    if not thread_id:
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
        response.set_cookie(
            key="thread_id",
            value=thread_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 3
        )

    thread_id_var.set(thread_id)

    if validate_prompt_injection(message):
        logger.error(f"PERINGATAN: Prompt Injection terdeteksi pada input: '{message}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permintaan ditolak: Terdeteksi indikasi Prompt Injection"
        )
    
    saved_filename = None
    ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".pdf", ".docx"}

    if file and file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File type not allowed"
            )
        
        saved_filename = file.filename.strip()
        file_path = DATA_DIR / saved_filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file,buffer)

    async def safe_stream_wrapper():
        try:
            async for chunk in stream_agent_response(
                user_input=message,
                thread_id=thread_id,
                filename=saved_filename
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Stream Error: {str(e)}")
            yield f"\n\n[Sistem Error]: {str(e)}"
    logger.info(f"THREAD ID: {thread_id}")

    return StreamingResponse(
        safe_stream_wrapper(),
        media_type="text/event-stream"
    )

# @app.post("/chat")
# async def chat_endpoint(
#     message: str = Form(...),
#     thread_id: str = Form(...),
#     file: UploadFile | None = File(None)
# ):
#     if validate_prompt_injection(message):
#         logger.error(f"PERINGATAN: Prompt Injection terdeteksi pada input: '{message}'")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Permintaan ditolak: Terdeteksi indikasi Prompt Injection"
#         )
    
#     saved_filename = None

#     ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".pdf", ".docx"}

#     if file and file.filename:
#         ext = Path(file.filename).suffix.lower()
#         if ext not in ALLOWED_EXTENSIONS:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="File type not allowed"
#             )
        
#         saved_filename = file.filename.strip()

#         file_path = DATA_DIR / saved_filename

#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(
#                 file.file,
#                 buffer
#             )

#     return StreamingResponse(
#         stream_agent_response(
#             user_input=message,
#             thread_id=thread_id,
#             filename=saved_filename
#         ),
#         media_type="text/event-stream"
#     )

@app.get("/")
def read_root():
    return {"message": "MCP Server connected to Grafana Cloud!"}
import asyncio
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
import re
import shutil
import math
import uuid
import time
from contextvars import ContextVar
from agent import get_active_agent, init_agent, shutdown_agent
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from opentelemetry import trace, metrics 
from opentelemetry.trace import Status, StatusCode
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
from guardrails.topic_classifier import check_topic

load_dotenv()

resource = Resource.create(attributes={
    "service.name": "mcp-monitoring",
    "deployment.environment.name": "development"})

otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
raw_headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
headers_dict = {}

if raw_headers:
    for item in raw_headers.split(","):
        if "=" in item:
            key, val = item.split("=", 1)
            headers_dict[key.strip()] = val.strip()

if not otlp_endpoint:
    raise ValueError("OTEL_EXPORTER_OTLP_ENDPOINT belum dikonfigurasi")

trace_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(trace_provider)
trace_exporter = OTLPSpanExporter(
    endpoint=f"{otlp_endpoint}/v1/traces",
    headers=headers_dict)
trace_provider.add_span_processor(
    BatchSpanProcessor(trace_exporter))

meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[
        PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=f"{otlp_endpoint}/v1/metrics",
                headers=headers_dict))])
metrics.set_meter_provider(meter_provider)

tracer = trace.get_tracer("mcp-monitoring")
meter = metrics.get_meter("mcp-monitoring")

tool_calls = meter.create_counter(
    name="mcp.tool.calls",
    description="Total MCP tool calls",
    unit="1")

tool_errors = meter.create_counter(
    name="mcp.tool.errors",
    description="Total MCP tool errors",
    unit="1")

tool_duration = meter.create_histogram(
    name="mcp.tool.duration",
    description="MCP tool execution duration",
    unit="s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_agent()
    try:
        yield
    finally:
        await shutdown_agent()
        trace_provider.force_flush()
        meter_provider.force_flush()
        trace_provider.shutdown()
        meter_provider.shutdown()

app = FastAPI(lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)

OUTPUT_DIR = Path("output_grafik")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/output",
    StaticFiles(directory=str(OUTPUT_DIR)),
    name="output")

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
    "execute_sales_python_analysis"}

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
    timeout_seconds=60):

    async def collect_events():
        events = []
        async for event in agent.astream_events(
            inputs,
            config=config,
            version="v2"):

            events.append(event)

        return events

    return await asyncio.wait_for(
        collect_events(),
        timeout=timeout_seconds)

async def stream_agent_response(
    user_input: str,
    thread_id: str,
    filename: str | None = None):

    start_time = time.perf_counter()
    TIMEOUT_SECONDS = 300

    try:
        probability = await asyncio.to_thread(check_topic, user_input)

        if(
            isinstance(probability, bool)
            or not isinstance(probability, (int, float))
            or not math.isfinite(probability)
            or not 0 <= probability <= 1):

            raise ValueError("Invalid topic probability")
        logger.info(f"Topic probability: {probability:.4f}")

    except Exception as e:
        logger.error(f"Topic Control Error: {e}")
        yield("Maaf, pemeriksaan topik sedang mengalami gangguan")

        return

    if probability < 0.50:
        logger.info("Permintaan ditolak karena diluar topik")
        yield("Maaf saya hanya dapat membantu pertanyaan seputar Transmisi Tower Listrik")
        
        return
        
    agent = get_active_agent()
    messages = []
    tool_runs = {}

    if filename:
        messages.append((
            "system",
            f"[INFO SISTEM]: Pengguna mengunggah file '{filename}'.\n"
            f"Gunakan `get_dataset_schema(filename='{filename}')` jika perlu"))

    messages.append(("user", user_input))
    inputs = {"messages": messages}
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 19}

    try:
        async for event in agent.astream_events(
            inputs,
            config=config,
            version="v2"):

            event_type = event.get("event")
            tool_name = event.get("name", "unknown_tool")
            run_id = str(event.get("run_id", ""))
            data = event.get("data", {})
            if event_type == "on_tool_start":
                span = tracer.start_span(
                    name=f"mcp.tool.{tool_name}")
                span.set_attribute(
                    "mcp.tool.name", tool_name)
                span.set_attribute(
                    "mcp.tool.run_id", run_id)
                tool_runs[run_id] = {
                    "span": span,
                    "start_time": time.perf_counter(),
                    "tool_name": tool_name}

                tool_input = data.get("input", {})
                logger.info(f"TOOL INPUT: {tool_input}")

            elif event_type == "on_tool_end":
                run = tool_runs.pop(run_id, None)
                tool_output = data.get("output", {})
                logger.info(f"TOOL OUTPUT: {tool_output}")

                def extract_tool_text(output):
                    content = getattr(output, "content", output)

                    if isinstance(content, str):
                        return content

                    if isinstance(content, list):
                        return "\n".join(
                            item.get("text", "")
                            for item in content
                            if isinstance(item, dict)
                            and item.get("type") == "text")

                    return ""

                if run:
                    duration = (time.perf_counter() - run["start_time"])
                    attributes = {
                        "mcp.tool.name": run["tool_name"],
                        "mcp.tool.status": "success"}

                    run["span"].set_attribute(
                        "mcp.tool.status",
                        "success")

                    run["span"].end()
                    tool_calls.add(1, attributes)
                    tool_duration.record(
                        duration, attributes)

                    logger.info(
                        f"MCP TOOL SELESAI: "
                        f"{run['tool_name']} "
                        f"(Durasi: {duration:.2f} detik)")

            elif event_type == "on_tool_error":
                run = tool_runs.pop(run_id, None)
                error = data.get("error")
                if run:
                    duration = (time.perf_counter() - run["start_time"])
                    attributes = {
                        "mcp.tool.name": run["tool_name"],
                        "mcp.tool.status": "error"}

                    run["span"].set_attribute(
                        "mcp.tool.status",
                        "error")

                    if error:
                        run["span"].set_attribute(
                            "error.message",
                            str(error)[:500])

                        if isinstance(error, BaseException):
                            run["span"].record_exception(error)

                    run["span"].set_status(
                        Status(StatusCode.ERROR))
                    run["span"].end()
                    tool_calls.add(1, attributes)
                    tool_errors.add(1, attributes)
                    tool_duration.record(
                        duration, attributes)

                    logger.error(
                        f"MCP TOOL ERROR: "
                        f"{run['tool_name']} - {error}")

            elif event_type == "on_chat_model_stream":
                content = data["chunk"].content
                if content:
                    yield content

            elapsed = time.perf_counter() - start_time
            if elapsed > TIMEOUT_SECONDS:
                logger.warning(
                    f"PERINGATAN: Agent timeout "
                    f"setelah {TIMEOUT_SECONDS} detik")

                yield (
                    f"\n\n[Sistem]: Proses analisis "
                    f"dihentikan karena melebihi "
                    f"batas waktu {TIMEOUT_SECONDS} detik")

                break

    except Exception as e:
        if "recursion limit" in str(e).lower():
            logger.warning(
                "PERINGATAN SISTEM: Agent dihentikan "
                "karena recursion limit")
            
            yield (
                "\n\nSistem Memotong Eksekusi Paksa:\n"
                "Proses analisis data terlalu panjang "
                "dan berputar-putar")

        else:
            logger.error(
                f"Sistem Error: {str(e)}")
            
            yield f"\n\n[Sistem Error]: {str(e)}"

    finally:
        for run_id, run in list(tool_runs.items()):
            duration = (time.perf_counter() - run["start_time"])

            attributes = {
                "mcp.tool.name": run["tool_name"],
                "mcp.tool.status": "interrupted"}

            run["span"].set_attribute(
                "mcp.tool.status", "interrupted")
            run["span"].end()

            tool_calls.add(1, attributes)
            tool_duration.record(
                duration, attributes)

            logger.warning(
                f"MCP TOOL INTERRUPTED: "
                f"{run['tool_name']} "
                f"(Durasi: {duration:.2f} detik)")

        tool_runs.clear()

thread_id_var: ContextVar[str] = ContextVar("thread_id_var")
@app.post("/chat")
async def chat_endpoint(
    request: Request,
    response: Response,
    message: str = Form(...),
    file: UploadFile | None = File(None)):

    thread_id = request.cookies.get("thread_id")
    if not thread_id:
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
        response.set_cookie(
            key="thread_id",
            value=thread_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 3)

    thread_id_var.set(thread_id)

    if validate_prompt_injection(message):
        logger.error(f"PERINGATAN: Prompt Injection terdeteksi pada input: '{message}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permintaan ditolak: Terdeteksi indikasi Prompt Injection")
    
    saved_filename = None
    ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".pdf", ".docx"}

    if file and file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File type not allowed")
        
        saved_filename = file.filename.strip()
        file_path = DATA_DIR / saved_filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file,buffer)

    async def safe_stream_wrapper():
        try:
            async for chunk in stream_agent_response(
                user_input=message,
                thread_id=thread_id,
                filename=saved_filename):

                yield chunk
        except Exception as e:
            logger.error(f"Stream Error: {str(e)}")
            yield f"\n\n[Sistem Error]: {str(e)}"
    logger.info(f"THREAD ID: {thread_id}")

    return StreamingResponse(
        safe_stream_wrapper(),
        media_type="text/event-stream")

@app.get("/")
def read_root():
    return {"message": "MCP Server connected to Grafana Cloud!"}
import asyncio
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
import re
import math
import uuid
import time
from contextvars import ContextVar
from agent import get_active_agent, init_agent, shutdown_agent, trim_agent_history
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from opentelemetry import trace, metrics 
from opentelemetry.trace import Status, StatusCode
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (OTLPSpanExporter)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from guardrails.topic_classifier import check_topic, extract_file_content

load_dotenv()

resource = Resource.create(attributes={
    "service.name": os.getenv("OTEL_SERVICE_NAME"),
    "deployment.environment.name": os.getenv("OTEL_ENVIRONMENT_NAME")})

otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
raw_headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
headers_dict = {}

if raw_headers:
    for item in raw_headers.split(","):
        if "=" in item:
            key, val = item.split("=", 1)
            headers_dict[key.strip()] = val.strip()

if not otlp_endpoint.startswith(("http://", "https://")):
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

tracer = trace.get_tracer(os.getenv("OTEL_SERVICE_NAME"))
meter = metrics.get_meter(os.getenv("OTEL_SERVICE_NAME"))

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
    try:
        await init_agent()
        yield

    finally:
        try:
            await shutdown_agent()
        finally:
            await asyncio.to_thread(trace_provider.force_flush)
            await asyncio.to_thread(meter_provider.force_flush)
            await asyncio.to_thread(trace_provider.shutdown)
            await asyncio.to_thread(meter_provider.shutdown)

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
  file_handler = logging.FileHandler("app_monitoring.log", mode="a")
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

def log_stage(
    request_id: str,
    stage: str,
    started_at: float,
    status: str = "success",
    **details
):
    """Catat durasi sebuah tahapan pipeline."""
    duration = time.perf_counter() - started_at
    detail_text = " ".join(
        f"{key}={value}"
        for key, value in details.items())

    logger.info(
        f"PIPELINE | request_id={request_id} | "
        f"stage={stage} | status={status} | "
        f"duration={duration:.3f}s"
        + (f" | {detail_text}" if detail_text else ""))

def extract_token_usage(output):
    if output is None:
        return None

    usage = getattr(output, "usage_metadata", None)

    if usage:
        return {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens")
        }

    response_metadata = getattr(output, "response_metadata", {}) or {}
    usage = response_metadata.get("token_usage") or response_metadata.get("usage") or {}

    if usage:
        input_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
        output_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
        total_tokens = usage.get("total_tokens")

        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens
        }

    return None

def validate_prompt_injection(user_input: str):
    for pattern in COMPILED_INJECTION_REGEX:
        if pattern.search(user_input):
            return True
    return False

async def iterate_with_timeout(async_iterable, timeout):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    iterator = async_iterable.__aiter__()

    try:
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError

            try:
                event = await asyncio.wait_for(
                    iterator.__anext__(),
                    timeout=remaining)
            except StopAsyncIteration:
                break

            yield event
    finally:
        aclose = getattr(iterator, "aclose", None)
        if aclose:
            await aclose()

async def stream_agent_response(
    user_input: str,
    thread_id: str,
    filename: str | None = None,
    topic_probability: float | None = None,
    request_id: str | None = None
):
    if (
        isinstance(topic_probability, bool)
        or not isinstance(topic_probability, (int, float))
        or not math.isfinite(topic_probability)
        or not 0 <= topic_probability <= 1
    ):
        raise ValueError("Invalid topic probability")

    if topic_probability < 0.50:
        logger.info(
            f"GUARDRAIL REJECTED | request_id={request_id} | "
            f"probability={topic_probability:.4f}")
        yield "Maaf saya hanya dapat membantu pertanyaan seputar Transmisi Tower Listrik"
        return

    logger.info(
        f"GUARDRAIL PASSED | request_id={request_id} | "
        f"probability={topic_probability:.4f}")

    TIMEOUT_SECONDS = 300
    agent_started = time.perf_counter()
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
        "recursion_limit": 12}

    first_token_logged = False
    model_runs = {}

    token_totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0
    }

    llm_call_count = 0
    llm_usage_missing = 0

    try:
        await trim_agent_history(config)
        
        async for event in iterate_with_timeout(
            agent.astream_events(
                inputs,
                config=config,
                version="v2"
            ),
            TIMEOUT_SECONDS
        ):
            event_type = event.get("event")
            tool_name = event.get("name", "unknown_tool")
            run_id = str(event.get("run_id", ""))
            data = event.get("data", {})

            if event_type == "on_tool_start":
                tool_started = time.perf_counter()
                span = tracer.start_span(name=f"mcp.tool.{tool_name}")
                span.set_attribute("mcp.tool.name", tool_name)
                span.set_attribute("mcp.tool.run_id", run_id)

                tool_runs[run_id] = {
                    "span": span,
                    "start_time": tool_started,
                    "tool_name": tool_name}

                tool_input = data.get("input", {})
                input_keys = (
                    list(tool_input.keys())
                    if isinstance(tool_input, dict)
                    else [])

                logger.info(
                    f"MCP TOOL START | request_id={request_id} | "
                    f"tool={tool_name} | run_id={run_id} | "
                    f"input_keys={input_keys}")

            elif event_type == "on_chat_model_start":
                model_run_id = str(event.get("run_id", ""))

                model_name = (
                    event.get("metadata", {}).get("ls_model_name")
                    or "unknown")

                model_runs[model_run_id] = {
                    "start_time": time.perf_counter(),
                    "model_name": model_name}

                logger.info(
                    f"LLM START | request_id={request_id} | "
                    f"run_id={model_run_id} | model={model_name}")

            elif event_type == "on_chat_model_end":
                model_run_id = str(event.get("run_id", ""))
                run = model_runs.pop(model_run_id, None)

                if run:
                    duration = time.perf_counter() - run["start_time"]

                    output = data.get("output")

                    actual_model = (
                        getattr(output, "response_metadata", {}).get("model_name")
                        or getattr(output, "response_metadata", {}).get("model")
                        or run["model_name"]
                    )

                    usage = extract_token_usage(output)

                    if usage:
                        input_tokens = usage["input_tokens"]
                        output_tokens = usage["output_tokens"]
                        total_tokens = usage["total_tokens"]

                        if input_tokens is not None:
                            token_totals["input_tokens"] += input_tokens

                        if output_tokens is not None:
                            token_totals["output_tokens"] += output_tokens

                        if total_tokens is not None:
                            token_totals["total_tokens"] += total_tokens

                        logger.info(
                            f"LLM TOKEN USAGE | request_id={request_id} | "
                            f"run_id={model_run_id} | model={actual_model} | "
                            f"input_tokens={input_tokens} | "
                            f"output_tokens={output_tokens} | "
                            f"total_tokens={total_tokens}"
                        )

                    else:
                        llm_usage_missing += 1

                        logger.warning(f"LLM TOKEN USAGE MISSING | request_id={request_id} | run_id={model_run_id} | model={actual_model}")

                    llm_call_count += 1

                    logger.info(f"LLM END | request_id={request_id} | run_id={model_run_id} | model={actual_model} | duration={duration:.3f}s")

            elif event_type == "on_chat_model_error":
                model_run_id = str(event.get("run_id", ""))
                run = model_runs.pop(model_run_id, None)

                logger.error(f"LLM ERROR | request_id={request_id} | run_id={model_run_id} | error={str(event.get('data', {}).get('error'))[:500]}")

            elif event_type == "on_tool_end":
                run = tool_runs.pop(run_id, None)

                if run:
                    duration = time.perf_counter() - run["start_time"]
                    attributes = {
                        "mcp.tool.name": run["tool_name"],
                        "mcp.tool.status": "success"}

                    run["span"].set_attribute("mcp.tool.status", "success")
                    run["span"].end()
                    tool_calls.add(1, attributes)
                    tool_duration.record(duration, attributes)

                    logger.info(f"MCP TOOL END | request_id={request_id} | tool={run['tool_name']} | run_id={run_id} | duration={duration:.3f}s | status=success")

                else:
                    logger.warning(f"MCP TOOL END WITHOUT START | request_id={request_id} | tool={tool_name} | run_id={run_id}")

            elif event_type == "on_tool_error":
                run = tool_runs.pop(run_id, None)
                error = data.get("error")

                if run:
                    duration = time.perf_counter() - run["start_time"]
                    attributes = {
                        "mcp.tool.name": run["tool_name"],
                        "mcp.tool.status": "error"}

                    run["span"].set_attribute("mcp.tool.status", "error")
                    if error:
                        run["span"].set_attribute(
                            "error.message",
                            str(error)[:500])
                        if isinstance(error, BaseException):
                            run["span"].record_exception(error)

                    run["span"].set_status(Status(StatusCode.ERROR))
                    run["span"].end()
                    tool_calls.add(1, attributes)
                    tool_errors.add(1, attributes)
                    tool_duration.record(duration, attributes)

                    logger.error(f"MCP TOOL ERROR | request_id={request_id} | tool={run['tool_name']} | run_id={run_id} | duration={duration:.3f}s | error={str(error)[:500]}")
                
                else:
                    logger.error(f"MCP TOOL ERROR WITHOUT START | request_id={request_id} | tool={tool_name} | run_id={run_id} | error={str(error)[:500]}")

            elif event_type == "on_chat_model_stream":
                chunk = data.get("chunk")
                content = getattr(chunk, "content", None)

                if content and not first_token_logged:
                    first_token_logged = True
                    log_stage(
                        request_id or "unknown",
                        "first_model_token",
                        agent_started)

                if isinstance(content, str):
                    if content:
                        yield content
                elif isinstance(content, list):
                    for block in content:
                        if (
                            isinstance(block, dict)
                            and block.get("type") == "text"
                            and block.get("text")
                        ):
                            yield block["text"]

    except asyncio.TimeoutError:
        logger.warning(f"AGENT TIMEOUT | request_id={request_id} | timeout={TIMEOUT_SECONDS}s")
        yield "\n[Sistem]: Proses analisis dihentikan karena melebihi batas waktu"

    except Exception as e:
        if "recursion limit" in str(e).lower():
            logger.warning(f"AGENT RECURSION LIMIT | request_id={request_id}")
            yield (
                "\n\nSistem Memotong Eksekusi Paksa:\nProses analisis data terlalu panjang dan berputar-putar")
        else:
            logger.exception(f"AGENT ERROR | request_id={request_id}")
            yield f"\n\n[Sistem Error]: {str(e)}"

    finally:
        for run_id, run in list(tool_runs.items()):
            duration = time.perf_counter() - run["start_time"]
            attributes = {
                "mcp.tool.name": run["tool_name"],
                "mcp.tool.status": "interrupted"}

            run["span"].set_attribute(
                "mcp.tool.status",
                "interrupted")
            
            run["span"].end()
            tool_calls.add(1, attributes)
            tool_duration.record(duration, attributes)

            logger.warning(
                f"MCP TOOL INTERRUPTED | request_id={request_id} | "
                f"tool={run['tool_name']} | run_id={run_id} | "
                f"duration={duration:.3f}s")

        tool_runs.clear()

        logger.info(
            f"LLM REQUEST TOKEN SUMMARY | request_id={request_id} | "
            f"llm_calls={llm_call_count} | "
            f"input_tokens={token_totals['input_tokens']} | "
            f"output_tokens={token_totals['output_tokens']} | "
            f"total_tokens={token_totals['total_tokens']} | "
            f"usage_missing={llm_usage_missing}"
        )

        log_stage(
            request_id or "unknown",
            "agent_stream",
            agent_started)

thread_id_var: ContextVar[str] = ContextVar("thread_id_var")

@app.post("/chat")
async def chat_endpoint(
    request: Request,
    message: str = Form(...),
    file: UploadFile | None = File(None)
):
    request_id = uuid.uuid4().hex[:12]
    request_started = time.perf_counter()

    logger.info(
        f"REQUEST START | request_id={request_id} | "
        f"method={request.method} | path={request.url.path}")

    thread_id = request.cookies.get("thread_id")
    is_new_thread = False

    if not thread_id:
        thread_id = f"thread_{uuid.uuid4().hex}"
        is_new_thread = True

    stage_started = time.perf_counter()
    if validate_prompt_injection(message):
        log_stage(
            request_id,
            "prompt_injection_validation",
            stage_started,
            status="rejected")
        
        logger.error(f"PROMPT INJECTION DETECTED | request_id={request_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permintaan ditolak: Terdeteksi indikasi Prompt Injection")

    log_stage(
        request_id,
        "prompt_injection_validation",
        stage_started)

    file_bytes = None
    file_content = ""
    saved_filename = None
    original_filename = None

    ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".pdf", ".docx"}
    MAX_FILE_SIZE = 20 * 1024 * 1024
    MAX_CONTENT_LENGTH = 15000

    if file and file.filename:
        file_stage_started = time.perf_counter()

        try:
            original_filename = Path(
                file.filename.replace("\\", "/")
            ).name.strip()

            ext = Path(original_filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                log_stage(
                    request_id,
                    "extract_file",
                    file_stage_started,
                    status="rejected",
                    reason="unsupported_extension")
                raise HTTPException(
                    status_code=400,
                    detail="Format file tidak didukung")

            file_bytes = await file.read(MAX_FILE_SIZE + 1)
            if len(file_bytes) > MAX_FILE_SIZE:
                log_stage(
                    request_id,
                    "extract_file",
                    file_stage_started,
                    status="rejected",
                    reason="file_too_large",
                    file_size=len(file_bytes))
                raise HTTPException(
                    status_code=413,
                    detail="Ukuran file maksimal 20 MB")

            file_content = extract_file_content(
                file_bytes,
                original_filename)
            
            file_content = file_content[:MAX_CONTENT_LENGTH]

            log_stage(
                request_id,
                "extract_file",
                file_stage_started,
                filename=original_filename,
                file_size=len(file_bytes),
                extracted_chars=len(file_content))

        except HTTPException:
            raise
        except Exception:
            log_stage(
                request_id,
                "extract_file",
                file_stage_started,
                status="error")
            logger.exception(
                f"FILE EXTRACTION ERROR | request_id={request_id}")
            raise HTTPException(
                status_code=422,
                detail="Isi file tidak dapat dibaca atau format file tidak valid")
        finally:
            await file.close()

    topic_input = f"""CURRENT USER MESSAGE:
    {message}

    UPLOADED FILE CONTENT:
    {file_content if file_content else "Tidak ada file yang diunggah."}
    """

    guardrail_input_started = time.perf_counter()
    log_stage(
        request_id,
        "build_guardrail_input",
        guardrail_input_started,
        input_length=len(topic_input),
        message_length=len(message),
        file_content_length=len(file_content))

    guardrail_started = time.perf_counter()
    try:
        topic_probability = await asyncio.to_thread(
            check_topic,
            topic_input)

        if (
            isinstance(topic_probability, bool)
            or not isinstance(topic_probability, (int, float))
            or not math.isfinite(topic_probability)
            or not 0 <= topic_probability <= 1
        ):
            raise ValueError("Invalid topic probability")

        guardrail_status = ("success" if topic_probability >= 0.50 else "rejected")

        log_stage(
            request_id,
            "check_guardrail",
            guardrail_started,
            status=guardrail_status,
            probability=f"{topic_probability:.4f}",
            input_length=len(topic_input))

    except Exception:
        log_stage(
            request_id,
            "check_guardrail",
            guardrail_started,
            status="error")

        logger.exception(f"GUARDRAIL ERROR | request_id={request_id}")
        raise HTTPException(status_code=503, detail="Pemeriksaan topik sedang mengalami gangguan")

    if topic_probability >= 0.50 and file_bytes is not None:
        save_started = time.perf_counter()

        saved_filename = (f"{uuid.uuid4().hex}_{original_filename}")
        file_path = DATA_DIR / saved_filename

        try:
            with open(file_path, "wb") as buffer:
                buffer.write(file_bytes)

            log_stage(
                request_id,
                "save_uploaded_file",
                save_started,
                file_size=len(file_bytes))
            
        except Exception:
            log_stage(
                request_id,
                "save_uploaded_file",
                save_started,
                status="error")
            
            logger.exception(f"SAVE FILE ERROR | request_id={request_id}")
            raise HTTPException(
                status_code=500,
                detail="File gagal disimpan")

    async def safe_stream_wrapper():
        token = thread_id_var.set(thread_id)
        stream_started = time.perf_counter()

        logger.info(
            f"AGENT START | request_id={request_id} | "
            f"thread_id={thread_id}")

        try:
            async for chunk in stream_agent_response(
                user_input=message,
                thread_id=thread_id,
                filename=saved_filename,
                topic_probability=topic_probability,
                request_id=request_id
            ):
                yield chunk

        except Exception:
            logger.exception(f"STREAM ERROR | request_id={request_id}")
            yield "\n\n[Sistem Error]: Terjadi kesalahan saat memproses permintaan"

        finally:
            log_stage(
                request_id,
                "agent_stream_wrapper",
                stream_started)
            
            log_stage(
                request_id,
                "total_request",
                request_started)

            logger.info(f"REQUEST FINISHED | request_id={request_id}")
            thread_id_var.reset(token)

    streaming_response = StreamingResponse(
        safe_stream_wrapper(),
        media_type="text/event-stream")

    if is_new_thread:
        streaming_response.set_cookie(
            key="thread_id",
            value=thread_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 3)

    logger.info(
        f"THREAD ID | request_id={request_id} | "
        f"thread_id={thread_id}")

    return streaming_response

@app.get("/")
def read_root():
    return {"message": "MCP Server connected to Grafana Cloud!"}
import io
import contextlib
import pandas as pd
import numpy as np
import textwrap
import modal
import time
import asyncio
import logging
from services_mcp.isolator_clean_service import get_isolator_clean_df

logger = logging.getLogger(__name__)
MODAL_APP_NAME = "si-smart-sandbox"

MODAL_IMAGE = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "pandas",
        "numpy",
        "matplotlib",
        "seaborn"
    )
)

SANDBOX_TIMEOUT = 180
EXECUTION_TIMEOUT = 120
SANDBOX_CPU = 0.5
SANDBOX_MEMORY = 1024
MAX_DATA_SIZE = 100 * 1024 * 1024

ISOLATOR_CLEAN_DF = None
ISOLATOR_CLEAN_LOCK = asyncio.Lock()

async def _get_cached_isolator_clean_df() -> pd.DataFrame:
    global ISOLATOR_CLEAN_DF

    async with ISOLATOR_CLEAN_DF:
        if (
            ISOLATOR_CLEAN_DF is None 
            or ISOLATOR_CLEAN_DF.empty
        ):
            logger.info("Fetching dataset")
            ISOLATOR_CLEAN_DF = (await get_isolator_clean_df())

    return ISOLATOR_CLEAN_DF.copy()

def register_isolator_clean_tools(mcp):

    @mcp.tool()
    async def execute_isolator_clean_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL PEMBERSIHAN ISOLATOR menggunakan E2B Sandbox
        
        DataFrame tersedia dalam variabel df
        WAJIB menggunakan print(...) untuk melihat output
        
        Eksekusi Python dilakukan di lingkungan sandbox terisolasi
        """

        # sandbox = None
        sb = None
        started_at = time.perf_counter()

        try:
            logger.info("Getting dataset")
            df_isolator_clean = await _get_cached_isolator_clean_df()

            if df_isolator_clean.empty:
                return "Data detail pembersihan isolator kosong"

            json_data = df_isolator_clean.to_json(
                orient="records",
                date_format="iso",
                force_ascii=False
            )

            data_size = len(json_data.encode("utf-8"))

            if data_size > MAX_DATA_SIZE:
                return (f"Dataset isolator clean terlalu besar ({data_size / 1024 / 1024:.2f} MB)")

            logger.info("Dataset ready | rows=%s | size=%s bytes", len(df_isolator_clean), data_size)
            code = code.strip()
            if code.startswith("```"):
                lines = code.splitlines()
                lines = lines[1:]

                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]

                code = "\n".join(lines)

            execution_script = f'''
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_json(
"/tmp/isolator_change_data.json",
orient="records"
)

print("Jumlah baris:", len(df))
print("Jumlah kolom:", len(df.columns))
print("Kolom:", df.columns.tolist())
print()

{code}
'''
            logger.info("MODAL | Looking up app")
            sb_app = await modal.App.lookup.aio(
                MODAL_APP_NAME,
                create_if_missing=True
            )

            logger.info("MODAL | Creating sandbox")
            sb = await modal.Sandbox.create.aio(
                app=sb_app,
                image=MODAL_IMAGE,
                cpu=SANDBOX_CPU,
                memory=SANDBOX_MEMORY,
                timeout=SANDBOX_TIMEOUT,
                block_network=True
            )

            logger.info("MODAL | Sandbox created")

            await sb.filesystem.write_text.aio(json_data, "/tmp/isolator_change_data.json")
            await sb.filesystem.write_text.aio(execution_script, "/tmp/analysis.py")
            logger.info("MODAL | Dataset and script uploaded")
            logger.info("MODAL | Validating python syntax")

            check = await sb.exec.aio(
                "python",
                "-m",
                "py_compile",
                "/tmp/analysis.py",
                timeout=20
            )

            check_stdout = await check.stdout.read.aio()
            check_stderr = await check.stderr.read.aio()
            check_returncode = await check.wait.aio()

            if check_returncode != 0:
                return(f"Python syntaxError: {check_stderr or check_stdout}")

            logger.info("MODAL | Executing analysis")

            process = await sb.exec.aio(
                "python",
                "/tmp/analysis.py",
                timeout=EXECUTION_TIMEOUT
            )

            stdout, stderr, returncode = await asyncio.gather(
                process.stdout.read.aio(),
                process.stderr.read.aio(),
                process.wait.aio()
            )

            duration = time.perf_counter() - started_at
            logger.info("MODAL | Execution completed | returncode=%s | duration=%.2fs", returncode, duration)

            if returncode != 0:
                return (f"Error executing isolator clean analysis. Details:n{stderr or stdout}")

            output = stdout.strip()

            if not output:
                output = "Kode berhasil diekseskusi tanpa output print"

            return(f"{output}\n\nExecution time: {duration:.2f} seconds")

        except Exception as e:
            logger.exception("Modal execution failed")

            return(f"Error executing python code: ({type(e).__name__}): {str(e)}")

        finally:
            if sb is not None:
                try:
                    await sb.terminate.aio()
                    logger.info("MODAL | Sandbox terminated")

                except Exception:
                    logger.exception("MODAL | Failed to terminate sandbox")

    return mcp

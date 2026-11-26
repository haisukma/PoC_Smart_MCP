import time
import modal
import logging
import asyncio
import pandas as pd
import numpy as np
from services_mcp.pondasi_leveling_detail_service import get_pondasi_leveling_detail_df

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
SANDBOX_MEMORY = 1024
SANDBOX_CPU = 0.5
MAX_DATA_SIZE = 100 * 1024 * 1024

PONDASI_LEVELING_DETAIL_DF = None
PONDASI_LEVELING_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_pondasi_leveling_detail_df() -> pd.DataFrame:
    global PONDASI_LEVELING_DETAIL_DF

    async with PONDASI_LEVELING_DETAIL_LOCK:
        if (PONDASI_LEVELING_DETAIL_DF is None 
            or PONDASI_LEVELING_DETAIL_DF.empty
        ):
            logger.info("Fetching dataset")
            PONDASI_LEVELING_DETAIL_DF = await get_pondasi_leveling_detail_df()

    return PONDASI_LEVELING_DETAIL_DF.copy()

def register_pondasi_leveling_detail_tools(mcp):

    @mcp.tool()
    async def execute_pondasi_leveling_detail_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL PENGUKURAN LEVELING PONDASI TOWER
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        sb = None
        started_at = time.perf_counter()

        try:

            logger.info("Getting dataset")
            df_pondasi_leveling = await _get_cached_pondasi_leveling_detail_df()
            if df_pondasi_leveling.empty:
                return "Data pondasi leveling report kosong"

            json_data = df_pondasi_leveling.to_json(
                orient="records",
                data_format="iso",
                force_ascii=False
            )

            data_size = len(json_data.encode("utf-8"))

            if data_size > MAX_DATA_SIZE:
                return(f"Dataset pondasi leveling terlalu besar ({data_size / 1024 / 1024:.2f} MB)")

            logger.info("Dataset ready | rows=%s | size=%s bytes", len(df_pondasi_leveling), data_size)

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
matplotlibe.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_json(
    "/tmp/pondasi_leveling_data.json",
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

            await sb.filesystem.write_text.aio(json_data, "/tmp/pondasi_leveling_data.json")
            await sb.filesystem.write_text.aio(execution_script, "/tmp/analysis.py")
            logger.info("MODAL | Dataset and scrip uploaded")
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
                return (f"Error executing pondasi leveling analysis. Detail:\n{stderr or stdout}")

            output = stdout.strip()

            if not output:
                output = "Kode berhasil dieksekusi tanpa output print"

            return(f"{output}\n\nExecution time: {duration:.2f} seconds")

        except Exception as e:
            logger.info("Modal execution failed")

            return (f"Error executing python code: ({type(e).__name__}): {str(e)}")

        finally:
            if sb is not None:
                try:
                    await sb.terminate.aio()
                    logger.info("MODAL | Sandbox terminate")

                except Exception:
                    logger.exception("MODAL | Failed to terminate sandbox")

    return mcp

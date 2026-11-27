import asyncio
import logging
import io
import time
import pandas as pd
import modal
from services_mcp.verticality_detail_service import get_verticality_detail_df

logger = logging.getLogger(__name__)
MODAL_APP_NAME = "si-smart-sandbox"

MODAL_IMAGE = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "pandas",
        "numpy",
        "matplotlib",
        "seaborn",
        "pyarrow"
    )
)

SANDBOX_TIMEOUT = 180
EXECUTION_TIMEOUT = 120
SANDBOX_CPU = 1.0
SANDBOX_MEMORY = 1024
MAX_DATA_SIZE = 100 * 1024 * 1024

VERTICALITY_DETAIL_DF = None
VERTICALITY_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_verticality_detail_df() -> pd.DataFrame:
    global VERTICALITY_DETAIL_DF

    async with VERTICALITY_DETAIL_LOCK:
        if (
            VERTICALITY_DETAIL_DF is None
            or VERTICALITY_DETAIL_DF.empty
        ):
            logger.info("Fetching dataset")
            VERTICALITY_DETAIL_DF = (await get_verticality_detail_df())

        return VERTICALITY_DETAIL_DF.copy()

def register_verticality_detail_tools(mcp):

    @mcp.tool()
    async def execute_verticality_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL PENGUKURAN KEMIRINGAN atau VERTICALITY TOWER
        
        Kolom yang tersedia di df: [TBLNAME, IDUNIT, UPT, IDULTG, IDGARDU, GI, IDLINE, PENGHANTAR, IDLOC,
        LOKASI, NAMA_KEGIAtAN, TANGGAL, PARAMDATE, INSPECTIONDATE, IDSCH, IDINSPECTION, IDGROUNDPATROL, DIUKUR_OLEH,
        TYPE_TOWER, PENGUKURAN, TIPE_TOWER, TINGGI_TOWER, PENGUKURAN_NILAI_DEFORMASI, TENSION, SUSPENSION, ROWNUMID]
        WAJIB menggunakan print(...) untuk melihat output

        Eksekusi python dilakukan di lingkungan sandbox terisolasi
        """

        sb = None
        started_at = time.perf_counter()
        try:
            logger.info("Getting dataset")
            df_verticality = await _get_cached_verticality_detail_df()

            if df_verticality.empty:
                return "Data verticality report kosong"

            parquet_buffer = io.BytesIO()
            df_verticality.to_parquet(parquet_buffer, index=False, engine="pyarrow")
            parquet_bytes = parquet_buffer.getvalue()

            data_size = len(parquet_bytes)
            if data_size > MAX_DATA_SIZE:
                return f"Dataset verticality terlalu besar ({data_size / 1024 / 1024:.2f} MB)"

            logger.info("Dataset ready | rows=%s | size=%s bytes", len(df_verticality), data_size)

            code = code.strip()
            if code.startswith("```"):
                lines = code.splitlines()[1:]
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

df = pd.read_parquet("/tmp/verticality_data.parquet")
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

            await asyncio.gather(
                sb.filesystem.write_bytes.aio(remote_path="/tmp/verticality_data.parquet", data=parquet_bytes),
                sb.filesystem.write_text.aio(execution_script, "/tmp/analysis.py")
            )
            logger.info("MODAL | Dataset and script uploaded")

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
                return f"CODE_ERROR: Kode Python gagal dieksekusi. Perbaiki kode berikut berdasarkan error:\n{stderr or stdout}"

            output = stdout.strip()
            if not output:
                output = "Kode berhasil dieksekusi tanpa output print."

            return f"{output}\n\nExecution time: {duration:.2f} seconds"

        except Exception as e:
            logger.exception("Modal infrastructure/system execution failed")
            return ("SYSTEM_ERROR: Terjadi gangguan sementara pada sistem sandbox saat memproses permintaan")

        finally:
            if sb is not None:
                try:
                    await sb.terminate.aio()
                    logger.info("MODAL | Sandbox terminated")
                except Exception:
                    logger.exception("MODAL | Failed to terminate sandbox")

    return mcp

# import asyncio
# import logging
# import io
# import contextlib
# import pandas as pd
# import modal
# from services_mcp.verticality_detail_service import get_verticality_detail_df

# logger = logging.getLogger(__name__)

# VERTICALITY_DETAIL_DF = None
# VERTICALITY_DETAIL_LOCK = asyncio.Lock()

# async def _get_cached_verticality_detail_df() -> pd.DataFrame:
#     global VERTICALITY_DETAIL_DF

#     async with VERTICALITY_DETAIL_LOCK:
#         if (
#             VERTICALITY_DETAIL_DF is None
#             or VERTICALITY_DETAIL_DF.empty
#         ):
#             logger.info("Fetching dataset")
#             VERTICALITY_DETAIL_DF = (await get_verticality_detail_df())

#         return VERTICALITY_DETAIL_DF.copy()

# def register_verticality_detail_tools(mcp):

#     @mcp.tool()
#     async def execute_verticality_detail_analysis(code: str) -> str:
#         """
#         Menganalisis data DETAIL PENGUKURAN KEMIRINGAN atau VERTICALITY TOWER
        
#         DataFrame tersedia dalam variabel df.
#         WAJIB menggunakan print(...) untuk melihat output
#         """

#         try:
#             df_verticality = await _get_cached_verticality_detail_df()
#             if df_verticality.empty:
#                 return "Data verticality report kosong"

#             local_vars = {
#                 "df": df_verticality,
#                 "pd": pd
#             }

#             output_buffer = io.StringIO()
#             with contextlib.redirect_stdout(output_buffer):
#                 exec(code, local_vars)

#             result = output_buffer.getvalue()

#             return (
#                 result.strip()
#                 if result.strip()
#                 else "Kode berhasil dieksekusi tanpa output print"
#             )

#         except Exception as e:
#             return f"Error executing Python code: {str(e)}"
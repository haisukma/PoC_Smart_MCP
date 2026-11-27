import io
import contextlib
import asyncio
import pandas as pd
import numpy as np
import time
import logging
import modal
from services_mcp.thermovisi_detail_service import get_thermovisi_detail_df

logger = logging.getLogger(__name__)
MODAL_APP_NAME = "si-smart-sandbox"

MODAL_IMAGE = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "pandas",
        "numpy",
        "seaborn",
        "pyarrow"
    )
)

SANDBOX_TIMEOUT = 180
EXECUTION_TIMEOUT = 120
SANDBOX_CPU = 1.0
SANDBOX_MEMORY = 1024
MAX_DATA_SIZE = 100 * 1024 * 1024

THERMOVISI_DETAIL_DF = None
THERMOVISI_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_thermovisi_detail_df() -> pd.DataFrame:
    global THERMOVISI_DETAIL_DF

    async with THERMOVISI_DETAIL_LOCK:
        if (
            THERMOVISI_DETAIL_DF is None 
            or THERMOVISI_DETAIL_DF.empty
        ):
            logger.info("Fetching dataset")
            THERMOVISI_DETAIL_DF = (await get_thermovisi_detail_df())

    return THERMOVISI_DETAIL_DF.copy()

def register_thermovisi_detail_tools(mcp):

    @mcp.tool()
    async def execute_thermovisi_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL THERMOVISI
        
        Kolom yang tersedia di df: [TBLNAME, IDUNIT, UPT, IDULTG, ULTG, IDGARDU, GI, IDLINE, PENGHANTAR,
        IDLOC, LOKASI, IDEQP, PST, CLAMP, TANGGAL, PARAMDATE, INSPECTIONDATE, IDINSPECTION, ARUS_BEBAN, ARUS_MAKSIMAL,
        D_SUHU_OBJEK_1, D_SUHU_OBJEK_2, D_SUHU_OBJEK_3, D_SUHU_OBJEK_4, J_SUHU_OBJEK_1, J_SUHU_BJEK_2,
        J_SUHU_OBJEK_3, J_SUHU_OBJEK_4, M_SUHU_OBJEK_1, M_SUHU_OBJEK_2, M_SUHU_OBJEK_3, M_SUHU_OBJEK_4, R_SUHU_OBJEK_1,
        R_SUHU_OBJEK_2, R_SUHU_OBJEk_3, R_SUHU_OBJEK_4, JT_SUHU_OBJEK_1, JT_SUHU_OBJEK_2, JT_SUHU_OBJEK_3,
        JT_SUHU_OBJEK_4, D_SUHU_KAWAT_1, D_SUHU_KAWAT_2, D_SUHU_KAWAT_3, D_SUHU_KAWAT_4, J_SUHU_KAWAT_1, J_SUHU_KAWAT_2,
        J_SUHU_KAWAT_3, J_SUHU_KAWAT_4, M_SUHU_KAWAT_1, M_SUHU_KAWAT_2, M_SUHU_KAWAT_3, M_SUHU_KAWAT_4, R_SUHU_KAWAT_1, R_SUHU_KAWAT_2,
        R_SUHU_KAWAT_3, R_SUHU_KAWAT_4, JT_SUHU_KAWAT_1, JT_SUHU_KAWAT_2, JT_SUHU_KAWAT_3, JT_SUHU_KAWAT_4, DELTA_D_1,
        DELTA_D_2, DELTA_D_3, DELTA_D_4, DELTA_J_1, DELTA_J_2, DELTA_J_3, DELTA_J_4, DELTA_M_1, DELTA_M_2, DELTA_M_3, DELTA_M_4,
        DELTA_R_1, DELTA_R_2, DELTA_R_3, DELTA_R_4, DELTA_JT_1, DELTA_JT_2, DELTA_JT_3, DELTA_JT_4, KONDISI, REKOMENDASI,
        FLAG_KONDISI, FLAG_REKOMENDASI, KETERANGAN, ROWNUMID]
        WAJIB menggunakan print(...) untuk melihat output

        Eksekusi python dilakukan dilingkungan sandbox terisolasi
        """

        sb = None
        started_at = time.perf_counter()
        try:
            logger.info("Getting dataset")
            df_thermovisi = await _get_cached_thermovisi_detail_df()
            
            if df_thermovisi.empty:
                return "Data thermovisi report kosong"

            parquet_buffer = io.BytesIO()
            df_thermovisi.to_parquet(parquet_buffer, index=False, engine="pyarrow")
            parquet_bytes = parquet_buffer.getvalue()

            data_size = len(parquet_bytes)
            if data_size > MAX_DATA_SIZE:
                return f"Dataset thermovisi terlalu besar ({data_size / 1024 / 1024:.2f} MB)"

            logger.info("Dataset ready | rows=%s | size=%s bytes", len(df_thermovisi), data_size)

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

df = pd.read_parquet("tmp/thermovisi_data.parquet")
print("Jumlah baris:", len(df))
print("Jumlah kolom:", df.columns)
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
                sb.filesystem.write_bytes.aio(remote_path="/tmp/thermovisi_data.parquet", data=parquet_bytes),
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
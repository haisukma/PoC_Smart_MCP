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

    async with ISOLATOR_CLEAN_LOCK:
        if (
            ISOLATOR_CLEAN_DF is None 
            or ISOLATOR_CLEAN_DF.empty
        ):
            logger.info("Fetching dataset")
            ISOLATOR_CLEAN_DF = (await get_isolator_clean_df())

    return ISOLATOR_CLEAN_DF.copy()

def register_isolator_clean_tools(mcp):

    @mcp.tool()
    async def execute_isolator_clean_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL PEMBERSIHAN ISOLATOR
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_isolator_clean = await _get_cached_isolator_clean_df()
            if df_isolator_clean.empty:
                return "Data isolator clean report kosong"

            local_vars = {
                "df": df_isolator_clean,
                "pd": pd
            }

            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                exec(code, local_vars)

            result = output_buffer.getvalue()

            return (
                result.strip()
                if result.strip()
                else "Kode berhasil dieksekusi tanpa output print"
            )

        except Exception as e:
            return f"Error executing Python code: {str(e)}"
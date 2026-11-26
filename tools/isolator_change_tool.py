import io
import contextlib
import pandas as pd
import numpy as np
import textwrap
import modal
import logging
import asyncio
import time
from services_mcp.isolator_change_service import get_isolator_change_df

logger = logging.getLogger(__name__)

ISOLATOR_CHANGE_DETAIL_DF = None
ISOLATOR_CHANGE_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_isolator_change_detail_df() -> pd.DataFrame:
    global ISOLATOR_CHANGE_DETAIL_DF

    async with ISOLATOR_CHANGE_DETAIL_LOCK:
        if (ISOLATOR_CHANGE_DETAIL_DF is None 
            or ISOLATOR_CHANGE_DETAIL_DF.empty
        ):
            logger.info("Fetching dataset")
            ISOLATOR_CHANGE_DETAIL_DF = (await get_isolator_change_df())

    return ISOLATOR_CHANGE_DETAIL_DF.copy()

def register_isolator_change_tools(mcp):

    @mcp.tool()
    async def execute_isolator_change_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL PENGGANTIAN ISOLATOR
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_isolator_change = await _get_cached_isolator_change_detail_df()
            if df_isolator_change.empty:
                return "Data isolator change report kosong"

            local_vars = {
                "df": df_isolator_change,
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
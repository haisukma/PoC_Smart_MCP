import io
import contextlib
import asyncio
import pandas as pd
import numpy as np
import logging
import modal
from services_mcp.thermovisi_detail_service import get_thermovisi_detail_df

logger = logging.getLogger(__name__)

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
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_thermovisi = await _get_cached_thermovisi_detail_df()
            if df_thermovisi.empty:
                return "Data thermovisi report kosong"

            local_vars = {
                "df": df_thermovisi,
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
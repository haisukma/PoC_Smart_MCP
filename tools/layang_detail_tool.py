import asyncio
import pandas as pd
import numpy as np
import logging
import modal
import io
import contextlib
from services_mcp.layang_detail_service import get_layang_detail_df

logger = logging.getLogger(__name__)

LAYANG_DETAIL_DF = None
LAYANG_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_layang_detail_df() -> pd.DataFrame:
    global LAYANG_DETAIL_DF

    async with LAYANG_DETAIL_LOCK:
        if (LAYANG_DETAIL_DF is None 
            or LAYANG_DETAIL_DF.empty
        ):
            logger.info("Fetching dataset")
            LAYANG_DETAIL_DF = (await get_layang_detail_df())

    return LAYANG_DETAIL_DF.copy()

def register_layang_detail_tools(mcp):

    @mcp.tool()
    async def execute_layang_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL TE MITIGASI LAYANG
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_layang = await _get_cached_layang_detail_df()
            if df_layang.empty:
                return "Data layang report kosong"

            local_vars = {
                "df": df_layang,
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
import asyncio
import logging
import io
import contextlib
import pandas as pd
import modal
from services_mcp.lingkungan_detail_service import get_lingkungan_detail_df

logger = logging.getLogger(__name__)

LINGKUNGAN_DETAIL_DF = None
LINGKUNGAN_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_lingkungan_detail_df() -> pd.DataFrame:
    global LINGKUNGAN_DETAIL_DF

    async with LINGKUNGAN_DETAIL_LOCK:
        if (
            LINGKUNGAN_DETAIL_DF is None
            or LINGKUNGAN_DETAIL_DF.empty
        ):
            logger.info("Fetching dataset")
            LINGKUNGAN_DETAIL_DF = (await get_lingkungan_detail_df())

        return LINGKUNGAN_DETAIL_DF.copy()

def register_lingkungan_detail_tools(mcp):

    @mcp.tool()
    async def execute_lingkungan_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL ANCAMAN KONDISI LINGKUNGAN
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_lingkungan = await _get_cached_lingkungan_detail_df()
            if df_lingkungan.empty:
                return "Data lingkungan report kosong"

            local_vars = {
                "df": df_lingkungan,
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
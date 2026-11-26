import asyncio
import logging
import io
import contextlib
import pandas as pd
import modal
from services_mcp.jumper_gsw_detail_service import get_jumper_gsw_detail_df

logger = logging.getLogger(__name__)

JUMPER_GSW_DETAIL_DF = None
JUMPER_GSW_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_jumper_gsw_detail_df() -> pd.DataFrame:
    global JUMPER_GSW_DETAIL_DF

    async with JUMPER_GSW_DETAIL_LOCK:

        if (
            JUMPER_GSW_DETAIL_DF is None
            or JUMPER_GSW_DETAIL_DF.empty
        ):
            logger.info("JUMPER GSW | Fetching dataset")
            JUMPER_GSW_DETAIL_DF = (await get_jumper_gsw_detail_df())

        return JUMPER_GSW_DETAIL_DF.copy()

def register_jumper_gsw_detail_tools(mcp):

    @mcp.tool()
    async def execute_jumper_gsw_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL JUMPER GSW
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_jumper_gsw = await _get_cached_jumper_gsw_detail_df()
            if df_jumper_gsw.empty:
                return "Data jumper gsw report kosong"

            local_vars = {
                "df": df_jumper_gsw,
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
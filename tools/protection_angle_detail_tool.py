import asyncio
import logging
import io
import contextlib
import pandas as pd
import modal
from services_mcp.protection_angle_detail_service import get_protection_angle_detail_df

logger = logging.getLogger(__name__)

PROTECTION_ANGLE_DETAIL_DF = None
PROTECTION_ANGLE_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_protection_angle_detail_df() -> pd.DataFrame:
    global PROTECTION_ANGLE_DETAIL_DF

    async with PROTECTION_ANGLE_DETAIL_LOCK:
        if (
            PROTECTION_ANGLE_DETAIL_DF is None
            or PROTECTION_ANGLE_DETAIL_DF.empty
        ):
            logger.info("Fetching dataset")
            PROTECTION_ANGLE_DETAIL_DF = (await get_protection_angle_detail_df())

        return PROTECTION_ANGLE_DETAIL_DF.copy()

def register_protection_angle_detail_tools(mcp):

    @mcp.tool()
    async def execute_protection_angle_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL ASSESMEN SUDUT LINDUNG
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_protection_angle = await _get_cached_protection_angle_detail_df()
            if df_protection_angle.empty:
                return "Data protection angle report kosong"

            local_vars = {
                "df": df_protection_angle,
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
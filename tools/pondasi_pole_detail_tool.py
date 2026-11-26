import asyncio
import logging
import io
import contextlib
import pandas as pd
import modal
from services_mcp.pondasi_pole_detail_service import get_pondasi_pole_detail_df

logger = logging.getLogger(__name__)

POLE_DETAIL_DF = None
POLE_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_pondasi_pole_detail_df() -> pd.DataFrame:
    global POLE_DETAIL_DF

    async with POLE_DETAIL_LOCK:
        if (
            POLE_DETAIL_DF is None
            or POLE_DETAIL_DF.empty
        ):
            logger.info("Fetching dataset")
            POLE_DETAIL_DF = (await get_pondasi_pole_detail_df())

        return POLE_DETAIL_DF.copy()

def register_pondasi_pole_detail_tools(mcp):

    @mcp.tool()
    async def execute_pondasi_pole_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL KONDISI PONDASI TOWER TIPE POLE
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_pondasi_pole = await _get_cached_pondasi_pole_detail_df()
            if df_pondasi_pole.empty:
                return "Data pondasi pole report kosong"

            local_vars = {
                "df": df_pondasi_pole,
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
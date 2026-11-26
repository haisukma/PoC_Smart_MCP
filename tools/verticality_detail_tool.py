import asyncio
import logging
import io
import contextlib
import pandas as pd
import modal
from services_mcp.verticality_detail_service import get_verticality_detail_df

logger = logging.getLogger(__name__)

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
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_verticality = await _get_cached_verticality_detail_df()
            if df_verticality.empty:
                return "Data verticality report kosong"

            local_vars = {
                "df": df_verticality,
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
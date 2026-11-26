import asyncio
import logging
import io
import contextlib
import pandas as pd
import modal
from services_mcp.lightning_detail_service import get_lightning_detail_df

logger = logging.getLogger(__name__)

LIGHTNING_DETAIL_DF = None
LIGHTNING_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_lightning_detail_df() -> pd.DataFrame:
    global LIGHTNING_DETAIL_DF

    async with LIGHTNING_DETAIL_LOCK:
        if (
            LIGHTNING_DETAIL_DF is None
            or LIGHTNING_DETAIL_DF.empty
        ):
            logger.info("Fetching dataset")
            LIGHTNING_DETAIL_DF = (await get_lightning_detail_df())

        return LIGHTNING_DETAIL_DF.copy()

def register_lightning_detail_tools(mcp):

    @mcp.tool()
    async def execute_lightning_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL LIGHTNING atau PROTEKSI PETIR
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_lightning = await _get_cached_lightning_detail_df()
            if df_lightning.empty:
                return "Data lightning report kosong"

            local_vars = {
                "df": df_lightning,
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
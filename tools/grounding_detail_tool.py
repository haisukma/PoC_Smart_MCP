import asyncio
import logging
import io
import contextlib
import pandas as pd
import modal
from services_mcp.grounding_detail_service import get_grounding_detail_df

logger = logging.getLogger(__name__)

GROUNDING_DETAIL_DF = None
GROUNDING_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_grounding_detail_df() -> pd.DataFrame:
    global GROUNDING_DETAIL_DF

    async with GROUNDING_DETAIL_LOCK:
        if (
            GROUNDING_DETAIL_DF is None
            or GROUNDING_DETAIL_DF.empty
        ):
            logger.info("Fetching dataset")
            GROUNDING_DETAIL_DF = (await get_grounding_detail_df())

        return GROUNDING_DETAIL_DF.copy()

def register_grounding_detail_tools(mcp):

    @mcp.tool()
    async def execute_grounding_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL GROUNDING / PENTANAHAN
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_grounding = await _get_cached_grounding_detail_df()
            if df_grounding.empty:
                return "Data grounding report kosong"

            local_vars = {
                "df": df_grounding,
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
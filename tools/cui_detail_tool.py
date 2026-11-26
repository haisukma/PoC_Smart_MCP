import asyncio
import logging
import io
import contextlib
import pandas as pd
import modal
from services_mcp.cui_detail_service import get_cui_detail_df

logger = logging.getLogger(__name__)

CUI_DETAIL_DF = None
CUI_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_cui_detail_df() -> pd.DataFrame:
    global CUI_DETAIL_DF

    async with CUI_DETAIL_LOCK:

        if (
            CUI_DETAIL_DF is None
            or CUI_DETAIL_DF.empty
        ):
            logger.info("Fetching dataset")
            CUI_DETAIL_DF = (await get_cui_detail_df())

        return CUI_DETAIL_DF.copy()

def register_cui_detail_tools(mcp):

    @mcp.tool()
    async def execute_cui_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL CLIMB UP INSPECTION
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_cui = await _get_cached_cui_detail_df()
            if df_cui.empty:
                return "Data hammer test report kosong"

            local_vars = {
                "df": df_cui,
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
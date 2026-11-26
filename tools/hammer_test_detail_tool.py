import asyncio
import logging
import io
import contextlib
import pandas as pd
import modal
from services_mcp.hammer_test_service import get_hammer_test_detail_df

logger = logging.getLogger(__name__)

HAMMER_TEST_DETAIL_DF = None
HAMMER_TEST_DETAIL_LOCK = asyncio.Lock()

async def _get_cached_hammer_test_detail_df() -> pd.DataFrame:
    global HAMMER_TEST_DETAIL_DF

    async with HAMMER_TEST_DETAIL_LOCK:
        if (
            HAMMER_TEST_DETAIL_DF is None
            or HAMMER_TEST_DETAIL_DF.empty
        ):
            logger.info("Fetching dataset")
            HAMMER_TEST_DETAIL_DF = (await get_hammer_test_detail_df())

        return HAMMER_TEST_DETAIL_DF.copy()

def register_hammer_test_detail_tools(mcp):

    @mcp.tool()
    async def execute_hammer_test_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL HAMMER TEST / PENGUJIAN KEKUATAN BETON
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_hammer_test = await _get_cached_hammer_test_detail_df()
            if df_hammer_test.empty:
                return "Data hammer test report kosong"

            local_vars = {
                "df": df_hammer_test,
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
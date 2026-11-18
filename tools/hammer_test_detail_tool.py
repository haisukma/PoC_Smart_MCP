import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.hammer_test_service import get_hammer_test_detail_df

HAMMER_TEST_DETAIL_DF = None

async def _get_cached_hammer_test_detail_df() -> pd.DataFrame:
    global HAMMER_TEST_DETAIL_DF

    if HAMMER_TEST_DETAIL_DF is None or HAMMER_TEST_DETAIL_DF.empty:
       HAMMER_TEST_DETAIL_DF = await get_hammer_test_detail_df()

    return HAMMER_TEST_DETAIL_DF

def register_hammer_test_detail_tools(mcp):

    @mcp.tool()
    async def execute_hammer_test_detail_analysis(code: str) -> str:
        """
        Mengambil data mentah (DataFrame) DETAIL PENGUJIAN KEKUATAN BETON.
        WAJIB dipanggil PERTAMA kali untuk pertanyaan detail pengujian beton, 
        sebelum memanggil `execute_hammer_test_detail_analysis`
        """

        try:
            df_hammer_test = await _get_cached_hammer_test_detail_df()
            if df_hammer_test.empty:
                return "Data thermovisi report kosong"

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
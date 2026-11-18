import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.sktt_detail_service import get_sktt_detail_df

SKTT_DETAIL_DF = None

async def _get_cached_sktt_detail_df() -> pd.DataFrame:
    global SKTT_DETAIL_DF

    if SKTT_DETAIL_DF is None or SKTT_DETAIL_DF.empty:
        SKTT_DETAIL_DF = await get_sktt_detail_df()

    return SKTT_DETAIL_DF

def register_sktt_detail_tools(mcp):

    @mcp.tool()
    async def execute_sktt_detail_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL SALURAN KABEL TEGANGAN TINGGI
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_sktt = await _get_cached_sktt_detail_df()
            if df_sktt.empty:
                return "Data sktt report kosong"

            local_vars = {
                "df": df_sktt,
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
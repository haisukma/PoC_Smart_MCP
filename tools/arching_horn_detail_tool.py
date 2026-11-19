import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.arching_horn_detail_service import get_arching_horn_detail_df

ARCHING_HORN_DETAIL_DF = None

async def _get_cached_arching_horn_detail_df() -> pd.DataFrame:
    global ARCHING_HORN_DETAIL_DF

    if ARCHING_HORN_DETAIL_DF is None or ARCHING_HORN_DETAIL_DF.empty:
        ARCHING_HORN_DETAIL_DF = await get_arching_horn_detail_df()

    return ARCHING_HORN_DETAIL_DF

def register_arching_horn_detail_tools(mcp):

    @mcp.tool()
    async def execute_arching_horn_detail_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL ARCHING_HORN
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_arching_horn = await _get_cached_arching_horn_detail_df()
            if df_arching_horn.empty:
                return "Data arching horn report kosong"

            local_vars = {
                "df": df_arching_horn,
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
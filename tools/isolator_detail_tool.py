import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.isolator_detail_service import get_isolator_detail_df

ISOLATOR_REPORT_DF = None

async def _get_cached_isolator_detail_df() -> pd.DataFrame:
    global ISOLATOR_REPORT_DF

    if ISOLATOR_REPORT_DF is None or ISOLATOR_REPORT_DF.empty:
        ISOLATOR_REPORT_DF = await get_isolator_detail_df()

    return ISOLATOR_REPORT_DF

def register_isolator_detail_tools(mcp):

    @mcp.tool()
    async def execute_isolator_detail_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL ISOLATOR
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_isolator = await _get_cached_isolator_detail_df()
            if df_isolator.empty:
                return "Data grounding report kosong"

            local_vars_isolator = {
                "df": df_isolator,
                "pd": pd
            }

            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                exec(code, local_vars_isolator)

            result = output_buffer.getvalue()

            return (
                result.strip()
                if result.strip()
                else "Kode berhasil dieksekusi tanpa output print")

        except Exception as e:
            return f"Error executing Python Code: {str(e)}"            
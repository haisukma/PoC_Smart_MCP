import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.isolator_change_service import get_isolator_change_df

ISOLATOR_CHANGE_DF = None

async def _get_cached_isolator_change_df() -> pd.DataFrame:
    global ISOLATOR_CHANGE_DF

    if ISOLATOR_CHANGE_DF is None or ISOLATOR_CHANGE_DF.empty:
        ISOLATOR_CHANGE_DF = await get_isolator_change_df()

    return ISOLATOR_CHANGE_DF

def register_isolator_change_tools(mcp):

    @mcp.tool()
    async def execute_isolator_change_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL PENGGANTIAN ISOLATOR
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_isolator_change = await _get_cached_isolator_change_df()
            if df_isolator_change.empty:
                return "Data grounding report kosong"

            local_vars_isolator_change = {
                "df": df_isolator_change,
                "pd": pd
            }

            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                exec(code, local_vars_isolator_change)

            result = output_buffer.getvalue()

            return (
                result.strip()
                if result.strip()
                else "Kode berhasil dieksekusi tanpa output print")

        except Exception as e:
            return f"Error executing Python Code: {str(e)}"            
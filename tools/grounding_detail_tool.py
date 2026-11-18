import io
import contextlib
import pandas as pd
import numpy as np
from e2b_code_interpreter import AsyncSandbox
from services_mcp.grounding_detail_service import get_grounding_detail_df

GROUNDING_DETAIL_DF = None

async def _get_cached_grounding_detail_df() -> pd.DataFrame:
    global GROUNDING_DETAIL_DF

    if GROUNDING_DETAIL_DF is None or GROUNDING_DETAIL_DF.empty:
        GROUNDING_DETAIL_DF = await get_grounding_detail_df()

    return GROUNDING_DETAIL_DF

def register_grounding_detail_tools(mcp):

    @mcp.tool()
    async def execute_grounding_detail_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL GROUNDING

        DataFrame tersedia dalam variabel df
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_grounding = await _get_cached_grounding_detail_df()

            if df_grounding.empty:
                return "Data grounding report kosong"

            local_vars_grounding = {
                "df": df_grounding,
                "pd": pd
            }

            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                exec(code, local_vars_grounding)

            result = output_buffer.getvalue()

            return (
                result.strip()
                if result.strip()
                else "Kode berhasil dieksekusi tanpa output print")

        except Exception as e:
            return f"Error executing Python code: {str(e)}"
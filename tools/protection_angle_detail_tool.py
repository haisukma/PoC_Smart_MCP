import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.protection_angle_detail_service import get_protection_angle_detail_df

PROTECTION_ANGLE_DETAIL_DF = None

async def _get_cached_protection_angle_detail_df() -> pd.DataFrame:
    global PROTECTION_ANGLE_DETAIL_DF

    if PROTECTION_ANGLE_DETAIL_DF is None or PROTECTION_ANGLE_DETAIL_DF.empty:
        PROTECTION_ANGLE_DETAIL_DF = await get_protection_angle_detail_df()

    return PROTECTION_ANGLE_DETAIL_DF

def register_protection_angle_detail_tools(mcp):

    @mcp.tool()
    async def execute_protection_angle_detail_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL ASESMEN SUDUT LINDUNG
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_protection_angle = await _get_cached_protection_angle_detail_df()
            if df_protection_angle.empty:
                return "Data protection angle report kosong"

            local_vars = {
                "df": df_protection_angle,
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
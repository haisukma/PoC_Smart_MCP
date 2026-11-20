import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.pondasi_leveling_detail_service import get_pondasi_leveling_detail_df

PONDASI_LEVELING_DETAIL_DF = None

async def _get_cached_pondasi_leveling_detail_df() -> pd.DataFrame:
    global PONDASI_LEVELING_DETAIL_DF

    if PONDASI_LEVELING_DETAIL_DF is None or PONDASI_LEVELING_DETAIL_DF.empty:
        PONDASI_LEVELING_DETAIL_DF = await get_pondasi_leveling_detail_df()

    return PONDASI_LEVELING_DETAIL_DF

def register_pondasi_leveling_detail_tools(mcp):

    @mcp.tool()
    async def execute_pondasi_leveling_detail_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL PENGUKURAN LEVELING PONDASI TOWER
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_pondasi_leveling = await _get_cached_pondasi_leveling_detail_df()
            if df_pondasi_leveling.empty:
                return "Data pondasi leveling report kosong"

            local_vars = {
                "df": df_pondasi_leveling,
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
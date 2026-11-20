import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.pondasi_pole_detail_service import get_pondasi_pole_detail_df

PONDASI_POLE_DETAIL_DF = None

async def _get_cached_pondasi_pole_detail_df() -> pd.DataFrame:
    global PONDASI_POLE_DETAIL_DF

    if PONDASI_POLE_DETAIL_DF is None or PONDASI_POLE_DETAIL_DF.empty:
        PONDASI_POLE_DETAIL_DF = await get_pondasi_pole_detail_df()

    return PONDASI_POLE_DETAIL_DF

def register_pondasi_pole_detail_tools(mcp):

    @mcp.tool()
    async def execute_pondasi_pole_detail_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL ASESMEN KONDISI PONDASI TOWER TIPE POLE
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_pondasi_pole = await _get_cached_pondasi_pole_detail_df()
            if df_pondasi_pole.empty:
                return "Data pondasi pole report kosong"

            local_vars = {
                "df": df_pondasi_pole,
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
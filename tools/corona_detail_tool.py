import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.corona_detail_service import get_corona_detail_df

CORONA_DETAIL_DF = None

async def _get_cached_corona_detail_df() -> pd.DataFrame:
    global CORONA_DETAIL_DF

    if CORONA_DETAIL_DF is None or CORONA_DETAIL_DF.empty:
        CORONA_DETAIL_DF = await get_corona_detail_df()

    return CORONA_DETAIL_DF

def register_corona_detail_tools(mcp):

    @mcp.tool()
    async def execute_corona_detail_analysis(code: str) -> str:
        """
        Mengambil data mentah (DataFrame) DETAIL KORONA PADA TRANSMISI.
        WAJIB dipanggil PERTAMA kali untuk pertanyaan detail korona, 
        sebelum memanggil `execute_corona_detail_analysis`
        """

        try:
            df_corona = await _get_cached_corona_detail_df()
            if df_corona.empty:
                return "Data corona report kosong"

            local_vars = {
                "df": df_corona,
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
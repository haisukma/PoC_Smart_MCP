import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.lingkungan_detail_service import get_lingkungan_detail_df

LINGKUNGAN_DETAIL_DF = None

async def _get_cached_lingkungan_detail_df() -> pd.DataFrame:
    global LINGKUNGAN_DETAIL_DF

    if LINGKUNGAN_DETAIL_DF is None or LINGKUNGAN_DETAIL_DF.empty:
        LINGKUNGAN_DETAIL_DF = await get_lingkungan_detail_df()

    return LINGKUNGAN_DETAIL_DF

def register_lingkungan_detail_tools(mcp):

    @mcp.tool()
    async def execute_lingkungan_detail_analysis(code: str) -> str:
        """
        Mengambil data mentah (DataFrame) DETAIL ANCAMAN KONDISI LINGKUNGAN.
        WAJIB dipanggil PERTAMA kali untuk pertanyaan detail ancaman kondisi lingkungan, 
        sebelum memanggil `execute_lingkungan_detail_analysis`
        """

        try:
            df_lingkungan = await _get_cached_lingkungan_detail_df()
            if df_lingkungan.empty:
                return "Data lingkungan report kosong"

            local_vars = {
                "df": df_lingkungan,
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
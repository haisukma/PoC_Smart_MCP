import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.thermovisi_detail_service import get_thermovisi_detail_df

THERMOVISI_DETAIL_DF = None

async def _get_cached_thermovisi_detail_df() -> pd.DataFrame:
    global THERMOVISI_DETAIL_DF

    if THERMOVISI_DETAIL_DF is None or THERMOVISI_DETAIL_DF.empty:
        THERMOVISI_DETAIL_DF = await get_thermovisi_detail_df()

    return THERMOVISI_DETAIL_DF

def register_thermovisi_detail_tools(mcp):

    @mcp.tool()
    async def execute_thermovisi_detail_analysis(code: str) -> str:
        """
        Mengambil data mentah (DataFrame) DETAIL THERMOVISI.
        WAJIB dipanggil PERTAMA kali untuk pertanyaan detail thermovisi, 
        sebelum memanggil `execute_thermovisi_detail_analysis`
        """

        try:
            df_thermovisi = await _get_cached_thermovisi_detail_df()
            if df_thermovisi.empty:
                return "Data thermovisi report kosong"

            local_vars = {
                "df": df_thermovisi,
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
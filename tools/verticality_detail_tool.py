import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.verticality_detail_service import get_verticality_detail_df

VERTICALITY_DETAIL_DF = None

async def _get_cached_verticality_detail_df() -> pd.DataFrame:
    global VERTICALITY_DETAIL_DF

    if VERTICALITY_DETAIL_DF is None or VERTICALITY_DETAIL_DF.empty:
       VERTICALITY_DETAIL_DF = await get_verticality_detail_df()

    return VERTICALITY_DETAIL_DF

def register_verticality_detail_tools(mcp):

    @mcp.tool()
    async def execute_verticality_detail_analysis(code: str) -> str:
        """
        Mengambil data mentah (DataFrame) DETAIL VERTICALITY TOWER.
        WAJIB dipanggil PERTAMA kali untuk pertanyaan detail verticality tower, 
        sebelum memanggil `execute_verticality_detail_analysis`
        """

        try:
            df_verticality = await _get_cached_verticality_detail_df()
            if df_verticality.empty:
                return "Data verticality report kosong"

            local_vars = {
                "df": df_verticality,
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
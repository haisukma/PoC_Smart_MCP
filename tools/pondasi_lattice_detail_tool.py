import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.pondasi_lattice_detail_service import get_pondasi_lattice_detail_df

PONDASI_LATTICE_DETAIL_DF = None

async def _get_cached_pondasi_lattice_detail_df() -> pd.DataFrame:
    global PONDASI_LATTICE_DETAIL_DF

    if PONDASI_LATTICE_DETAIL_DF is None or PONDASI_LATTICE_DETAIL_DF.empty:
        PONDASI_LATTICE_DETAIL_DF = await get_pondasi_lattice_detail_df()

    return PONDASI_LATTICE_DETAIL_DF

def register_pondasi_lattice_detail_tools(mcp):

    @mcp.tool()
    async def execute_pondasi_lattice_detail_analysis(code: str) -> str:
        """
        Mengambil data mentah (DataFrame) DETAIL pondasi lattice.
        WAJIB dipanggil PERTAMA kali untuk pertanyaan detail pondasi lattice, 
        sebelum memanggil `execute_pondasi_lattice_detail_analysis`
        """

        try:
            df_pondasi_lattice = await _get_cached_pondasi_lattice_detail_df()
            if df_pondasi_lattice.empty:
                return "Data pondasi lattice report kosong"

            local_vars = {
                "df": df_pondasi_lattice,
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
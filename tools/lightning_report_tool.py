import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.lightning_report_service import get_lightning_report_df

LIGHTNING_REPORT_DF = None

async def _get_cached_lightning_report_df() -> pd.DataFrame:
    global LIGHTNING_REPORT_DF

    if LIGHTNING_REPORT_DF is None or LIGHTNING_REPORT_DF.empty:
        LIGHTNING_REPORT_DF = await get_lightning_report_df()

    return LIGHTNING_REPORT_DF

def register_lightning_report_tools(mcp):

    @mcp.tool()
    async def execute_lightning_analysis(code: str) -> str:
        """
        Mengambil data mentah (DataFrame) REKAP DAN REALISASI PROTEKSI PETIR atau LIGHTNING.
        WAJIB dipanggil PERTAMA kali untuk pertanyaan rekap dan realisasi lightning, 
        sebelum memanggil `execute_lightning_report_analysis`
        """

        try:
            df_lightning_report = await _get_cached_lightning_report_df()
            if df_lightning_report.empty:
                return "Data lightning report kosong"

            local_vars = {
                "df": df_lightning_report,
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
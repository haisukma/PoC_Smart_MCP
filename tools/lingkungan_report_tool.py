import io
import contextlib
import pandas as pd
import numpy as np
import json
import datetime
from services_mcp.lingkungan_report_service import get_lingkungan_report_df

__LINGKUNGAN_REPORT_DF: pd.DataFrame = None

async def _get_cached_lingkungan_report_df() -> dict[str, pd.DataFrame]:
    global __LINGKUNGAN_REPORT_DF

    if __LINGKUNGAN_REPORT_DF is None or not __LINGKUNGAN_REPORT_DF:
        __LINGKUNGAN_REPORT_DF = await get_lingkungan_report_df()

    return __LINGKUNGAN_REPORT_DF

def register_lingkungan_report_tools(mcp):

    @mcp.tool()
    async def execute_lingkungan_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data AGREGASI atau KESIMPULAN ANCAMAN KONDISI LINGKUNGAN TRANSMISI dari API

        DataFrame yang tersedia:
        - df_classification: Data klasifikasi kondisi lingkungan per UPT
        - df_priority: Data prioritas penanganan per UPT
        - df_tindak_lanjut: Data progres tindak lanjut

        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            lingkungan_report_data = await _get_cached_lingkungan_report_df()
            if not lingkungan_report_data:
                return "Data lingkungan report dari API kosong"

            local_vars = {
                "df_classification": lingkungan_report_data["classification"],
                "df_priority": lingkungan_report_data["priority"],
                "df_tindak_lanjut": lingkungan_report_data["tindak_lanjut"],
                "pd": pd}

            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                exec(code, local_vars)

            result = output_buffer.getvalue()

            return (
                result.strip()
                if result.strip()
                else "Kode berhasil dieksekusi tanpa output print")

        except Exception as e:
            return f"Error executing Python code: {str(e)}"

import io
import contextlib
import pandas as pd
import numpy as np
import json
import datetime
from services_mcp.corona_report_service import get_corona_report_df

__CORONA_REPORT_DF: pd.DataFrame = None

async def _get_cached_corona_report_df() -> dict[str, pd.DataFrame]:
    global __CORONA_REPORT_DF

    if __CORONA_REPORT_DF is None or not __CORONA_REPORT_DF:
        __CORONA_REPORT_DF = await get_corona_report_df()

    return __CORONA_REPORT_DF

def register_corona_report_tools(mcp):

    @mcp.tool()
    async def execute_corona_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data KESIMPULAN ASSESMEN KORONA dari API

        DataFrame yang tersedia:
        - df_target_realisasi: Data target dan realisasi inspeksi korona per UPT
        - df_assesment: Data rekapitulasi kondisi hasil asesmen korona

        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            corona_report_data = await _get_cached_corona_report_df()
            if not corona_report_data:
                return "Data corona report dari API kosong"

            local_vars = {
                "df_target_realisasi": corona_report_data["target_realisasi"],
                "df_assesment": corona_report_data["assesment"],
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

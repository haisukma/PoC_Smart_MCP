import io
import contextlib
import pandas as pd
import numpy as np
import json
import datetime
from services_mcp.thermovisi_report_service import get_thermovisi_report_df

__THERMOVISI_REPORT_DF: pd.DataFrame = None

async def _get_cached_thermovisi_report_df() -> dict[str, pd.DataFrame]:
    global __THERMOVISI_REPORT_DF

    if __THERMOVISI_REPORT_DF is None or not __THERMOVISI_REPORT_DF:
        __THERMOVISI_REPORT_DF = await get_thermovisi_report_df()

    return __THERMOVISI_REPORT_DF

def register_thermovisi_report_tools(mcp):

    @mcp.tool()
    async def execute_thermovisi_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data THERMOVISI REPORT/KESIMPULAN THERMOVISI dari API

        DataFrame yang tersedia:
        - df_realisasi: Data thermovisi berdasarkan realisasi
        - df_target_upt: Data thermovisi berdasarkan target UPT
        - df_kondisi: Data thermovisi berdasarkan kondisi
        - df_rekomendasi: Data thermovisi berdasarkan rekomendasi

        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            thermovisi_data = await _get_cached_thermovisi_report_df()
            if not thermovisi_data:
                return "Data thermovisi report dari API kosong"

            local_vars = {
                "df_realisasi": thermovisi_data["realisasi"],
                "df_target_upt": thermovisi_data["target_upt"],
                "df_kondisi": thermovisi_data["kondisi"],
                "df_rekomendasi": thermovisi_data["rekomendasi"],
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

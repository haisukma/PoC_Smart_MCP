import io
import contextlib
import pandas as pd
import numpy as np
import json
import datetime
from services_mcp.arching_horn_report_service import get_arching_horn_report_df

__ARCHING_HORN_REPORT_DF: pd.DataFrame = None

async def _get_cached_arching_horn_report_df() -> dict[str, pd.DataFrame]:
    global __ARCHING_HORN_REPORT_DF

    if __ARCHING_HORN_REPORT_DF is None or not __ARCHING_HORN_REPORT_DF:
        __ARCHING_HORN_REPORT_DF = await get_arching_horn_report_df()

    return __ARCHING_HORN_REPORT_DF

def register_arching_horn_report_tools(mcp):

    @mcp.tool()
    async def execute_arching_horn_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data ARCHING HORN REPORT/EVALUASI ARCHING HORN dari API

        DataFrame yang tersedia:
        - df_realization_tower: Data arching horn total realisasi tower per UPT
        - df_length_evaluaation_s: Data evaluasi panjang S pada arching horn
        - df_length_evaluation_d: Data evaluasi panjang D pada arching horn
        - df_length_evaluation_sd: Data evaluasi panjang S dan D

        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            arching_horn_report_data = await _get_cached_arching_horn_report_df()
            if not arching_horn_report_data:
                return "Data arching horn report dari API kosong"

            local_vars = {
                "df_realization_tower": arching_horn_report_data["realization_tower"],
                " df_length_evaluaation_s": arching_horn_report_data["length_evaluation_s"],
                "df_length_evaluation_d": arching_horn_report_data["length_evaluation_d"],
                "df_length_evaluation_sd": arching_horn_report_data["length_evaluation_sd"],
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

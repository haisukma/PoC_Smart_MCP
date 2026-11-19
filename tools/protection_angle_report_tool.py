import io
import contextlib
import pandas as pd
import numpy as np
import json
import datetime
from services_mcp.protection_angle_report_service import get_protection_angle_report_df

__PROTECTION_ANGLE_REPORT_DF: pd.DataFrame = None

async def _get_cached_protection_angle_report_df() -> dict[str, pd.DataFrame]:
    global __PROTECTION_ANGLE_REPORT_DF

    if __PROTECTION_ANGLE_REPORT_DF is None or not __PROTECTION_ANGLE_REPORT_DF:
        __PROTECTION_ANGLE_REPORT_DF = await get_protection_angle_report_df()

    return __PROTECTION_ANGLE_REPORT_DF

def register_protection_angle_report_tools(mcp):

    @mcp.tool()
    async def execute_protection_angle_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data LAPORAN AGREGASI ASESMEN SUDUT LINDUNG dari API

        DataFrame yang tersedia:
        - df_realization_angle: Data target dan realisasi asesmen sudut lindung per UPT
        - df_evaluations_angle: Data agregasi hasil evaluasi sudut lindung

        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            protection_report_data = await _get_cached_protection_angle_report_df()
            if not protection_report_data:
                return "Data protection angle report dari API kosong"

            local_vars = {
                "df_realization_angle": protection_report_data["realization_angle"],
                "df_evaluations_angle": protection_report_data["evaluations_angle"],
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

import io
import contextlib
import pandas as pd
import numpy as np
import json
import datetime
from services_mcp.pondas_lattice_report_service import get_pondasi_lattice_report_df

__PONDASI_LATTICE_REPORT_DF: pd.DataFrame = None

async def _get_cached_pondasi_lattice_report_df() -> dict[str, pd.DataFrame]:
    global __PONDASI_LATTICE_REPORT_DF

    if __PONDASI_LATTICE_REPORT_DF is None or not __PONDASI_LATTICE_REPORT_DF:
        __PONDASI_LATTICE_REPORT_DF = await get_pondasi_lattice_report_df()

    return __PONDASI_LATTICE_REPORT_DF

def register_pondasi_lattice_report_tools(mcp):

    @mcp.tool()
    async def execute_pondasi_lattice_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data LAPORAN AGREGASI atau RANGKUMAN KONDISI PONDASI TOWER TIPE LATTICE dari API

        DataFrame yang tersedia:
        - df_priority: Data pondasi lattice prioritas per UPT
        - df_classification: Data pondasi lattice klasifikasi per UPT
        - df_tindak_lanjut: Data pondasi lattice tindak lanjut per UPT

        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            pondasi_report_data = await _get_cached_pondasi_lattice_report_df()
            if not pondasi_report_data:
                return "Data pondasi lattice report dari API kosong"

            local_vars = {
                "df_priority": pondasi_report_data["priority"],
                "df_classification": pondasi_report_data["classification"],
                "df_tindak_lanjut": pondasi_report_data["tindak_lanjut"],
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

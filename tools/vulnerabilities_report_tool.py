import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.vulnerabilities_report_service import get_vulnerabilities_report_df

VULNERABILITIES_REPORT_DF = None

async def _get_cached_vulnerabilities_report_df() -> pd.DataFrame:
    global VULNERABILITIES_report_DF

    if VULNERABILITIES_REPORT_DF is None or VULNERABILITIES_REPORT_DF.empty:
        VULNERABILITIES_REPORT_DF = await get_vulnerabilities_report_df()

    return VULNERABILITIES_REPORT_DF

def register_vulnerabilities_report_tools(mcp):

    @mcp.tool()
    async def execute_vulnerabilities_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis rekapitulasi / pivot data potensi kerawanan transmisi per UPT.

        Kategori kerawanan yang dirangkum meliputi:

        Plastik Mulsa, Kabel SUTM/TR Melintang, Lahan Gambut, Pabrik/Gudang Tekstil/Kayu/Kertas, Gudang Bahan Bakar
        Bangunan, Timbunan Sampah/Material, Atap/Seng Konduktif, Potensi Kebakaran/Pembakaran Sampah
        Potensi Longsor, Galian Tanah/Pengeboran, Potensi Menyentuh Konduktor, Aktivitas Masyarakat, Pekerjaan Pihak Lain
                
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_vulnerabilities_report = await _get_cached_vulnerabilities_report_df()
            if df_vulnerabilities_report.empty:
                return "Data vulnerabilities report kosong"

            local_vars = {
                "df": df_vulnerabilities_report,
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
import io
import contextlib
import pandas as pd
import numpy as np
from guardrails.execution_policy import get_restricted_builtins, validate_code
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
        Gunakan tool ini untuk menganalisis REKAPITULASI / RINGKASAN data potensi kerawanan transmisi per UPT.

        Kategori kerawanan yang dirangkum meliputi:

        Plastik Mulsa, Kabel SUTM/TR Melintang, Lahan Gambut, Pabrik/Gudang Tekstil/Kayu/Kertas, Gudang Bahan Bakar
        Bangunan, Timbunan Sampah/Material, Atap/Seng Konduktif, Potensi Kebakaran/Pembakaran Sampah
        Potensi Longsor, Galian Tanah/Pengeboran, Potensi Menyentuh Konduktor, Aktivitas Masyarakat, Pekerjaan Pihak Lain
                
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            validate_code(code)

            df_vulnerabilities_report = await _get_cached_vulnerabilities_report_df()
            if df_vulnerabilities_report.empty:
                return "Data vulnerabilities report kosong"

            if not code or not code.strip():
                return "Kode python tidak boleh kosong"

            df_execution = df_vulnerabilities_report.copy(deep=True)
            executing_globals = {
                "__builtins__": get_restricted_builtins,
                "__name__": "__llm_analysis__",
                "df": df_vulnerabilities_report,
                "pd": pd,
                "np": np
            }

            # local_vars = {
            #     "df": df_vulnerabilities_report,
            #     "pd": pd
            # }

            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                exec(
                    compile(code, "<llm_generated_code>", "exec"),
                    executing_globals,
                    executing_globals
                )

            result = output_buffer.getvalue()

            return (
                result.strip()
                if result.strip()
                else "Kode berhasil dieksekusi tanpa output print"
            )

        except ImportError as e:
            return f"Library tidak diizinkan: {str(e)}"

        except Exception as e:
            return f"Error executing Python code: {str(e)}"
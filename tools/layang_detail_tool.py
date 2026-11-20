import io
import contextlib
import pandas as pd
import numpy as np
import textwrap
from e2b_code_interpreter import AsyncSandbox
from services_mcp.layang_detail_service import get_layang_detail_df

LAYANG_DETAIL_DF = None

async def _get_cached_layang_detail_df() -> pd.DataFrame:
    global LAYANG_DETAIL_DF

    if LAYANG_DETAIL_DF is None or LAYANG_DETAIL_DF.empty:
        LAYANG_DETAIL_DF = await get_layang_detail_df()

    return LAYANG_DETAIL_DF

def register_layang_detail_tools(mcp):

    @mcp.tool()
    async def execute_layang_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL TEMUAN serta MITIGASI LAYANG-LAYANG menggunakan E2B Sandbox
        
        DataFrame tersedia dalam variabel df
        WAJIB menggunakan print(...) untuk melihat output
        
        Ekseskusi Python dilakukan di lingkungan sandbox terisolasi
        """

        sandbox = None
        try:
            df_layang = await _get_cached_layang_detail_df()

            if df_layang.empty:
                return "Data detail layang kosong"

            json_data = df_layang.to_json(orient="records")
            json_path = "/tmp/layang_detail.json"

            sandbox = await AsyncSandbox.create()
            await sandbox.files.write(json_path, json_data)

            execution_code = textwrap.dedent(f"""
                import pandas as pd
                df = pd.read_json("{json_path}", orient="records")
                print("Shape: ", df.shape)
                print("Columns: ", df.columns.tolist)
            """) + "\n" + textwrap.dedent(code)

            execution = await sandbox.run_code(
                execution_code, timeout=120
            )

            if execution.error:
                return(
                    "Error executing Python code: "
                    f"{execution.error.value}"
                )

            stdout = execution.logs.stdout or []
            result = "".join(str(item) for item in stdout)

            return(
                result.strip()
                if result.strip()
                else "Kode berhasil dieksekusi tanpa output print"
            )

        except Exception as e:
            return f"Error executing Python code: {str(e)}"

        finally:
            if sandbox is not None:
                try:
                    await sandbox.kill()
                except Exception:
                    pass

# def register_layang_detail_tools(mcp):

#     @mcp.tool()
#     async def execute_layang_detail_analysis(code: str) -> str:
#         """
#         Gunakan tool ini untuk menganalisis data TEMUAN dan KEGIATAN MITIGASI LAYANG-LAYANG
        
#         DataFrame tersedia dalam variabel df.
#         WAJIB menggunakan print(...) untuk melihat output
#         """

#         try:
#             df_layang = await _get_cached_layang_detail_df()
#             if df_layang.empty:
#                 return "Data layang report kosong"

#             local_vars = {
#                 "df": df_layang,
#                 "pd": pd
#             }

#             output_buffer = io.StringIO()
#             with contextlib.redirect_stdout(output_buffer):
#                 exec(code, local_vars)

#             result = output_buffer.getvalue()

#             return (
#                 result.strip()
#                 if result.strip()
#                 else "Kode berhasil dieksekusi tanpa output print"
#             )

#         except Exception as e:
#             return f"Error executing Python code: {str(e)}"
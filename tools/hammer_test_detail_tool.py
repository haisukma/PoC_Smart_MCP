import io
import contextlib
import pandas as pd
import numpy as np
import textwrap
from e2b_code_interpreter import AsyncSandbox
from services_mcp.hammer_test_service import get_hammer_test_detail_df

HAMMER_TEST_DETAIL_DF = None

async def _get_cached_hammer_test_detail_df() -> pd.DataFrame:
    global HAMMER_TEST_DETAIL_DF

    if HAMMER_TEST_DETAIL_DF is None or HAMMER_TEST_DETAIL_DF.empty:
       HAMMER_TEST_DETAIL_DF = await get_hammer_test_detail_df()

    return HAMMER_TEST_DETAIL_DF

def register_hammer_test_detail_tools(mcp):

    @mcp.tool()
    async def execute_hammer_test_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL PENGUJIAN KEKUATAN BETON/HAMMER TEST TOWER dan PONDASI menggunakan E2B Sandbox
        
        DataFrame tersedia dalam variabel df
        WAJIB menggunakan print(...) untuk melihat output
        
        Eksekusi Python dilakukan di lingkungan sandbox terisolasi
        """

        sandbox = None
        try:
            df_hammer_test = await _get_cached_hammer_test_detail_df()

            if df_hammer_test.empty:
                return "Data detail hammer test kosong"

            json_data = df_hammer_test.to_json(orient="records")
            json_path = "/tmp/hammer_test_detail.json"

            sandbox = await AsyncSandbox.create()
            await sandbox.files.write(json_path, json_data)

            execution_code = textwrap.dedent(f"""
                import pandas as pd
                df = pd.read_json("{json_path}", orient="records")
                print("SHAPE: ", df.shape)
                print("COLUMNS: ", df.columns.tolist)
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

# def register_hammer_test_detail_tools(mcp):

#     @mcp.tool()
#     async def execute_hammer_test_detail_analysis(code: str) -> str:
#         """
#         Mengambil data mentah (DataFrame) DETAIL PENGUJIAN KEKUATAN BETON/HAMMER TEST TOWER DAN PONDASI.
#         WAJIB dipanggil PERTAMA kali untuk pertanyaan detail pengujian kekuatan beton/hammer test dan pondasi, 
#         sebelum memanggil `execute_hammer_test_detail_analysis`
#         """

#         try:
#             df_hammer_test = await _get_cached_hammer_test_detail_df()
#             if df_hammer_test.empty:
#                 return "Data thermovisi report kosong"

#             local_vars = {
#                 "df": df_hammer_test,
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
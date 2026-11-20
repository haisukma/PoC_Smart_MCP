import pandas as pd
import numpy as np
import textwrap
from e2b_code_interpreter import AsyncSandbox
from services_mcp.cui_detail_service import get_cui_detail_df

CUI_DETAIL_DF = None

async def _get_cached_cui_detail_df() -> pd.DataFrame:
    global CUI_DETAIL_DF

    if CUI_DETAIL_DF is None or CUI_DETAIL_DF.empty:
        CUI_DETAIL_DF = await get_cui_detail_df()

    return CUI_DETAIL_DF

def register_cui_detail_tools(mcp):

    @mcp.tool()
    async def execute_cui_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL CLIMB UP INSPECTION menggunakan E2B Sandbox
        
        DataFrame tersedia dalam variabel df
        WAJIB menggunakan print(...) untuk melihat output
        
        Eksekusi Python dilakukan di lingkungan sandbox terisolasi
        """

        sandbox = None
        try:
            df_cui = await _get_cached_cui_detail_df()

            if df_cui.empty:
                return "Data detail cui kosong"

            json_data = df_cui.to_json(orient="records")
            json_path = "/tmp/cui_detail.json"

            sandbox = await AsyncSandbox.create()
            await sandbox.files.write(json_path, json_data)

            execution_code = textwrap.dedent(f"""
                import pandas as pd
                df = pd.read_json("{json_path}", orient="records")
                print("Shape:", df.shape)
                print("Columns:", df.columns.tolist)
            """) + "\n" + textwrap.dedent(code)

            execution = await sandbox.run_code(
                execution_code, timeout=120)

            if execution.error:
                return (
                    "Error executing Python code: "
                    f"{execution.error.value}")

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

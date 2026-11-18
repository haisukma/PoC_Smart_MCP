import pandas as pd
import os
from e2b_code_interpreter import AsyncSandbox
from services_mcp.grounding_detail_service import get_grounding_detail_df
# from dotenv import load_dotenv

# load_dotenv()

# API_KEY = os.getenv("E2B_API_KEY")
GROUNDING_DETAIL_DF = None

async def _get_cached_grounding_detail_df() -> pd.DataFrame:
    global GROUNDING_DETAIL_DF

    if GROUNDING_DETAIL_DF is None or GROUNDING_DETAIL_DF.empty:
        GROUNDING_DETAIL_DF = await get_grounding_detail_df()

    return GROUNDING_DETAIL_DF

def register_grounding_detail_tools(mcp):

    @mcp.tool()
    async def execute_grounding_detail_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL GROUNDING.

        Eksekusi kode Python dilakukan di E2B Sandbox.

        DataFrame tersedia dalam variabel df.
        Library yang tersedia: pandas (pd), numpy (np).
        WAJIB menggunakan print(...) untuk melihat output.
        """

        sandbox = None

        try:
            df_grounding = await _get_cached_grounding_detail_df()
            if df_grounding.empty:
                return "Data grounding report kosong"

            sandbox = await AsyncSandbox.create()
            csv_data = df_grounding.to_csv(index=False)
            await sandbox.files.write(
                "/tmp/grounding_detail.csv", csv_data)

            sandbox_code = f"""
            import pandas as pd
            import numpy as np

            df = pd.read_csv("/tmp/grounding_detail.csv")

            print("Dataset berhasil dimuat")
            print(f"Jumlah baris: {{len(df)}}")
            print(f"Jumlah kolom: {{len(df.columns)}}")

            {code}
            """

            execution = await sandbox.run_code(sandbox_code, timeout=60)
            if execution.error:
                return (
                    "Error saat eksekusi kode di E2B Sandbox:\n"
                    f"{execution.error.name}: "
                    f"{execution.error.value}\n\n"
                    f"{execution.error.traceback}"
                )

            stdout = "".join(
                execution.logs.stdout or []
            ).strip()

            stderr = "".join(
                execution.logs.stderr or []
            ).strip()

            if stdout:
                return stdout

            if stderr:
                return f"Sandbox stderr:\n{stderr}"

            return "Kode berhasil dieksekusi tanpa output print"

        except Exception as e:
            return (f"Error executing Python code in E2B Sandbox: {str(e)}")

        finally:
            if sandbox is not None:
                try:
                    await sandbox.kill()
                except Exception as cleanup_error:
                    print(f"Sandbox cleanup error: {cleanup_error}")

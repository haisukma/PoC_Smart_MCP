import pandas as pd
import numpy as np
import textwrap
import modal
from e2b_code_interpreter import AsyncSandbox
from services_mcp.cui_detail_service import get_cui_detail_df

CUI_DETAIL_DF = None

async def _get_cached_cui_detail_df() -> pd.DataFrame:
    global CUI_DETAIL_DF

    if CUI_DETAIL_DF is None or CUI_DETAIL_DF.empty:
        CUI_DETAIL_DF = await get_cui_detail_df()

    return CUI_DETAIL_DF

def register_cui_detail_tools(mcp):

    MODAL_IMAGE = modal.Image.debian_slim(python_version="3.12").pip_install(
        "pandas",
        "numpy",
        "matplotlib",
        "seaborn"
    )
    MODAL_APP = modal.App.lookup("si-smart-sandbox", create_if_missing=True)

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
            sandbox = await modal.Sandbox.create.aio(
                image=MODAL_IMAGE,
                app=MODAL_APP,
                region=["app-southeast"],
                cpu=0.25,
                memory=512,
                timeout=120,
                block_network=True
            )
            json_path = "/tmp/cui_detail.json"

            # sandbox = await AsyncSandbox.create()
            # await sandbox.files.write(json_path, json_data)
            async with sandbox.open.aio(json_path, "w") as f:
                await f.write.aio(json_data)

            execution_code = textwrap.dedent(f"""
                import pandas as pd
                df = pd.read_json("{json_path}", orient="records")
                print("Shape:", df.shape)
                print("Columns:", df.columns.tolist)
            """) + "\n" + textwrap.dedent(code)

            # execution = await sandbox.run_code(
            #     execution_code, timeout=120)
            process = await sandbox.exec.aio("python", "-c", execution_code)
            stdout = await process.stdout.read.aio()
            stderr = await process.stderr.read.aio()
            await process.wait.aio()

            if process.returncode != 0:
                return("Error executing Python code: "
                       f"{stderr.strip()}")

            # if execution.error:
            #     return (
            #         "Error executing Python code: "
            #         f"{execution.error.value}")

            # stdout = execution.logs.stdout or []
            # result = "".join(str(item) for item in stdout)

            return(
                stdout.strip()
                if stdout.strip()
                else "Kode berhasil dieksekusi tanpa output print"
            )

        except Exception as e:
            return f"Error executing Python code: {str(e)}"

        finally:
            if sandbox is not None:
                try:
                    await sandbox.terminate.aio()
                except Exception:
                    pass

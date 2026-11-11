
from pathlib import Path
import traceback
import pandas as pd
import seaborn as sns
from e2b_code_interpreter import AsyncSandbox
from mcp.server.fastmcp import Image as MCPImage

DATA_DIR = Path("data_storage")
OUTPUT_DIR = Path("output_grafik")

def register_grafik_tools(mcp):

    @mcp.tool()
    async def get_file_grafik(filename: str) -> str:
        """
        Membaca schema dan sampel data CSV/Excel sebelum membuat grafik

        Gunakan tool ini PERTAMA KALI ketika pengguna meminta grafik
        atau visualisasi dari file CSV/Excel

        Tool ini hanya membaca data, tidak membuat grafik
        """

        try:
            base_dir = DATA_DIR.resolve()
            filepath = (base_dir / filename).resolve()
            if not filepath.is_relative_to(base_dir):
                return "Error: Akses file di luar data_storage tidak diizinkan"

            if not filepath.exists():
                return f"Error: File '{filename}' tidak ditemukan"

            suffix = filepath.suffix.lower()
            if suffix == ".csv":
                df_grafik = pd.read_csv(filepath, nrows=5, low_memory=False)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    total_rows = sum(1 for _ in f) - 1

            elif suffix in [".xlsx", ".xls"]:
                df_grafik = pd.read_excel(filepath, nrows=5)
                total_rows = "Banyak (Excel File)"

            else:
                return "Error: Format hanya mendukung CSV dan Excel"

            if df_grafik.empty:
                return "Error: Dataset kosong"

            output = []
            output.append(f"File Name: {filename}")
            output.append(
                f"Total Baris: {total_rows}, "
                f"Total Kolom: {len(df_grafik.columns)}")

            output.append("\nDaftar Nama Kolom dan Tipe Data:")
            for col, dtype in df_grafik.dtypes.items():
                output.append(f"- '{col}' ({dtype})")

            output.append("\nSample Data:")
            output.append(df_grafik.to_string(index=False))

            return "\n".join(output)

        except Exception as e:
            return f"Error membaca schema: {str(e)}"


    @mcp.tool()
    async def create_grafik(filename: str, python_code: str) -> MCPImage:
        """
        Menjalankan kode Python buatan AI untuk membuat grafik PNG

        CATATAN PENTING UNTUK LLM:
        - HANYA untuk permintaan grafik atau visualisasi
        - Panggil get_file_grafik terlebih dahulu
        - Gunakan Pandas untuk membaca dan mengolah data
        - Gunakan Matplotlib dan Seaborn untuk membuat grafik
        - Simpan hasil grafik menggunakan:
          plt.savefig("chart.png", dpi=300, bbox_inches="tight")
        """

        try:
            base_dir = DATA_DIR.resolve()
            filepath = (base_dir / filename).resolve()
            if not filepath.is_relative_to(base_dir):
                raise ValueError("Akses file di luar data_storage tidak diizinkan")

            if not filepath.exists():
                raise FileNotFoundError(f"File '{filename}' tidak ditemukan")

            suffix = filepath.suffix.lower()
            if suffix not in [".csv", ".xlsx", ".xls"]:
                raise ValueError("Format hanya mendukung CSV dan Excel")

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            counter = 1
            while True:
                output_path = OUTPUT_DIR / f"{filepath.stem}_chart_{counter}.png"
                if not output_path.exists():
                    break

                counter += 1

            sandbox = await AsyncSandbox.create()
            try:
                with open(filepath, "rb") as f:
                    file_bytes = f.read()

                await sandbox.files.write(filename, file_bytes)
                execution = await sandbox.run_code(python_code, timeout=60)

                if execution.error:
                    raise RuntimeError(
                        f"{execution.error.name}: "
                        f"{execution.error.value}\n"
                        f"{execution.error.traceback}")

                image_bytes = await sandbox.files.read("chart.png", format="bytes")
                if not image_bytes:
                    raise ValueError("Grafik PNG tidak berhasil dibuat")

                with open(output_path, "wb") as f:
                    f.write(image_bytes)

                return MCPImage(data=image_bytes, format="png")

            finally:
                await sandbox.kill()

        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"Error membuat grafik ({type(e).__name__}): {str(e)}")

import pandas as pd
from pathlib import Path
from pypdf import PdfReader

DATA_DIR = Path("data_storage")

def register_file_schema(mcp):

    @mcp.tool()
    async def get_file_schema(filename: str) -> str:
        """
        Mengambil skema file (kolom dan sampel data untuk CSV/Excel)
        Gunakan tool ini PERTAMA KALI saat pengguna mengunggah file CSV/Excel
        
        PERINGATAN STRICT:
        - Dilarang dipanggil untuk data API (Sales Performance, Asset, Customer)
        - HANYA dipanggil jika ada argumen `filename` file yang diunggah
        """

        try:
            base_dir = DATA_DIR.resolve()
            filepath = (base_dir / filename).resolve()
            if not filepath.is_relative_to(base_dir):
                return "Error: Akses file diluar data_storage tidak diizinkan"

            if not filepath.exists():
                return f"Error: File '{filename}' tidak ditemukan"

            suffix = filepath.suffix.lower()
            if suffix == ".csv":
                df = pd.read_csv(filepath, nrows=5, low_memory=False)
                with open(filepath, "r", encoding="utf-8", errors='ignore') as f:
                    total_rows = sum(1 for _ in f) - 1
            elif suffix in [".xlsx", ".xls"]:
                df = pd.read_excel(filepath, nrows=5)
                total_rows = "Banyak (excel File)"
            else:
                return "Error: Format hanya mendukung CSV dan Excel"

            if df.empty:
                return "Error: dataset Kosong"

            output = []
            output.append(f"File Name: {filename}")
            output.append(f"Total Baris: {total_rows}, Total Kolom: {len(df.columns)}")
            output.append("\nDaftar Nama Kolom dan Tipe Data:")
            for col, dtype in df.dtypes.items():
                output.append(f"- '{col}' ({dtype})")

            output.append("\nSample Data:")
            output.append(df.to_string(index=False))

            return "\n".join(output)

        except Exception as e:
            return f"Error membaca schema: {str(e)}"
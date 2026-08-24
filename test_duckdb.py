from pathlib import Path
import duckdb
import pandas as pd

# =========================================================================
# 1. GANTI NAMA FILE DI SINI SESUAI FILE YANG ADA DI FOLDER KAMU
# =========================================================================
FILE_NAME = "/Users/diajeng/Documents/si-smart/data_storage/LAPORAN TEGAKAN.csv"  # Ganti jadi "nama_file_kamu.csv" atau "nama_file_kamu.xlsx"
DATA_DIR = Path("/Users/diajeng/Documents/si-smart/data_storage")  # Sesuai folder penyimpanan kamu
FILE_PATH = DATA_DIR / FILE_NAME
DB_FILE = Path("my_data.duckdb")


def main():
    print(f"=== 1. PENGECEKAN FILE ===")
    if not FILE_PATH.exists():
        print(f"❌ ERROR: File '{FILE_PATH.absolute()}' tidak ditemukan!")
        print("Silakan pastikan file CSV/Excel sudah ada di folder tersebut.")
        return

    suffix = FILE_PATH.suffix.lower()
    print(f"✅ File ditemukan: {FILE_PATH.name} (Format: {suffix})\n")

    print(f"=== 2. MENGHUBUNGKAN KE DUCKDB & IMPORT DATA ===")
    # Membuka/membuat database DuckDB berbasis file (persistent)
    con = duckdb.connect(str(DB_FILE))

    try:
        if suffix == ".csv":
            print("Importing file CSV ke DuckDB via read_csv_auto()...")
            # DuckDB membaca file CSV langsung dari disk secara otomatis
            con.execute(f"""
                CREATE OR REPLACE TABLE dataset AS 
                SELECT * FROM read_csv_auto('{FILE_PATH}', ignore_errors=true)
            """)

        elif suffix in [".xlsx", ".xls"]:
            print("Importing file Excel via Pandas ke DuckDB...")
            # Untuk Excel, load dulu lewat Pandas lalu register ke DuckDB
            df_excel = pd.read_excel(FILE_PATH)
            con.register("temp_excel", df_excel)
            con.execute(
                "CREATE OR REPLACE TABLE dataset AS SELECT * FROM temp_excel"
            )

        else:
            print(f"❌ Format {suffix} tidak didukung.")
            return

        print(f"✅ Data berhasil dimasukkan ke tabel 'dataset' di DuckDB!\n")

    except Exception as e:
        print(f"❌ Error saat import data: {str(e)}")
        return

    print("=== 3. EKSEKUSI QUERY DAN TAMPILKAN HASIL ===")

    # A. Cek Total Baris & Kolom
    total_rows = con.execute("SELECT COUNT(*) FROM dataset").fetchone()[0]
    print(f"📊 Total Baris di Database: {total_rows:,} baris")

    # B. Tampilkan Schema / Kolom
    print("\n📋 Daftar Kolom & Tipe Data:")
    schema_df = con.execute("DESCRIBE dataset").df()
    print(schema_df[["column_name", "column_type"]].to_string(index=False))

    # C. Tampilkan 5 Baris Pertama
    print("\n🔍 Sampel 5 Baris Pertama Data:")
    sample_df = con.execute("SELECT * FROM dataset LIMIT 5").df()
    print(sample_df.to_string(index=False))

    # D. Tes Query Agregasi Sederhana
    print("\n" + "=" * 50)
    print("⚡ Uji Coba Query Agregasi Sederhana:")
    # Mengambil kolom pertama sebagai contoh agregasi
    first_col = schema_df["column_name"].iloc[0]
    query_test = (
        f"SELECT {first_col}, COUNT(*) as total FROM dataset GROUP BY 1 LIMIT 5"
    )
    print(f"Executing Query: {query_test}\n")

    result_df = con.execute(query_test).df()
    print(result_df.to_string(index=False))

    # Tutup koneksi
    con.close()
    print("\n=== PROSES SELESAI & SUKSES ===")


if __name__ == "__main__":
    main()
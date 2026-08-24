import os
import httpx
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

API_BASE_URL = os.getenv("API_BASE_URL")
CHROMA_DIR = "chroma_sales_db" 

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

async def sync_sales_api_to_vector_db():
    """
    Mengambil data raksasa dari API dan menyimpannya secara permanen ke Vector DB Chroma.
    Fungsi ini dijalankan berkala atau saat startup jika data diperbarui.
    """
    url = f"{API_BASE_URL}/sales-performance"
    
    print("Menghubungi API Sales untuk sinkronisasi data raksasa...")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60)
        response.raise_for_status()
        result = response.json()
        data_sales = result.get("data", [])

    if not data_sales:
        print("Data dari API kosong, sinkronisasi dibatalkan.")
        return

    documents = []
    print(f"Memproses {len(data_sales)} baris data menjadi vektor chunks...")
    
    for row in data_sales:
        text_content = (
            f"Nama Sales: {row.get('sales_name')}. "
            f"Region/Wilayah Kerja: {row.get('region')}. "
            f"Target Penjualan: Rp {row.get('total_target')}. "
            f"Pencapaian Realisasi: Rp {row.get('total_achievement')}. "
            f"Periode: {row.get('period')}."
        )

        doc = Document(
            page_content=text_content,
            metadata={
                "sales_name": row.get("sales_name"),
                "region": row.get("region"),
                "total_achievement": row.get("total_achievement"),
                "period": row.get("period")
            }
        )
        documents.append(doc)

    Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )
    print("Sinkronisasi Sukses! Data aman tersimpan di Vector DB lokal.")

def query_sales_rag(user_query: str, k: int = 5) -> str:
    """
    Fungsi pencarian cepat di dalam Vector DB tanpa memakan RAM server.
    Mencari 'k' baris data yang paling cocok dengan pertanyaan user.
    """

    db = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    results = db.similarity_search(user_query, k=k)
    
    if not results:
        return "Tidak ditemukan data sales yang cocok di database."

    formatted_context = "\n".join([f"- {doc.page_content}" for doc in results])
    return formatted_context

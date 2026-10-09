import duckdb
from langchain_community.embeddings import FastEmbedEmbeddings

embedder = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

def is_malicious_prompt(user_prompt: str, threshold: float = 0.82) -> tuple[bool, str]:
    """
    Mengembalikan (True, Alasan) jika prompt terindikasi berbahaya.
    """
    con = duckdb.connect("data_storage/security_jailbreaks.duckdb")
    con.execute("LOAD vss;")
    
    query_vector = embedder.embed_query(user_prompt.lower())
    
    result = con.execute("""
        SELECT pattern, category, array_similarity(embedding, ?::FLOAT[384]) as similarity
        FROM malicious_patterns
        ORDER BY similarity DESC
        LIMIT 1
    """, (query_vector,)).fetchone()
    
    if result:
        matched_pattern, category, score = result
        if score >= threshold:
            print(f"[SECURITY ALERT] Terdeteksi {category} (Score: {score:.2f}) -> Match: '{matched_pattern}'")
            return True, f"Permintaan ditolak karena terindikasi {category}."
            
    return False, ""
# --- SUPABASE BAĞLANTISI ---
@st.cache_resource
def init_supabase() -> Client:
    # Secrets panelinden gelen metindeki tüm gizli boşlukları ve satır bölünmelerini temizle
    url = "".join(str(st.secrets.get("SUPABASE_URL", "")).split()).strip('"').strip("'")
    key = "".join(str(st.secrets.get("SUPABASE_KEY", "")).split()).strip('"').strip("'").strip("'''")
    
    if not url.startswith("http"):
        url = "https://" + url
        
    if not url or not key:
        st.error("Supabase URL veya API Anahtarı Secrets alanında bulunamadı!")
        st.stop()
    return create_client(url, key)

supabase = init_supabase()

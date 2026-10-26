import os
import json
import pandas as pd
from datetime import datetime
import uuid
import streamlit as st
import plotly.express as px
from supabase import create_client, Client

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Kesintisiz Yönetim Sistemi", layout="wide")

# --- LOKAL VERİTABANI DOSYASI VE KLASÖRLER ---
DB_FILE = "notes_database.json"
CONFIG_FILE = "notes_config.json"
UPLOAD_DIR = "uploaded_images"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- SUPABASE BAĞLANTISI ---
@st.cache_resource
def init_supabase():
    url = "".join(str(st.secrets.get("SUPABASE_URL", "")).split())
    key = "".join(str(st.secrets.get("SUPABASE_KEY", "")).split())
    if not url.startswith("http"):
        url = "https://" + url
    return create_client(url, key)

supabase = init_supabase()
BUCKET_NAME = "notes-media"

# --- YARDIMCI FONKSİYONLAR ---
def load_records():
    try:
        response = supabase.table("notes_records").select("*").order("id", desc=True).execute()
        records = response.data if response and response.data else []
        
        for r in records:
            paths = []
            raw_paths = r.get("image_paths", [])
            if not raw_paths and r.get("image_path"):
                raw_paths = [r.get("image_path")]
            if isinstance(raw_paths, str):
                raw_paths = [raw_paths]
            
            for p in raw_paths:
                if p:
                    p_str = str(p).strip()
                    # Sadece geçerli ve ulaşılabilir olanları listeye ekle
                    if p_str.startswith("http") or os.path.exists(p_str):
                        paths.append(p_str)
            r["image_paths"] = paths
        return records
    except Exception as e:
        try:
            response = supabase.table("notes").select("*").execute()
            return response.data if response and response.data else []
        except Exception as inner_e:
            st.error(f"Veriler yüklenirken hata oluştu: {inner_e}")
            return []

def save_records(records):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"admin_password": "1234"}
    return {"admin_password": "1234"}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def save_images(uploaded_files):
    """Birden fazla görseli Supabase Storage'a yükler ve public URL'lerini döndürür."""
    image_paths = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            try:
                file_ext = os.path.splitext(uploaded_file.name)[1]
                unique_filename = f"{uuid.uuid4().hex}_{int(datetime.now().timestamp())}{file_ext}"
                file_bytes = uploaded_file.getvalue()
                
                supabase.storage.from_(BUCKET_NAME).upload(
                    path=unique_filename,
                    file=file_bytes,
                    file_options={"content-type": uploaded_file.type}
                )
                
                public_url_response = supabase.storage.from_(BUCKET_NAME).get_public_url(unique_filename)
                if public_url_response:
                    image_paths.append(public_url_response)
            except Exception as e:
                st.error(f"Resim yüklenirken hata oluştu: {e}")
    return image_paths

# --- UYGULAMA ANA AKIŞI ---
config = load_config()
records = load_records()

st.title("📝 Notes - Hata ve Kayıt Takip Paneli")

# --- YENİ KAYIT EKLEME FORMU ---
with st.expander("➕ Yeni Kayıt / Hata Ekle"):
    with st.form("add_form", clear_on_submit=True):
        new_text = st.text_input("Text (İsim):")
        new_date = st.text_input("Date (Tarih):", value=datetime.now().strftime("%d/%m/%Y"))
        new_note = st.text_area("Not / Açıklama:")
        new_images = st.file_uploader("Files & media (Resim Yükle - Çoklu Seçim):", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        submit_btn = st.form_submit_button("Tabloya Ekle")
        if submit_btn:
            uploaded_urls = save_images(new_images)
            max_id = max([r.get("id", 0) for r in records], default=0) if records else 0
            new_record = {
                "id": max_id + 1,
                "text": new_text,
                "date": new_date,
                "note": new_note,
                "image_paths": uploaded_urls
            }
            try:
                supabase.table("notes_records").insert(new_record).execute()
                st.success("Kayıt başarıyla eklendi!")
                st.rerun()
            except Exception as e:
                st.error(f"Kayıt eklenirken hata oluştu: {e}")

# --- ARAMA VE LİSTELEME ---
search_query = st.text_input("🔍 Kayıtlarda Arama Yap (İsim veya Not):")

filtered_records = records
if search_query:
    filtered_records = [
        r for r in records 
        if search_query.lower() in str(r.get("text", "")).lower() or search_query.lower() in str(r.get("note", "")).lower()
    ]

if filtered_records:
    st.write(f"Toplam {len(filtered_records)} kayıt gösteriliyor.")
    
    col_h1, col_h2, col_h3, col_h4 = st.columns([2, 1, 1, 1])
    with col_h1:
        st.markdown("**İsim & Not**")
    with col_h2:
        st.markdown("**Tarih**")
    with col_h3:
        st.markdown("**Görsel**")
    with col_h4:
        st.markdown("**İşlem**")
    st.markdown("---")

    for r in filtered_records:
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            name_val = r.get('text', '') or r.get('name', 'İsimsiz')
            st.markdown(f"**{name_val}**")
            st.caption(r.get('note', ''))
            
        with col2:
            st.write(r.get('date', ''))
            
        with col3:
            imgs = r.get("image_paths", [])
            if imgs:
                for img_url in imgs:
                    try:
                        st.image(img_url, width=45)
                    except Exception:
                        st.write("-")
            else:
                st.write("-")
                    
        with col4:
            if st.button("Sil", key=f"del_{r.get('id', 0)}"):
                try:
                    supabase.table("notes_records").delete().eq("id", r.get('id')).execute()
                    st.success("Kayıt silindi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Silinirken hata oluştu: {e}")
                
        st.markdown("---")
else:
    st.info("Aramanıza uygun veya henüz eklenmiş bir kayıt bulunmuyor.")

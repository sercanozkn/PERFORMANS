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
            if "image_path" in r and "image_paths" not in r:
                r["image_paths"] = [r["image_path"]] if r["image_path"] else []
            if "image_paths" in r and isinstance(r["image_paths"], list):
                r["image_paths"] = [p for p in r["image_paths"] if p and str(p).startswith("http")]
            else:
                r["image_paths"] = []
        return records
    except Exception as e:
        st.error(f"Veriler yüklenirken hata oluştu: {e}")
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
                
                # Supabase Storage'a yükleme
                supabase.storage.from_(BUCKET_NAME).upload(
                    path=unique_filename,
                    file=file_bytes,
                    file_options={"content-type": uploaded_file.type}
                )
                
                # Public URL alma
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

# Arama ve Filtreleme
search_query = st.text_input("🔍 Kayıtlarda Arama Yap (İsim veya Not):")

filtered_records = records
if search_query:
    filtered_records = [
        r for r in records 
        if search_query.lower() in str(r.get("text", "")).lower() or search_query.lower() in str(r.get("note", "")).lower()
    ]

if filtered_records:
    st.write(f"Toplam {len(filtered_records)} kayıt gösteriliyor.")
    for r in filtered_records:
        st.markdown(f"**İsim:** {r.get('text', '')} | **Tarih:** {r.get('date', '')}")
        st.markdown(f"**Not:** {r.get('note', '')}")
        
        # Resimler varsa minyatür olarak göster
        imgs = r.get("image_paths", [])
        if imgs:
            cols = st.columns(min(len(imgs), 3))
            for idx, img_url in enumerate(imgs):
                with cols[idx % len(cols)]:
                    st.image(img_url, width=100)
        st.divider()
else:
    st.info("Aramanıza uygun veya henüz eklenmiş bir kayıt bulunmuyor.")

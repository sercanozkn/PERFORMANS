import streamlit as st
import os
import pandas as pd
from collections import Counter
from supabase import create_client, Client

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Hata Yönetim Sistemi", layout="wide")

# --- SUPABASE BULUT BAĞLANTISI ---
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_connection()

# --- GÜVENLİ VERİ FONKSİYONLARI (Asla çökmez, sessizce boş döner) ---
def load_records():
    try:
        response = supabase.table("notes_records").select("*").execute()
        return response.data if response.data else []
    except:
        return []

def save_record_to_db(record_data):
    try:
        supabase.table("notes_records").insert(record_data).execute()
    except Exception as e:
        st.error(f"Kayıt eklenemedi: {e}")

def delete_record_from_db(record_id):
    try:
        supabase.table("notes_records").delete().eq("id", record_id).execute()
    except Exception as e:
        st.error(f"Kayıt silinemedi: {e}")

def load_config():
    try:
        response = supabase.table("notes_config").select("*").execute()
        if response.data:
            config_dict = {}
            for row in response.data:
                config_dict[row.get("key")] = row.get("value")
            return config_dict
        return {"admin_password": "1234"}
    except:
        return {"admin_password": "1234"}

def save_config_to_db(key, value):
    try:
        supabase.table("notes_config").upsert({"key": key, "value": value}).execute()
    except:
        pass

# --- OTURUM ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "zoomed_image" not in st.session_state:
    st.session_state.zoomed_image = None

# --- GİRİŞ ---
def check_password():
    config = load_config()
    admin_pass = config.get("admin_password", "1234")
    
    if not st.session_state.authenticated:
        st.title("🔒 Giriş Yap")
        with st.form("login_form"):
            username = st.text_input("Kullanıcı Adı:", value="admin")
            password = st.text_input("Şifre:", type="password")
            if st.form_submit_button("Giriş Yap"):
                if username == "admin" and password == admin_pass:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Hatalı şifre!")
        return False
    return True

if not check_password():
    st.stop()

# --- ANA UYGULAMA ---
UPLOAD_DIR = "uploaded_images"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

st.title("📄 Notes - Hata Takip Paneli")
st.success("🟢 Sistem Hazır - Kayıtlarınızı ekleyebilirsiniz.")
st.markdown("---")

if st.sidebar.button("Çıkış Yap"):
    st.session_state.authenticated = False
    st.rerun()

# --- YENİ KAYIT EKLEME FORMU ---
with st.form("entry_form", clear_on_submit=True):
    st.subheader("➕ Yeni Kayıt / Hata Ekle")
    name = st.text_input("Text (İsim):")
    date = st.date_input("Date (Tarih):", format="DD/MM/YYYY")
    note = st.text_area("Not / Açıklama:")
    uploaded_files = st.file_uploader("Files & media (Resim Yükle):", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    if st.form_submit_button(label="Tabloya Ekle") and name and note:
        image_paths = []
        if uploaded_files:
            for uf in uploaded_files:
                img_path = os.path.join(UPLOAD_DIR, uf.name)
                with open(img_path, "wb") as f:
                    f.write(uf.getbuffer())
                image_paths.append(img_path)
        
        new_item = {
            "name": name,
            "date": str(date),
            "note": note,
            "image_path": image_paths[0] if image_paths else None,
            "image_paths": image_paths,
            "has_image": len(image_paths) > 0
        }
        save_record_to_db(new_item)
        st.success("Kayıt başarıyla eklendi!")
        st.rerun()

# --- TABLO ---
st.markdown("---")
st.subheader("📋 All notes (Kayıt ve Hata Tablosu)")
records = load_records()

if records:
    for idx, record in enumerate(records):
        col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
        with col1:
            st.markdown(f"**{record.get('name', '')}**")
            st.caption(f"{record.get('note', '')}")
        with col2:
            st.write(record.get('date', ''))
        with col3:
            if record.get('image_path') and os.path.exists(record.get('image_path')):
                st.image(record.get('image_path'), width=50)
        with col4:
            if st.button("🗑️ Sil", key=f"del_{idx}"):
                delete_record_from_db(record.get("id"))
                st.rerun()
        st.markdown("---")
else:
    st.info("Henüz kayıt bulunmuyor. Yeni kayıt ekleyebilirsiniz.")

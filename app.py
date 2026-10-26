import os
import json
from datetime import datetime
import uuid
import streamlit as st
import plotly.express as px
from supabase import create_client, Client

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Kesintisiz Yonetim Sistemi", layout="wide")

# --- SUPABASE BAGLANTISI ---
@st.cache_resource
def init_supabase():
    url = "".join(str(st.secrets.get("SUPABASE_URL", "")).split())
    key = "".join(str(st.secrets.get("SUPABASE_KEY", "")).split())
    if not url.startswith("http"):
        url = "https://" + url
    return create_client(url, key), url

supabase, SUPABASE_URL = init_supabase()
BUCKET_NAME = "notes-media"

# --- OTURUM & KULLANICI YONETIMI ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🔐 Notes - Kullanici Girisi")

    with st.form("login_form"):
        username_input = st.text_input("Kullanıcı Adı:")
        password_input = st.text_input("Şifre:", type="password")
        login_btn = st.form_submit_button("Giriş Yap")
        
        if login_btn:
            if username_input.strip().lower() == "sercan" and password_input.strip() == "134679":
                st.session_state["logged_in"] = True
                st.session_state["username"] = "sercan"
                st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")
    st.stop()

# --- VERILERI YUKLEME ---
def load_records():
    try:
        response = supabase.table("notes_records").select("*").order("id", desc=True).execute()
        records = response.data if response and response.data else []
        for r in records:
            paths = []
            raw_paths = r.get("image_paths", [])
            if isinstance(raw_paths, str):
                try:
                    raw_paths = json.loads(raw_paths.replace("'", '"'))
                except Exception:
                    raw_paths = [raw_paths]
            if not isinstance(raw_paths, list):
                raw_paths = [raw_paths]
            for p in raw_paths:
                if p:
                    p_str = str(p).strip("[]'\" ")
                    if p_str.startswith("http"):
                        for sub_p in p_str.split("https://"):
                            if sub_p.strip():
                                clean_url = "https://" + sub_p.strip("[]'\" ,")
                                if clean_url not in paths:
                                    paths.append(clean_url)
            r["image_paths"] = paths
        return records
    except Exception as e:
        st.error(f"Veriler yüklenirken hata oluştu: {e}")
        return []

def save_images(uploaded_files):
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
                clean_base_url = SUPABASE_URL.rstrip('/')
                public_url = f"{clean_base_url}/storage/v1/object/public/{BUCKET_NAME}/{unique_filename}"
                image_paths.append(public_url)
            except Exception as e:
                st.error(f"Resim yüklenirken hata oluştu: {e}")
    return image_paths

# --- SOL MENU / YONETIM PANELI ---
st.sidebar.title("🛠️ Yonetim Paneli")

with st.sidebar.expander("➕ Yeni Kayit / Hata Ekle", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        new_name = st.text_input("Isim / Baslik:")
        new_date = st.text_input("Tarih:", value=datetime.now().strftime("%d/%m/%Y"))
        new_note = st.text_area("Not / Aciklama:")
        new_images = st.file_uploader("Gorsel Yukle:", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        submit_btn = st.form_submit_button("Tabloya Ekle")
        if submit_btn:
            if not new_name.strip():
                st.warning("Lutfen bir isim/baslik girin.")
            else:
                uploaded_urls = save_images(new_images)
                new_record = {
                    "name": new_name,
                    "date": new

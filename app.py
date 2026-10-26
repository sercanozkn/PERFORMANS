import os
import json
from datetime import datetime
import uuid
import streamlit as st
import plotly.express as px
from supabase import create_client, Client

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Yonetim Sistemi", layout="wide")

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

# --- OTURUM VE KİMLİK YÖNETİMİ ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "app_username" not in st.session_state:
    st.session_state["app_username"] = "admin"

if "app_password" not in st.session_state:
    st.session_state["app_password"] = "1234"

if not st.session_state["logged_in"]:
    st.title("Kullanici Giris Paneli")
    with st.form("login_form"):
        username_input = st.text_input("Kullanici Adi:")
        password_input = st.text_input("Sifre:", type="password")
        login_btn = st.form_submit_button("Giris Yap")
        
        if login_btn:
            if username_input == st.session_state["app_username"] and password_input == st.session_state["app_password"]:
                st.session_state["logged_in"] = True
                st.success("Giris basarili! Yonlendiriliyorsunuz...")
                st.rerun()
            else:
                st.error("Kullanici adi veya sifre hatali!")
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
        st.error(f"Veriler yuklenirken hata olustu: {e}")
        return []

# --- RESIM YUKLEME ---
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
                st.error(f"Resim yuklenirken hata olustu: {e}")
    return image_paths

# --- SOL MENU / YONETIM PANELI ---
st.sidebar.title("Yonetim Paneli")

# 1. Yeni Kayit Ekleme Bolumu
with st.sidebar.expander("Yeni Kayit / Hata Ekle", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        new_name = st.text_input("Isim / Baslik:")
        new_date = st.text_input("Tarih:", value=datetime.now().strftime("%d/%m/%Y"))
        new_note = st.text_area("Not / Aciklama:")
        new_images = st.file_uploader("Gorsel Yukle (Coklu Secim):", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        submit_btn = st.form_submit_button("Tabloya Ekle")
        if submit_btn:
            records_check = load_records()
            uploaded_urls = save_images(new_images)
            max_id = max([r.get("id", 0) for r in records_check], default=0) if records_check else 0
            
            new_record = {
                "id": max_id + 1,
                "name": new_name,
                "date": new_date,
                "note": new_note,
                "image_paths": uploaded_urls
            }
            try:
                supabase.table("notes_records").insert(new_record).execute()
                st.success("Kayit basariyla eklendi!")
                st.rerun()
            except Exception as e:
                st.error(f"Kayit eklenirken hata olustu: {e}")

# 2. Ayarlar Sekmesi (Sifre ve Kullanici Adi Degistirme)
with st.sidebar.expander("Ayarlar", expanded=False):
    with st.form("settings_form"):
        st.write("Kullanici Bilgileri")
        current_username = st.text_input("Mevcut Kullanici Adi:")
        new_username = st.text_input("Yeni Kullanici Adi:")
        
        st.write("Sifre Degistir")
        current_password = st.text_input("Mevcut Sifre:", type="password")
        new_password = st.text_input("Yeni Sifre:", type="password")
        confirm_password = st.text_input("Yeni Sifre (Tekrar):", type="password")
        
        settings_submit = st.form_submit_button("Degisiklikleri Kaydet")
        if settings_submit:
            if current_username != st.session_state["app_username"] or current_password != st.session_state["app_password"]:
                st.error("Mevcut kullanici adi veya sifre hatali!")
            elif new_password and new_password != confirm_password:
                st.error("Yeni sifreler birbiriyle uyusmuyor!")
            else:
                if new_username.strip():
                    st.session_state["app_username"] = new_username.strip()
                if new_password.strip():
                    st.session_state["app_password"] = new_password.strip()
                st.success("Ayarlar basariyla guncellendi!")

st.sidebar.markdown("---")
# 3. Cikis Yap Butonu
if st.sidebar.button("Cikis Yap"):
    st.session_state["logged_in"] = False
    st.rerun()

# --- ANA EKRAN ---
st.

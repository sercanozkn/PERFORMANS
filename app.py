import os
import json
from datetime import datetime
import uuid
import streamlit as st
import plotly.express as px
from supabase import create_client, Client

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Kesintisiz Yönetim Sistemi", layout="wide")

# --- SUPABASE BAĞLANTISI ---
@st.cache_resource
def init_supabase():
    url = "".join(str(st.secrets.get("SUPABASE_URL", "")).split())
    key = "".join(str(st.secrets.get("SUPABASE_KEY", "")).split())
    if not url.startswith("http"):
        url = "https://" + url
    return create_client(url, key), url

supabase, SUPABASE_URL = init_supabase()
BUCKET_NAME = "notes-media"

# --- OTURUM & KULLANICI YÖNETİMİ ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🔐 Notes - Kullanıcı Girişi")
    
    try:
        res = supabase.table("notes_users").select("*").execute()
        users_list = res.data if res.data else []
    except Exception as e:
        users_list = []
        st.error(f"Veritabanı bağlantı hatası: {e}")

    with st.form("login_form"):
        username_input = st.text_input("Kullanıcı Adı:")
        password_input = st.text_input("Şifre:", type="password")
        login_btn = st.form_submit_button("Giriş Yap")
        
        if login_btn:
            login_success = False
            matched_user_id = None
            for u in users_list:
                if str(u.get("username")).strip() == username_input.strip() and str(u.get("password")).strip() == password_input.strip():
                    login_success = True
                    matched_user_id = u.get("id")
                    break
            
            if login_success:
                st.session_state["logged_in"] = True
                st.session_state["user_id"] = matched_user_id
                st.session_state["username"] = username_input.strip()
                st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")
    st.stop()

# --- VERİLERİ YÜKLEME ---
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

# --- RESİM YÜKLEME ---
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

# --- SOL MENÜ / YÖNETİM PANELİ ---
st.sidebar.title("🛠️ Yönetim Paneli")

with st.sidebar.expander("➕ Yeni Kayıt / Hata Ekle", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        new_name = st.text_input("İsim / Başlık:")
        new_date = st.text_input("Tarih:", value=datetime.now().strftime("%d/%m/%Y"))
        new_note = st.text_area("Not / Açıklama:")
        new_images = st.file_uploader("Görsel Yükle (Çoklu Seçim):", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        submit_btn = st.form_submit_button("Tabloya Ekle")
        if submit_btn:
            if not new_name.strip():
                st.warning("Lütfen bir isim/başlık girin.")
            else:
                uploaded_urls = save_images(new_images)
                
                new_record = {
                    "name": new_name,
                    "date": new_date,
                    "note": new_note,
                    "image_paths": uploaded_urls
                }
                try:
                    supabase.table("notes_records").insert(new_record).execute()
                    st.success("Kayıт başarıyla eklendi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kayıt eklenirken hata oluştu: {e}")

with st.sidebar.expander("⚙️ Ayarlar", expanded=False):
    with st.form("settings_form"):
        st.write("**Kullanıcı Bilgileri Değiştir**")
        current_user_check = st.text_input("Mevcut Kullanıcı Adı:")
        new_username = st.text_input("Yeni Kullanıcı Adı (İsteğe bağlı):")
        
        st.write("**Şifre De

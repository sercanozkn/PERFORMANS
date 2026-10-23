import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Kesintisiz Yönetim Sistemi", layout="wide")

# --- LOKAL VERİTABANI DOSYASI ---
DB_FILE = "notes_database.json"
CONFIG_FILE = "notes_config.json"
UPLOAD_DIR = "uploaded_images"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def load_records():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_records(records):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"admin_password": "1234"}
    return {"admin_password": "1234"}

# --- OTURUM ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- GİRİŞ KONTROLÜ ---
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
st.title("📄 Notes - Kesintisiz Takip Paneli")
st.success("🟢 Sistem Kararlı Çalışıyor - Lokal Mod Aktif.")
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
    
    submit_btn = st.form_submit_button(label="Tabloya Ekle")
    
    if submit_btn:
        if name and note:
            image_path = None
            if uploaded_files:
                uf = uploaded_files[0]
                image_path = os.path.join(UPLOAD_DIR, uf.name)
                with open(image_path, "wb") as f:
                    f.write(uf.getbuffer())
            
            records = load_records()
            new_id = int(datetime.now().timestamp() * 1000)
            
            new_item = {
                "id": new_id,
                "name": name,
                "date": str(date),
                "note": note,
                "image_path": image_path,
                "has_image": bool(image_path)
            }
            
            records.append(new_item)
            save_records(records)
            st.success("Kayıt başarıyla eklendi!")
            st.rerun()
        else:
            st.warning("Lütfen İsim ve Not alanlarını doldurun.")

# --- TABLO ---
st.markdown("---")
st.subheader("📋 All notes (Kayıt ve Hata Tablosu)")
records = load_records()

if records:
    for record in records:
        col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
        with col1:
            st.markdown(f"**{record.get('name', '')}**")
            st.caption(f"{record.get('note', '')}")
        with col2:
            st.write(record.get('date', ''))
        with col3:
            img_p = record.get('image_path')
            if img_p and os.path.exists(img_p):
                st.image(img_p, width=50)
            else:
                st.write("-")
        with col4:
            if st.button("🗑️ Sil", key=f"del_{record.get('id')}"):
                updated_records = [r for r in records if r.get('id') != record.get('id')]
                save_records(updated_records)
                st.rerun()
        st.markdown("---")
else:
    st.info("Henüz kayıt bulunmuyor. Yeni kayıt ekleyebilirsiniz.")

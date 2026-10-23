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
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

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
st.title("📄 Notes - Hata ve Kayıt Takip Paneli")
st.success("🟢 Kararlı Lokal Mod Aktif (Gün/Ay/Yıl Tarih Formatı)")
st.markdown("---")

if st.sidebar.button("Çıkış Yap"):
    st.session_state.authenticated = False
    st.rerun()

records = load_records()

# --- DÜZENLEME MODU VEYA YENİ KAYIT FORMU ---
editing_record = None
if st.session_state.edit_id is not None:
    for r in records:
        if r.get("id") == st.session_state.edit_id:
            editing_record = r
            break

if editing_record:
    st.subheader("✏️ Kaydı Düzenle")
    with st.form("edit_form"):
        e_name = st.text_input("Text (İsim):", value=editing_record.get("name", ""))
        
        date_str = editing_record.get("date", datetime.now().strftime("%d/%m/%Y"))
        try:
            default_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        except:
            try:
                default_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                default_date = datetime.now().date()
                
        e_date = st.date_input("Date (Tarih):", value=default_date, format="DD/MM/YYYY")
        e_note = st.text_area("Not / Açıklama:", value=editing_record.get("note", ""))
        
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            update_btn = st.form_submit_button("Değişiklikleri Kaydet")
        with col_up2:
            cancel_btn = st.form_submit_button("İptal")
            
        if update_btn:
            for r in records:
                if r.get("id") == st.session_state.edit_id:
                    r["name"] = e_name
                    r["date"] = e_date.strftime("%d/%m/%Y")
                    r["note"] = e_note
            save_records(records)
            st.session_state.edit_id = None
            st.success("Kayıt başarıyla güncellendi!")
            st.rerun()
        if cancel_btn:
            st.session_state.edit_id = None
            st.rerun()
else:
    with st.form("entry_form", clear_on_submit=True):
        st.subheader("➕ Yeni Kayıt / Hata Ekle")

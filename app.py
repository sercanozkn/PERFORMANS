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
st.success("🟢 Kararlı Lokal Mod Aktif")
st.markdown("---")

if st.sidebar.button("Çıkış Yap"):
    st.session_state.authenticated = False
    st.rerun()

records = load_records()

# --- DÜZENLEME MODU VEYA YENİ KAYIT ---
editing_record = None
if st.session_state.edit_id is not None:
    for r in records:
        if r.get("id") == st.session_state.edit_id:
            editing_record = r
            break

if editing_record:
    st.subheader("✏️ Kaydı Düzenle")
    e_name = st.text_input("Text (İsim):", value=editing_record.get("name", ""), key="edit_name")
    
    date_str = editing_record.get("date", datetime.now().strftime("%d/%m/%Y"))
    try:
        default_date = datetime.strptime(date_str, "%d/%m/%Y").date()
    except:
        try:
            default_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            default_date = datetime.now().date()
            
    e_date = st.date_input("Date (Tarih):", value=default_date, format="DD/MM/YYYY", key="edit_date")
    e_note = st.text_area("Not / Açıklama:", value=editing_record.get("note", ""), key="edit_note")
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        if st.button("💾 Değişiklikleri Kaydet", use_container_width=True):
            for r in records:
                if r.get("id") == st.session_state.edit_id:
                    r["name"] = e_name
                    r["date"] = e_date.strftime("%d/%m/%Y")
                    r["note"] = e_note
            save_records(records)
            st.session_state.edit_id = None
            st.success("Kayıt başarıyla güncellendi!")
            st.rerun()
    with col_up2:
        if st.button("❌ İptal", use_container_width=True):
            st.session_state.edit_id = None
            st.rerun()
else:
    st.subheader("➕ Yeni Kayıt / Hata Ekle")
    name = st.text_input("Text (İsim):", key="new_name")
    date = st.date_input("Date (Tarih):", format="DD/MM/YYYY", key="new_date")
    note = st.text_area("Not / Açıklama:", key="new_note")
    uploaded_files = st.file_uploader("Files & media (Resim Yükle):", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="new_file")
    
    if st.button("Tabloya Ekle", type="primary"):
        if name and note:
            image_path = None
            if uploaded_files:
                uf = uploaded_files[0]
                image_path = os.path.join(UPLOAD_DIR, uf.name)
                with open(image_path, "wb") as f:
                    f.write(uf.getbuffer())
            
            new_id = int(datetime.now().timestamp() * 1000)
            new_item = {
                "id": new_id,
                "name": name,
                "date": date.strftime("%d/%m/%Y"),
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

# --- GRAFİK / İSTATİSTİK BÖLÜMÜ ---
st.markdown("---")
st.subheader("📊 Grafik / İstatistikler")
if records:
    df_chart = pd.DataFrame(records)
    if "date" in df_chart.columns and not df_chart.empty:
        date_counts = df_chart["date"].value_counts().reset_index()
        date_counts.columns = ["Tarih", "Kayıt Sayısı"]
        date_counts = date_counts.set_index("Tarih")
        st.bar_chart(date_counts)
    else:
        st.info("Grafik için yeterli veri bulunmuyor.")
else:
    st.info("Henüz istatistik oluşturulacak kayıt yok.")

# --- TABLO VE YÖNETİM ---
st.markdown("---")
st.subheader("📋 All notes (Kayıt ve Hata Tablosu)")
records = load_records()

if records:
    for record in records:
        col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 1, 1])
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
            if st.button("✏️ Düzenle", key=f"edit_{record.get('id', 0)}"):
                st.session_state.edit_id = record.get('id')
                st.rerun()
        with col5:
            if st.button("🗑️ Sil", key=f"del_{record.get('id', 0)}"):
                updated_records = [r for r in records if r.get('id') != record.get('id')]
                save_records(updated_records)
                if st.session_state.edit_id == record.get('id'):
                    st.session_state.edit_id = None
                st.rerun()
        st.markdown("---")
else:
    st.info("Henüz kayıt bulunmuyor. Yeni kayıt ekleyebilirsiniz.")

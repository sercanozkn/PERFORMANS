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
st.success("🟢 Kararlı Lokal Mod Aktif (Çoklu Resim ve 3 Farklı Grafik)")
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
    
    # Çoklu resim yükleme (Düzenleme)
    e_uploaded_files = st.file_uploader("Files & media (Yeni Resimler Yükle - Çoklu):", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="edit_file")
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        if st.button("💾 Değişiklikleri Kaydet", use_container_width=True):
            image_paths = editing_record.get("image_paths", [])
            image_path = editing_record.get("image_path")
            has_img = editing_record.get("has_image", False)
            
            if e_uploaded_files:
                image_paths = []
                for uf in e_uploaded_files:
                    path = os.path.join(UPLOAD_DIR, uf.name)
                    with open(path, "wb") as f:
                        f.write(uf.getbuffer())
                    image_paths.append(path)
                image_path = image_paths[0] if image_paths else None
                has_img = True
                
            for r in records:
                if r.get("id") == st.session_state.edit_id:
                    r["name"] = e_name
                    r["date"] = e_date.strftime("%d/%m/%Y")
                    r["note"] = e_note
                    r["image_path"] = image_path
                    r["image_paths"] = image_paths
                    r["has_image"] = has_img
                    
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
    
    # Çoklu resim yükleme (Yeni Kayıt - accept_multiple_files=True)
    uploaded_files = st.file_uploader("Files & media (Resimler Yükle - Çoklu):", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="new_file")
    
    if st.button("Tabloya Ekle", type="primary"):
        if name and note:
            image_paths = []
            image_path = None
            has_img = False
            if uploaded_files:
                for uf in uploaded_files:
                    path = os.path.join(UPLOAD_DIR, uf.name)
                    with open(path, "wb") as f:
                        f.write(uf.getbuffer())
                    image_paths.append(path)
                image_path = image_paths[0] if image_paths else None
                has_img = True
            
            new_id = int(datetime.now().timestamp() * 1000)
            new_item = {
                "id": new_id,
                "name": name,
                "date": date.strftime("%d/%m/%Y"),
                "note": note,
                "image_path": image_path,
                "image_paths": image_paths,
                "has_image": has_img
            }
            
            records.append(new_item)
            save_records(records)
            st.success("Kayıt başarıyla eklendi!")
            st.rerun()
        else:
            st.warning("Lütfen İsim ve Not alanlarını doldurun.")

# --- 3 AYRI GRAFİK BÖLÜMÜ ---
st.markdown("---")
st.subheader("📊 İstatistik Grafikleri (Resimli, Resimsiz ve Ortalama)")

if records:
    df_chart = pd.DataFrame(records)
    
    col_g1, col_g2, col_g3 = st.columns(3)
    
    with col_g1:
        st.markdown("### 🖼️ Resimli Kayıtlar")
        df_with_img = df_chart[df_chart["has_image"] == True] if "has_image" in df_chart.columns else pd.DataFrame()
        if not df_with_img.empty and "name" in df_with_img.columns:
            img_counts = df_with_img["name"].value_counts().reset_index()
            img_counts.columns = ["İsim", "Kayıt Sayısı"]
            img_counts = img_counts.set_index("İsim")
            st.bar_chart(img_counts)
        else:
            st.info("Resimli kayıt yok.")
            
    with col_g2:
        st.markdown("### 📄 Resimsiz Kayıtlar")
        df_without_img = df_chart[df_chart["has_image"] != True] if "has_image" in df_chart.columns else df_chart
        if not df_without_img.empty and "name" in df_without_img.columns:
            no_img_counts = df_without_img["name"].value_counts().reset_index()
            no_img_counts.columns = ["İsim", "Kayıt Sayısı"]
            no_img_counts = no_img_counts.set_index("İsim")
            st.bar_chart(no_img_counts)
        else:
            st.info("Resimsiz kayıt yok.")
            
    with col_g3:
        st.markdown("### 📈 Ortalama / Genel Dağılım")
        if "name" in df_chart.columns and not df_chart.empty:
            # İsim bazlı ortalama veya genel toplam dağılımı
            avg_counts = df_chart["name"].value_counts().reset_index()
            avg_counts.columns = ["İsim", "Ortalama/Toplam"]
            # Ortalama değer hesabı (örnek olarak toplam sayı / toplam benzersiz isim veya doğrudan oran)
            avg_counts["Ortalama/Toplam"] = avg_counts["Ortalama/Toplam"] / len(avg_counts) if len(avg_counts) > 0 else avg_counts["Ortalama/Toplam"]
            avg_counts = avg_counts.set_index("İsim")
            st.bar_chart(avg_counts)
        else:
            st.info("Veri bulunmuyor.")
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
            # Çoklu resimleri veya tek resmi göster
            img_paths = record.get('image_paths', [])
            if not img_paths and record.get('image_path'):
                img_paths = [record.get('image_path')]
                
            valid_imgs = [p for p in img_paths if os.path.exists(p)]
            if valid_imgs:
                img_cols = st.columns(len(valid_imgs))
                for idx, img_p in enumerate(valid_imgs):
                    with img_cols[idx]:
                        st.image(img_p, width=40)
            else:
                st.write("-")
        with col4:
            if st.button("✏️ Düzenle", key=f"edit_{record.get('id', 0)}"):
                st.session_state.edit_id = record.get('id')
                st.rerun()
        with col5:
            if st.button("🗑️ Sil", key=f"del_{record.get('id', 0)}"):
                updated_records = [r for r in records if r.get('id'] != record.get('id')]
                save_records(updated_records)
                if st.session_state.edit_id == record.get('id'):
                    st.session_state.edit_id = None
                st.rerun()
        st.markdown("---")
else:
    st.info("Henüz kayıt bulunmuyor. Yeni kayıt ekleyebilirsiniz.")

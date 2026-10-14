import streamlit as st
import os
import pandas as pd
from collections import Counter
import json
import urllib.request
import urllib.parse

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Hata Yönetim Sistemi", layout="wide")

# --- GOOGLE SHEETS WEB APP / PUBLIC CSV SENKRONİZASYONU ---
# Tablonuzu Google Sheets'ten "CSV olarak yayınla" (Publish to web -> CSV) yaparak 
# alacağınız bağlantıyı buradaki GOOGLE_SHEET_CSV_URL değişkenine yapıştırın.
# (Alternatif olarak GitHub üzerinden kalıcı JSON tutmak yerine bu en kararlı yöntemdir).
GOOGLE_SHEET_CSV_URL = st.secrets.get("GOOGLE_SHEET_CSV_URL", "")

def load_records_from_cloud():
    if not GOOGLE_SHEET_CSV_URL:
        # Eğer link henüz eklenmediyse boş döner
        return []
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        records = []
        for _, row in df.iterrows():
            img_paths = json.loads(str(row["image_paths"])) if pd.notna(row["image_paths"]) else []
            records.append({
                "name": str(row["name"]),
                "date": str(row["date"]),
                "note": str(row["note"]),
                "image_path": img_paths[0] if img_paths else None,
                "image_paths": img_paths,
                "has_image": len(img_paths) > 0
            })
        return records
    except Exception as e:
        return []

# --- OTURUM (SESSION STATE) BAŞLANGIÇ DEĞERLERİ ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "username" not in st.session_state:
    st.session_state.username = "admin"

if "password" not in st.session_state:
    st.session_state.password = "1234"

# Kayıtları buluttan yüklüyoruz
if "records" not in st.session_state:
    st.session_state.records = load_records_from_cloud()

if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

if "zoomed_image" not in st.session_state:
    st.session_state.zoomed_image = None

# --- KULLANICI GİRİŞ FONKSİYONU ---
def check_password():
    if not st.session_state.authenticated:
        st.title("🔒 Giriş Yap")
        st.write("Lütfen devam etmek için kullanıcı adı ve şifrenizi girin.")

        with st.form("login_form"):
            username = st.text_input("Kullanıcı Adı:")
            password = st.text_input("Şifre:", type="password")
            submit = st.form_submit_button("Giriş Yap")
            if submit:
                if username == st.session_state.username and password == st.session_state.password:
                    st.session_state.authenticated = True
                    st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı!")
        return False
    return True

if not check_password():
    st.stop()

# --- ANA UYGULAMA ---
UPLOAD_DIR = "uploaded_images"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

st.title("📄 Notes - Hata Takip Paneli (Bulut Senkronize)")
st.markdown("---")

# Eğer Google Sheets bağlantı linki girilmediyse uyarı ver
if not GOOGLE_SHEET_CSV_URL:
    st.warning("⚠️ Verilerin telefonda ve bilgisayarda ortak görünmesi için lütfen Streamlit Secrets bölümüne `GOOGLE_SHEET_CSV_URL` adresinizi ekleyin.")

# --- KULLANICI AYARLARI ---
with st.sidebar.expander("⚙️ Hesap Ayarları"):
    yeni_kullanici = st.text_input("Yeni Kullanıcı Adı", value=st.session_state.username)
    yeni_sifre = st.text_input("Yeni Şifre", type="password")
    
    if st.button("Bilgileri Güncelle"):
        st.session_state.username = yeni_kullanici
        if yeni_sifre:
            st.session_state.password = yeni_sifre
        st.success("Bilgiler güncellendi! Lütfen yeniden giriş yapın.")
        st.session_state.authenticated = False
        st.rerun()

if st.sidebar.button("Çıkış Yap"):
    st.session_state.authenticated = False
    st.rerun()

# --- BÜYÜTÜLEN RESİM ---
if st.session_state.zoomed_image:
    col_z1, col_z2 = st.columns([10, 1])
    with col_z1:
        st.markdown("### 🔍 Resim Büyük Önizleme")
    with col_z2:
        if st.button("❌ Kapat", key="close_zoom"):
            st.session_state.zoomed_image = None
            st.rerun()
            
    if os.path.exists(st.session_state.zoomed_image):
        st.image(st.session_state.zoomed_image, use_column_width=True)
    st.markdown("---")

# --- DÜZENLEME PANELİ ---
if st.session_state.edit_index is not None:
    idx = st.session_state.edit_index
    if idx < len(st.session_state.records):
        current_record = st.session_state.records[idx]
        
        st.markdown(f"### 📂 Ayrıntı ve Düzenleme Ekranı: {current_record['name']}")
        
        with st.form("open_detail_edit_form"):
            edit_name = st.text_input("Text (İsim):", value=current_record.get("name", ""))
            
            try:
                default_date = pd.to_datetime(current_record.get("date")).date()
            except:
                default_date = pd.Timestamp.today().date()
                
            edit_date = st.date_input("Date (Tarih):", value=default_date, format="DD/MM/YYYY")
            edit_note = st.text_area("Not / İçerik:", value=current_record.get("note", ""))
            
            existing_paths = current_record.get("image_paths", [])
            edit_uploaded_files = st.file_uploader("Files & media (Ekstra Yeni Resimler Ekle):", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                update_button = st.form_submit_button(label="Değişiklikleri Kaydet")
            with col_f2:
                cancel_button = st.form_submit_button(label="Kapat / Geri Dön")
                
            if update_button:
                if edit_name and edit_note:
                    image_paths = list(existing_paths)
                    if edit_uploaded_files:
                        for uf in edit_uploaded_files:
                            img_path = os.path.join(UPLOAD_DIR, uf.name)
                            with open(img_path, "wb") as f:
                                f.write(uf.getbuffer())
                            if img_path not in image_paths:
                                image_paths.append(img_path)
                    
                    st.session_state.records[idx] = {
                        "name": edit_name,
                        "date": str(edit_date),
                        "note": edit_note,
                        "image_path": image_paths[0] if image_paths else None,
                        "image_paths": image_paths,
                        "has_image": len(image_paths) > 0
                    }
                    st.session_state.edit_index = None
                    st.success("Kayıt güncellendi! (Google E-Tablonuzdan verileri senkronize edebilirsiniz).")
                    st.rerun()
                else:
                    st.warning("Lütfen İsim ve Not alanlarını boş bırakmayın.")
                    
            if cancel_button:
                st.session_state.edit_index = None
                st.rerun()
        st.markdown("---")

# --- YENİ KAYIT EKLEME FORMU ---
with st.form("entry_form", clear_on_submit=True):
    st.subheader("➕ Yeni Kayıt / Hata Ekle")
    name = st.text_input("Text (İsim):")
    date = st.date_input("Date (Tarih):", format="DD/MM/YYYY")
    note = st.text_area("Not / Açıklama:")
    uploaded_files = st.file_uploader("Files & media (Resim Yükle):", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    submit_button = st.form_submit_button(label="Tabloya Ekle")
    
    if submit_button:
        if name and note:
            image_paths = []
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    image_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                    with open(image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    image_paths.append(image_path)
            
            st.session_state.records.append({
                "name": name,
                "date": str(date),
                "note": note,
                "image_path": image_paths[0] if image_paths else None,
                "image_paths": image_paths,
                "has_image": len(image_paths) > 0
            })
            
            st.success(f"'{name}' başarıyla eklendi!")
            st.rerun()
        else:
            st.warning("Lütfen İsim ve Not alanlarını doldurun.")

# --- ANALİZ PANELİ ---
if st.session_state.records:
    st.markdown("---")
    st.subheader("📊 Hata Analizi ve Ortalama Paneli")
    
    all_names = [r["name"] for r in st.session_state.records]
    error_counts = Counter(all_names)
    df_errors = pd.DataFrame(list(error_counts.items()), columns=["İsim", "Hata Sayısı"])
    ortalama_hata = df_errors["Hata Sayısı"].mean()
    
    st.metric(label="📈 Kişi Başı Ortalama Hata (Kayıt) Sayısı", value=f"{ortalama_hata:.2f}")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("### 🔴 En Çok Hata Yapanlar")
        df_max = df_errors.sort_values(by="Hata Sayısı", ascending=False).set_index("İsim")
        st.bar_chart(df_max)
            
    with col_g2:
        st.markdown("### 🟢 En Az Hata Yapanlar")
        df_min = df_errors.sort_values(by="Hata Sayısı", ascending=True).set_index("İsim")
        st.bar_chart(df_min)

# --- TABLO GÖRÜNÜMÜ ---
st.markdown("---")
st.subheader("📋 All notes (Kayıt ve Hata Tablosu)")

if st.session_state.records:
    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([1.2, 2.5, 2.5, 1.5, 1.5])
    with header_col1: st.markdown("**İşlem (OPEN)**")
    with header_col2: st.markdown("**Files & media**")
    with header_col3: st.markdown("**Text (İsim / Not)**")
    with header_col4: st.markdown("**Date**")
    with header_col5: st.markdown("**Actions (Sil)**")
    st.markdown("---")

    for idx, record in enumerate(st.session_state.records):
        row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([1.2, 2.5, 2.5, 1.5, 1.5])
        
        with row_col1:
            if st.button("OPEN", key=f"open_{idx}"):
                st.session_state.edit_index = idx
                st.rerun()
                
        with row_col2:
            paths = record.get("image_paths", [])
            if paths:
                img_cols = st.columns(len(paths) if len(paths) <= 4 else 4)
                for p_idx, img_p in enumerate(paths):
                    if os.path.exists(img_p):
                        col_target = img_cols[p_idx % len(img_cols)]
                        with col_target:
                            st.image(img_p, width=50)
                            if st.button("🔍", key=f"zoom_{idx}_{p_idx}", help="Büyüt"):
                                st.session_state.zoomed_image = img_p
                                st.rerun()
            else:
                st.write("-")
                
        with row_col3:
            st.markdown(f"**{record['name']}**")
            st.caption(f"{record['note']}")
            
        with row_col4:
            st.write(record['date'])
            
        with row_col5:
            if st.button("🗑️ Sil", key=f"del_{idx}"):
                st.session_state.records.pop(idx)
                st.rerun()
                
        st.markdown("---")
else:
    st.info("Henüz tabloya eklenmiş kayıt bulunmuyor. Google Sheets bağlantınızı tamamlayın.")

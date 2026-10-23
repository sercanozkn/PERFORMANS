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

# --- SUPABASE VERİ VE AYAR FONKSİYONLARI ---
def load_records():
    try:
        response = supabase.table("notes_records").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Kayıtlar yüklenirken hata oluştu: {e}")
        return []

def save_record_to_db(record_data):
    try:
        supabase.table("notes_records").insert(record_data).execute()
    except Exception as e:
        st.error(f"Kayıt eklenirken hata oluştu: {e}")

def update_record_in_db(record_id, record_data):
    try:
        supabase.table("notes_records").update(record_data).eq("id", record_id).execute()
    except Exception as e:
        st.error(f"Kayıt güncellenirken hata oluştu: {e}")

def delete_record_from_db(record_id):
    try:
        supabase.table("notes_records").delete().eq("id", record_id).execute()
    except Exception as e:
        st.error(f"Kayıt silinirken hata oluştu: {e}")

def load_config():
    try:
        response = supabase.table("notes_config").select("*").execute()
        if response.data:
            config_dict = {}
            for row in response.data:
                config_dict[row.get("key")] = row.get("value")
            return config_dict
        return {"admin_password": "1234"}
    except Exception as e:
        return {"admin_password": "1234"}

def save_config_to_db(key, value):
    try:
        supabase.table("notes_config").upsert({"key": key, "value": value}).execute()
    except Exception as e:
        st.error(f"Ayar kaydedilirken hata oluştu: {e}")

# --- OTURUM (SESSION STATE) BAŞLANGIÇ DEĞERLERİ ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

if "zoomed_image" not in st.session_state:
    st.session_state.zoomed_image = None

# --- KULLANICI GİRİŞ FONKSİYONU ---
def check_password():
    config = load_config()
    admin_pass = config.get("admin_password", "1234")
    
    if not st.session_state.authenticated:
        st.title("🔒 Giriş Yap")
        st.write("Lütfen devam etmek için şifrenizi girin (Varsayılan: 1234).")

        with st.form("login_form"):
            username = st.text_input("Kullanıcı Adı:", value="admin")
            password = st.text_input("Şifre:", type="password")
            submit = st.form_submit_button("Giriş Yap")
            if submit:
                if username == "admin" and password == admin_pass:
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

# Notion Tarzı Üst Başlık
st.title("📄 Notes - Hata Takip Paneli")
st.success("🟢 Bulut Veritabanı (Supabase) Bağlantısı Aktif - Verileriniz Güvende!")
st.markdown("---")

# --- KULLANICI AYARLARI ---
config = load_config()
with st.sidebar.expander("⚙️ Hesap Ayarları"):
    yeni_sifre = st.text_input("Yeni Şifre", type="password")
    
    if st.button("Şifreyi Güncelle"):
        if yeni_sifre:
            save_config_to_db("admin_password", yeni_sifre)
            st.success("Şifre kalıcı olarak güncellendi! Yeniden giriş yapın.")
            st.session_state.authenticated = False
            st.rerun()
        else:
            st.warning("Lütfen yeni şifre girin.")

if st.sidebar.button("Çıkış Yap"):
    st.session_state.authenticated = False
    st.rerun()

# --- BÜYÜTÜLEN RESİM İÇİN X İLE KAPATMA PENCERESİ ---
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

records = load_records()

# --- OPEN BUTONUNA BASILINCA AÇILAN DETAY VE DÜZENLEME PANELİ ---
if st.session_state.edit_index is not None:
    idx = st.session_state.edit_index
    if idx < len(records):
        current_record = records[idx]
        record_id = current_record.get("id")
        
        st.markdown(f"### 📂 Ayrıntı ve Düzenleme Ekranı: {current_record.get('name', '')}")
        st.info("Bu alanda seçilen kaydı inceleyebilir ve güncelleyebilirsiniz.")
        
        with st.form("open_detail_edit_form"):
            edit_name = st.text_input("Text (İsim):", value=current_record.get("name", ""))
            
            try:
                default_date = pd.to_datetime(current_record.get("date")).date()
            except:
                default_date = pd.Timestamp.today().date()
                
            edit_date = st.date_input("Date (Tarih):", value=default_date, format="DD/MM/YYYY")
            edit_note = st.text_area("Not / İçerik:", value=current_record.get("note", ""))
            
            existing_paths = current_record.get("image_paths", [])
            if not existing_paths and current_record.get("image_path"):
                existing_paths = [current_record["image_path"]]
                
            if existing_paths:
                st.write(f"Mevcut Yüklü Resim Sayısı: {len(existing_paths)}")
                
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
                    
                    has_img = len(image_paths) > 0
                    updated_data = {
                        "name": edit_name,
                        "date": str(edit_date),
                        "note": edit_note,
                        "image_path": image_paths[0] if image_paths else None,
                        "image_paths": image_paths,
                        "has_image": has_img
                    }
                    update_record_in_db(record_id, updated_data)
                    st.session_state.edit_index = None
                    st.success("Kayıt başarıyla bulutta güncellendi!")
                    st.rerun()
                else:
                    st.warning("Lütfen İsim ve Not alanlarını boş bırakmayın.")
                    
            if cancel_button:
                st.session_state.edit_index = None
                st.rerun()
        st.markdown("---")

# --- YENİ KAYIT (HATA) EKLEME FORMU ---
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
            has_image = False
            
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    image_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                    with open(image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    image_paths.append(image_path)
                has_image = True
            
            new_item = {
                "name": name,
                "date": str(date),
                "note": note,
                "image_path": image_paths[0] if image_paths else None,
                "image_paths": image_paths,
                "has_image": has_image
            }
            save_record_to_db(new_item)
            st.success(f"'{name}' için kayıt/hata başarıyla buluta eklendi!")
            st.rerun()
        else:
            st.warning("Lütfen İsim ve Not alanlarını doldurun.")

# --- HATA ANALİZİ VE GRAFİK PANELİ ---
records = load_records()
if records:
    st.markdown("---")
    st.subheader("📊 Hata Analizi ve Ortalama Paneli")
    
    all_names = [r.get("name", "") for r in records if r.get("name")]
    error_counts = Counter(all_names)
    if error_counts:
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

# --- NOTION TARZI TABLO VE SATIR GÖRÜNÜMÜ ---
st.markdown("---")
st.subheader("📋 All notes (Kayıt ve Hata Tablosu)")

if records:
    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([1.2, 2.5, 2.5, 1.5, 1.5])
    with header_col1:
        st.markdown("**İşlem (OPEN)**")
    with header_col2:
        st.markdown("**Files & media**")
    with header_col3:
        st.markdown("**Text (İsim / Not)**")
    with header_col4:
        st.markdown("**Date**")
    with header_col5:
        st.markdown("**Actions (Sil)**")
    st.markdown("---")

    for idx, record in enumerate(records):
        row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([1.2, 2.5, 2.5, 1.5, 1.5])
        record_id = record.get("id")
        
        with row_col1:
            if st.button("OPEN", key=f"open_{idx}"):
                st.session_state.edit_index = idx
                st.rerun()
                
        with row_col2:
            paths = record.get("image_paths", [])
            if not paths and record.get("image_path"):
                paths = [record["image_path"]]
            
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
            st.markdown(f"**{record.get('name', '')}**")
            st.caption(f"{record.get('note', '')}")
            
        with row_col4:
            st.write(record.get('date', ''))
            
        with row_col5:
            if st.button("🗑️ Sil", key=f"del_{idx}"):
                delete_record_from_db(record_id)
                st.rerun()
                
        st.markdown("---")
else:
    st.info("Henüz bulut veritabanında kayıt bulunmuyor.")

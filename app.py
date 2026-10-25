import os
import json
import pandas as pd
from datetime import datetime
import uuid
import streamlit as st
import plotly.express as px

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Kesintisiz Yönetim Sistemi", layout="wide", page_icon="📝")

# --- LOKAL VERİTABANI DOSYASI VE KLASÖRLER ---
DB_FILE = "notes_database.json"
CONFIG_FILE = "notes_config.json"
UPLOAD_DIR = "uploaded_images"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- YARDIMCI FONKSİYONLAR ---
def load_records():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
                for r in records:
                    if "image_path" in r and "image_paths" not in r:
                        r["image_paths"] = [r["image_path"]] if r["image_path"] else []
                return records
        except Exception as e:
            st.error(f"Veri yüklenirken hata oluştu: {e}")
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
        except Exception:
            return {"admin_password": "1234"}
    return {"admin_password": "1234"}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def save_images(uploaded_files):
    """Birden fazla görseli çakışmaları önleyecek şekilde benzersiz isimlerle kaydeder."""
    image_paths = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_ext = os.path.splitext(uploaded_file.name)[1]
            unique_filename = f"{uuid.uuid4().hex}_{int(datetime.now().timestamp())}{file_ext}"
            image_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            with open(image_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            image_paths.append(image_path)
    return image_paths

# --- OTURUM (SESSION) YÖNETİMİ ---
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
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                if username == "admin" and password == admin_pass:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre!")
        return False
    return True

if not check_password():
    st.stop()

# --- RESİM BÜYÜTME (MODAL / POP-UP) ---
@st.dialog("🖼️ Görsel Tam Ekran Önizleme", width="large")
def show_image_modal(img_path, title):
    st.subheader(title)
    if os.path.exists(img_path):
        st.image(img_path, use_container_width=True)
    else:
        st.error("Görsel bulunamadı.")
    if st.button("Kapat", use_container_width=True):
        st.rerun()

# --- GİRİŞ / ŞİFRE DEĞİŞTİRME SEKMESİ (SIDEBAR) ---
with st.sidebar:
    st.title("⚙️ Yönetim Paneli")
    st.success("🟢 Aktif Oturum (Admin)")
    st.markdown("---")
    
    st.subheader("🔑 Şifre Değiştir")
    with st.form("change_pass_form"):
        old_pass = st.text_input("Mevcut Şifre:", type="password")
        new_pass = st.text_input("Yeni Şifre:", type="password")
        confirm_pass = st.text_input("Yeni Şifre (Tekrar):", type="password")
        
        if st.form_submit_button("Şifreyi Güncelle"):
            config = load_config()
            if old_pass == config.get("admin_password", "1234"):
                if new_pass and new_pass == confirm_pass:
                    config["admin_password"] = new_pass
                    save_config(config)
                    st.success("Şifre başarıyla değiştirildi!")
                else:
                    st.error("Yeni şifreler uyuşmuyor veya boş bırakılamaz.")
            else:
                st.error("Mevcut şifre hatalı!")
                
    st.markdown("---")
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.edit_id = None
        st.rerun()

# --- ANA UYGULAMA ---
st.title("📄 Notes - Hata ve Kayıt Takip Paneli")
st.markdown("---")

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
    except ValueError:
        try:
            default_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            default_date = datetime.now().date()
            
    e_date = st.date_input("Date (Tarih):", value=default_date, format="DD/MM/YYYY", key="edit_date")
    e_note = st.text_area("Not / Açıklama:", value=editing_record.get("note", ""), key="edit_note")
    
    current_images = editing_record.get("image_paths", [])
    if current_images:
        st.markdown("**Mevcut Görseller:**")
        img_cols = st.columns(len(current_images) if len(current_images) <= 4 else 4)
        for idx, img_p in enumerate(current_images):
            if os.path.exists(img_p):
                with img_cols[idx % 4]:
                    st.image(img_p, width=100)
    
    e_uploaded_files = st.file_uploader("Yeni Görseller Yükle (İsteğe Bağlı - Çoklu Seçim):", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="edit_file")

    col_up1, col_up2 = st.columns(2)
    with col_up1:
        if st.button("💾 Değişiklikleri Kaydet", type="primary", use_container_width=True):
            for r in records:
                if r.get("id") == st.session_state.edit_id:
                    r["name"] = e_name
                    r["date"] = e_date.strftime("%d/%m/%Y")
                    r["note"] = e_note
                    
                    if e_uploaded_files:
                        new_img_paths = save_images(e_uploaded_files)
                        r["image_paths"] = r.get("image_paths", []) + new_img_paths
                        r["has_image"] = True
                        
            save_records(records)
            st.session_state.edit_id = None
            st.success("Kayıt başarıyla güncellendi!")
            st.rerun()
            
    with col_up2:
        if st.button("❌ İptal", use_container_width=True):
            st.session_state.edit_id = None
            st.rerun()

else:
    with st.expander("➕ Yeni Kayıt / Hata Ekle", expanded=True):
        with st.form("new_record_form", clear_on_submit=True):
            name = st.text_input("Text (İsim):")
            date = st.date_input("Date (Tarih):", format="DD/MM/YYYY")
            note = st.text_area("Not / Açıklama:")
            uploaded_files = st.file_uploader("Files & media (Resim Yükle - Çoklu Seçim):", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
            
            submitted = st.form_submit_button("Tabloya Ekle", type="primary")
            if submitted:
                if name and note:
                    image_paths = save_images(uploaded_files)
                    
                    new_id = int(datetime.now().timestamp() * 1000)
                    new_item = {
                        "id": new_id,
                        "name": name,
                        "date": date.strftime("%d/%m/%Y"),
                        "note": note,
                        "image_paths": image_paths,
                        "has_image": bool(image_paths)
                    }
                    
                    records.insert(0, new_item)
                    save_records(records)
                    st.success("Kayıt başarıyla eklendi!")
                    st.rerun()
                else:
                    st.warning("Lütfen İsim ve Not alanlarını doldurun.")

# --- PLOTLY İLE MODERN İSTATİSTİK / GRAFİK BÖLÜMÜ ---
st.markdown("---")
st.subheader("📊 İsimlere Göre Kayıt İstatistikleri")
if records:
    df_chart = pd.DataFrame(records)
    if "name" in df_chart.columns and not df_chart.empty:
        name_counts = df_chart["name"].value_counts().reset_index()
        name_counts.columns = ["İsim", "Kayıt Sayısı"]
        
        fig = px.bar(
            name_counts,
            x="İsim",
            y="Kayıt Sayısı",
            color="Kayıt Sayısı",
            color_continuous_scale="Plasma",
            text="Kayıt Sayısı",
            template="plotly_dark"
        )
        
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            xaxis_title="İsimler",
            yaxis_title="Kayıt Sayısı",
            coloraxis_showscale=False
        )
        
        fig.update_traces(textposition='outside')
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Grafik için yeterli veri bulunmuyor.")
else:
    st.info("Henüz istatistik oluşturulacak kayıt yok.")

# --- TABLO VE YÖNETİM ---
st.markdown("---")
col_header, col_export = st.columns([4, 2])
with col_header:
    st.subheader("📋 All notes (Kayıt ve Hata Tablosu)")

# --- EXCEL / CSV DIŞA AKTARMA ---
if records:
    df_download = pd.DataFrame(records)[["name", "date", "note"]]
    df_download.columns = ["İsim", "Tarih", "Not / Açıklama"]
    csv_data = df_download.to_csv(index=False, encoding='utf-8-sig')
    with col_export:
        st.download_button(
            label="📥 Excel/CSV Olarak İndir",
            data=csv_data,
            file_name=f"notlar_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# --- ARAMA VE FİLTRELEME ---
search_query = st.text_input("🔍 Kayıtlarda Arama Yap (İsim veya Not):", "").strip().lower()

filtered_records = records
if search_query:
    filtered_records = [
        r for r in records
        if search_query in r.get("name", "").lower() or search_query in r.get("note", "").lower()
    ]

# --- SAYFALAMASYON (PAGINATION) / PERFORMANS ---
if filtered_records:
    col_p1, col_p2 = st.columns([2, 4])
    with col_p1:
        items_per_page = st.selectbox("Sayfa Başına Kayıt:", [5, 10, 20, 50], index=0)
    
    total_items = len(filtered_records)
    total_pages = (total_items - 1) // items_per_page + 1 if total_items > 0 else 1
    
    with col_p2:
        if total_pages > 1:
            page_number = st.number_input("Sayfa Seç:", min_value=1, max_value=total_pages, value=1, step=1)
        else:
            page_number = 1
            
    start_idx = (page_number - 1) * items_per_page
    end_idx = start_idx + items_per_page
    paginated_records = filtered_records[start_idx:end_idx]

    st.markdown(f"*Toplam **{total_items}** kayıttan **{start_idx+1} - {min(end_idx, total_items)}** arası gösteriliyor. (Sayfa {page_number}/{total_pages})*")
    st.markdown("---")

    h1, h2, h3, h4, h5 = st.columns([2, 3, 2, 1, 1])
    h1.markdown("**İsim & Not**")
    h2.markdown("**Tarih**")
    h3.markdown("**Görsel**")
    h4.markdown("**İşlem**")
    h5.markdown("**İşlem**")
    st.markdown("---")

    for record in paginated_records:
        col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 1, 1])
        with col1:
            st.markdown(f"**{record.get('name', '')}**")
            st.caption(f"{record.get('note', '')}")
        with col2:
            st.write(record.get('date', ''))
        with col3:
            img_paths = record.get('image_paths', [])
            if img_paths:
                for idx, img_p in enumerate(img_paths):
                    if os.path.exists(img_p):
                        if st.button(f"🔍 Büyüt {idx+1}", key=f"zoom_{record.get('id', 0)}_{idx}"):
                            show_image_modal(img_p, f"{record.get('name')} - Görsel {idx+1}")
                        st.image(img_p, width=50)
            else:
                st.write("-")
        with col4:
            if st.button("✏️ Düzenle", key=f"edit_{record.get('id', 0)}"):
                st.session_state.edit_id = record.get('id')
                st.rerun()
        with col5:
            if st.button("🗑️ Sil", key=f"del_{record.get('id', 0)}"):
                imgs_to_delete = record.get('image_paths', [])
                for img_to_delete in imgs_to_delete:
                    if img_to_delete and os.path.exists(img_to_delete):
                        try: os.remove(img_to_delete)
                        except: pass

                records = [r for r in records if r.get('id') != record.get('id')]
                save_records(records)
                if st.session_state.edit_id == record.get('id'):
                    st.session_state.edit_id = None
                st.rerun()
        st.markdown("---")
else:
    st.info("Aramanıza uygun veya henüz eklenmiş bir kayıt bulunmuyor.")

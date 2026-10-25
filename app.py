import os
import json
import pandas as pd
from datetime import datetime
import uuid
import streamlit as st
import plotly.express as px
from supabase import create_client, Client

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Kesintisiz Yönetim Sistemi", layout="wide", page_icon="📝")

# --- SUPABASE BAĞLANTISI ---
@st.cache_resource
def init_supabase() -> Client:
    url = "".join(str(st.secrets.get("SUPABASE_URL", "")).split()).strip('"')
    key = "".join(str(st.secrets.get("SUPABASE_KEY", "")).split()).strip('"').strip("'")
    
    if not url.startswith("http"):
        url = "https://" + url
        
    if not url or not key:
        st.error("Supabase URL veya API Anahtarı Secrets alanında bulunamadı!")
        st.stop()
    return create_client(url, key)

supabase = init_supabase()

CONFIG_FILE = "notes_config.json"
BUCKET_NAME = "notes-media"

# --- YARDIMCI FONKSİYONLAR (SUPABASE TABLO & STORAGE) ---
def load_records():
    try:
        response = supabase.table("notes_records").select("*").order("id", desc=True).execute()
        records = response.data if response.data else []
        for r in records:
            if "image_path" in r and "image_paths" not in r:
                r["image_paths"] = [r["image_path"]] if r["image_path"] else []
            # Eski yerel yolları filtrele (hata vermemesi için sadece http ile başlayan URL'leri alıyoruz)
            if "image_paths" in r and isinstance(r["image_paths"], list):
                r["image_paths"] = [p for p in r["image_paths"] if p and str(p).startswith("http")]
        return records
    except Exception as e:
        st.error(f"Veriler yüklenirken hata oluştu: {e}")
        return []

def save_record_db(new_item):
    try:
        supabase.table("notes_records").insert(new_item).execute()
        return True
    except Exception as e:
        st.error(f"Kayıt eklenirken hata: {e}")
        return False

def update_record_db(record_id, data):
    try:
        supabase.table("notes_records").update(data).eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Kayıt güncellenirken hata: {e}")
        return False

def delete_record_db(record_id):
    try:
        supabase.table("notes_records").delete().eq("id", record_id).execute()
        return True
    except Exception as e:
        st.error(f"Kayıt silinirken hata: {e}")
        return False

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
    """Birden fazla görseli Supabase Storage (notes-media) alanına yükler ve halka açık URL'lerini döndürür."""
    image_urls = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_ext = os.path.splitext(uploaded_file.name)[1]
            unique_filename = f"{uuid.uuid4().hex}_{int(datetime.now().timestamp())}{file_ext}"
            try:
                file_bytes = uploaded_file.getvalue()
                supabase.storage.from_(BUCKET_NAME).upload(
                    path=unique_filename,
                    file=file_bytes,
                    file_options={"content-type": uploaded_file.type}
                )
                res = supabase.storage.from_(BUCKET_NAME).get_public_url(unique_filename)
                if isinstance(res, dict):
                    public_url = res.get("publicUrl") or res.get("publicURL", "")
                else:
                    public_url = str(res)
                if public_url:
                    image_urls.append(public_url)
            except Exception as e:
                st.error(f"Görsel buluta yüklenirken hata: {e}")
    return image_urls

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
def show_image_modal(img_url, title):
    st.subheader(title)
    st.image(img_url, use_container_width=True)
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
    keep_images = []
    if current_images:
        st.markdown("**Mevcut Görseller (Korumak istediklerinizi seçin):**")
        img_cols = st.columns(len(current_images) if len(current_images) <= 4 else 4)
        for idx, img_url in enumerate(current_images):
            with img_cols[idx % 4]:
                st.image(img_url, width=100)
                if st.checkbox(f"Koru #{idx+1}", value=True, key=f"keep_{editing_record.get('id')}_{idx}"):
                    keep_images.append(img_url)
    
    e_uploaded_files = st.file_uploader("Yeni Görseller Yükle (İsteğe Bağlı - Çoklu Seçim):", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="edit_file")

    col_up1, col_up2 = st.columns(2)
    with col_up1:
        if st.button("💾 Değişiklikleri Kaydet", type="primary", use_container_width=True):
            final_img_paths = keep_images
            if e_uploaded_files:
                new_img_urls = save_images(e_uploaded_files)
                final_img_paths.extend(new_img_urls)
            
            update_data = {
                "name": e_name,
                "date": e_date.strftime("%d/%m/%Y"),
                "note": e_note,
                "image_paths": final_img_paths,
                "has_image": bool(final_img_paths)
            }
            if update_record_db(st.session_state.edit_id, update_data):
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

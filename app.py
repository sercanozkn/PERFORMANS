import os
import json
from datetime import datetime
import uuid
import streamlit as st
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
    return create_client(url, key)

supabase = init_supabase()
BUCKET_NAME = "notes-media"

# --- VERİLERİ YÜKLEME ---
def load_records():
    try:
        response = supabase.table("notes_records").select("*").order("id", desc=True).execute()
        records = response.data if response and response.data else []
        
        for r in records:
            paths = []
            raw_paths = r.get("image_paths", [])
            if not raw_paths and r.get("image_path"):
                raw_paths = [r.get("image_path")]
            if isinstance(raw_paths, str):
                raw_paths = [raw_paths]
            
            for p in raw_paths:
                if p:
                    p_str = str(p).strip()
                    if p_str.startswith("http"):
                        paths.append(p_str)
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
                
                # Supabase Storage'a yükleme
                supabase.storage.from_(BUCKET_NAME).upload(
                    path=unique_filename,
                    file=file_bytes,
                    file_options={"content-type": uploaded_file.type}
                )
                
                # Public URL alma
                public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(unique_filename)
                
                if isinstance(public_url, dict):
                    url_val = public_url.get("publicUrl") or public_url.get("public_url")
                    if url_val:
                        image_paths.append(url_val)
                elif isinstance(public_url, str):
                    image_paths.append(public_url)
            except Exception as e:
                st.error(f"Resim yüklenirken hata oluştu: {e}")
    return image_paths

# --- ARAYÜZ ---
st.title("📝 Notes - Hata ve Kayıt Takip Paneli")

records = load_records()

# --- YENİ KAYIT FORMU ---
with st.expander("➕ Yeni Kayıt / Hata Ekle"):
    with st.form("add_form", clear_on_submit=True):
        new_name = st.text_input("İsim / Başlık:")
        new_date = st.text_input("Tarih:", value=datetime.now().strftime("%d/%m/%Y"))
        new_note = st.text_area("Not / Açıklama:")
        new_images = st.file_uploader("Görsel Yükle (Çoklu Seçim):", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        submit_btn = st.form_submit_button("Tabloya Ekle")
        if submit_btn:
            uploaded_urls = save_images(new_images)
            st.write("Oluşan Resim Linkleri:", uploaded_urls) # Debug için linkleri gösteriyoruz
            
            max_id = max([r.get("id", 0) for r in records], default=0) if records else 0
            
            new_record = {
                "id": max_id + 1,
                "name": new_name,
                "date": new_date,
                "note": new_note,
                "image_paths": uploaded_urls
            }
            try:
                supabase.table("notes_records").insert(new_record).execute()
                st.success("Kayıt ve görseller başarıyla eklendi!")
                st.rerun()
            except Exception as e:
                st.error(f"Kayıt eklenirken hata oluştu: {e}")

# --- LİSTELEME VE ARAMA ---
search_query = st.text_input("🔍 Kayıtlarda Arama Yap:")

filtered_records = records
if search_query:
    filtered_records = [
        r for r in records 
        if search_query.lower() in str(r.get("name", "")).lower() or search_query.lower() in str(r.get("note", "")).lower()
    ]

if filtered_records:
    st.write(f"Toplam {len(filtered_records)} kayıt gösteriliyor.")
    
    col_h1, col_h2, col_h3, col_h4 = st.columns([2, 1, 1, 1])
    col_h1.markdown("**İsim & Not**")
    col_h2.markdown("**Tarih**")
    col_h3.markdown("**Görsel**")
    col_h4.markdown("**İşlem**")
    st.markdown("---")

    for r in filtered_records:
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            name_val = r.get('name', '') or r.get('text', 'İsimsiz')
            st.markdown(f"**{name_val}**")
            st.caption(r.get('note', ''))
            
        with col2:
            st.write(r.get('date', ''))
            
        with col3:
            imgs = r.get("image_paths", [])
            valid_imgs = [img for img in imgs if img and str(img).startswith("http")]
            if valid_imgs:
                for img_url in valid_imgs:
                    try:
                        st.image(img_url, width=45)
                    except Exception as e:
                        st.write(f"Hata: {e}")
            else:
                st.text("-")
                    
        with col4:
            if st.button("Sil", key=f"del_{r.get('id', 0)}"):
                try:
                    supabase.table("notes_records").delete().eq("id", r.get('id')).execute()
                    st.success("Kayıt silindi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Silinirken hata oluştu: {e}")
                
        st.markdown("---")
else:
    st.info("Kayıt bulunmuyor.")

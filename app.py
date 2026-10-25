import os
import json
import pandas as pd
from datetime import datetime
import uuid
import streamlit as st
import plotly.express as px
from supabase import create_client, Client

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Kesintisiz Yönetim Sistemi", layout="wide", page_icon="📋")

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
UPLOAD_DIR = "uploaded_images"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- SUPABASE VERİTABANI FONKSİYONLARI ---
def load_records():
    try:
        response = supabase.table("notes_records").select("*").order("id", desc=True).execute()
        records = response.data if response.data else []
        for r in records:
            if "image_path" in r and "image_paths" not in r:
                r["image_paths"] = [r["image_path"]] if r["image_path"] else []
        return records
    except Exception as e:
        st.error(f"Veriler yüklenirken hata oluştu: {e}")
        return []

def save_record_db(name, date_str, note, image_paths):
    try:
        data = {
            "name": name,
            "date": date_str,
            "note": note,
            "image_paths": image_paths
        }
        supabase.table("notes_records").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Kayıt eklenirken hata: {e}")
        return False

def update_record_db(record_id, name, date_str, note, image_paths):
    try:
        data = {
            "name": name,
            "date": date_str,
            "note": note,
            "image_paths": image_paths
        }
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

# --- KİMLİK DOĞRULAMA (ŞİFRE) ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"password": "admin"}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

config = load_config()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

# --- YÖNETİM PANELİ (KENAR ÇUBUĞU) ---
with st.sidebar:
    st.header("⚙️ Yönetim Paneli")
    if st.session_state.authenticated:
        st.success("🟢 Aktif Oturum (Admin)")
        st.markdown("---")
        st.subheader("🔑 Şifre Değiştir")
        current_pw = st.text_input("Mevcut Şifre", type="password", key="curr_pw")
        new_pw = st.text_input("Yeni Şifre", type="password", key="new_pw")
        new_pw_conf = st.text_input("Yeni Şifre (Tekrar)", type="password", key="new_pw_conf")
        
        if st.button("Şifreyi Güncelle"):
            if current_pw == config.get("password", "admin"):
                if new_pw and new_pw == new_pw_conf:
                    config["password"] = new_pw
                    save_config(config)
                    st.success("Şifreniz başarıyla değiştirildi!")
                else:
                    st.error("Yeni şifreler eşleşmiyor veya boş.")
            else:
                st.error("Mevcut şifre yanlış!")
                
        st.markdown("---")
        if st.button("🚪 Çıkış Yap"):
            st.session_state.authenticated = False
            st.rerun()
    else:
        st.warning("🔒 Oturum Kapalı")
        login_pw = st.text_input("Yönetici Şifresi", type="password", key="login_pw_input")
        if st.button("Giriş Yap"):
            if login_pw == config.get("password", "admin"):
                st.session_state.authenticated = True
                st.success("Giriş başarılı!")
                st.rerun()
            else:
                st.error("Hatalı şifre!")

# --- ANA EKRAN ---
st.title("📋 Notes - Hata ve Kayıt Takip Paneli")
st.markdown("---")

# Modal / Görsel Büyütme Fonksiyonu
@st.dialog("🔍 Görsel Önizleme")
def show_image_modal(img_path, caption):
    if os.path.exists(img_path) and os.path.isfile(img_path):
        st.image(img_path, caption=caption, use_column_width=True)
    else:
        st.error("Görsel dosyası bulunamadı veya silinmiş.")

# --- YENİ KAYIT / DÜZENLEME FORMU ---
edit_record = None
if st.session_state.edit_id is not None:
    all_recs = load_records()
    for r in all_recs:
        if r.get("id") == st.session_state.edit_id:
            edit_record = r
            break

with st.expander("➕ Yeni Kayıt / Hata Ekle" if not edit_record else "✏️ Kaydı Düzenle", expanded=True if edit_record else False):
    with st.form("record_form", clear_on_submit=False if edit_record else True):
        default_name = edit_record.get("name", "") if edit_record else ""
        default_date = datetime.strptime(edit_record.get("date"), "%d/%m/%Y").date() if edit_record and edit_record.get("date") else datetime.today()
        default_note = edit_record.get("note", "") if edit_record else ""
        default_images = edit_record.get("image_paths", []) if edit_record else []

        f_name = st.text_input("Text (İsim):", value=default_name)
        f_date = st.date_input("Date (Tarih):", value=default_date)
        f_note = st.text_area("Not / Açıklama:", value=default_note)
        
        f_files = st.file_uploader("Files & media (Resim Yükle - Çoklu Seçim):", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        if edit_record and default_images:
            st.markdown("**Mevcut Yüklü Görseller:**")
            cols_prev = st.columns(min(len(default_images), 4))
            keep_images = []
            for idx, img_p in enumerate(default_images):
                if os.path.exists(img_p) and os.path.isfile(img_p):
                    with cols_prev[idx % 4]:
                        st.image(img_p, width=70)
                        if st.checkbox(f"Koru #{idx+1}", value=True, key=f"keep_{edit_record.get('id')}_{idx}"):
                            keep_images.append(img_p)
                else:
                    if os.path.exists(img_p):
                        try:
                            os.remove(img_p)
                        except:
                            pass

        submit_label = "Güncelle" if edit_record else "Tabloya Ekle"
        submitted = st.form_submit_button(submit_label)
        
        if submitted:
            if not f_name.strip():
                st.error("Lütfen 'Text (İsim)' alanını boş bırakmayın.")
            else:

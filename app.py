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
BUCKET_NAME = "notes-media"

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

# --- SUPABASE STORAGE GÖRSEL YÜKLEME ---
def upload_images_to_supabase(uploaded_files):
    image_urls = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_ext = os.path.splitext(uploaded_file.name)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
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
def show_image_modal(img_url, caption):
    st.image(img_url, caption=caption, use_column_width=True)

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
        
        keep_images = []
        if edit_record and default_images:
            st.markdown("**Mevcut Yüklü Görseller:**")
            cols_prev = st.columns(min(len(default_images), 4))
            for idx, img_url in enumerate(default_images):
                with cols_prev[idx % 4]:
                    st.image(img_url, width=70)
                    if st.checkbox(f"Koru #{idx+1}", value=True, key=f"keep_{edit_record.get('id')}_{idx}"):
                        keep_images.append(img_url)

        submit_label = "Güncelle" if edit_record else "Tabloya Ekle"
        submitted = st.form_submit_button(submit_label)
        
        if submitted:
            if not f_name.strip():
                st.error("Lütfen 'Text (İsim)' alanını boş bırakmayın.")
            else:
                date_str = f_date.strftime("%d/%m/%Y")
                final_image_paths = keep_images if edit_record else []
                
                if f_files:
                    new_uploaded_urls = upload_images_to_supabase(f_files)
                    final_image_paths.extend(new_uploaded_urls)
                
                if edit_record:
                    if update_record_db(edit_record.get("id"), f_name, date_str, f_note, final_image_paths):
                        st.success("Kayıt başarıyla güncellendi!")
                        st.session_state.edit_id = None
                        st.rerun()
                else:
                    if save_record_db(f_name, date_str, f_note, final_image_paths):
                        st.success("Kayıt başarıyla eklendi!")
                        st.rerun()

        if edit_record:
            if st.form_submit_button("İptal Et"):
                st.session_state.edit_id = None
                st.rerun()

st.markdown("---")

# --- ARAMA VE FİLTRELEME ---
records = load_records()

col_s1, col_s2 = st.columns([2, 1])
with col_s1:
    search_query = st.text_input("🔍 Kayıtlarda Ara (İsim veya Not):", "")
with col_s2:
    sort_order = st.selectbox("Sıralama:", ["Yeniden Eskiye", "Eskiden Yeniye"])

filtered_records = []
for r in records:
    if search_query.lower() in r.get("name", "").lower() or search_query.lower() in r.get("note", "").lower():
        filtered_records.append(r)

if sort_order == "Eskiden Yeniye":
    filtered_records = sorted(filtered_records, key=lambda x: x.get("id", 0))

# --- SAYFALAMA ---
items_per_page = st.selectbox("Sayfa Başına Kayıt:", [5, 10, 20, 50], index=0)
total_records = len(filtered_records)
total_pages = (total_records // items_per_page) + (1 if total_records % items_per_page > 0 else 0)
total_pages = max(total_pages, 1)

page_num = st.number_input("Sayfa", min_value=1, max_value=total_pages, step=1, value=1)
start_idx = (page_num - 1) * items_per_page
end_idx = start_idx + items_per_page
paginated_records = filtered_records[start_idx:end_idx]

st.markdown(f"Toplam **{total_records}** kayıttan **{start_idx+1} - {min(end_idx, total_records)}** arası gösteriliyor. (Sayfa {page_num}/{total_pages})")
st.markdown("---")

# --- TABLO BAŞLIKLARI ---
if paginated_records:
    h1, h2, h3, h4, h5 = st.columns([2, 3, 2, 1, 1])
    with h1:
        st.markdown("**İsim & Not**")
    with h2:
        st.markdown("**Tarih**")
    with h3:
        st.markdown("**Görsel**")
    with h4:
        st.markdown("**İşlem**")
    with h5:
        st.markdown("**İşlem**")
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
                for i in range(0, len(img_paths), 3):
                    row_imgs = img_paths[i:i+3]
                    thumb_cols = st.columns(len(row_imgs))
                    for sub_idx, img_url in enumerate(row_imgs):
                        global_idx = i + sub_idx
                        with thumb_cols[sub_idx]:
                            st.image(img_url, width=45)
                            if st.button("🔍", key=f"zoom_{record.get('id', 0)}_{global_idx}", help=f"Görsel {global_idx+1} Büyüt"):
                                show_image_modal(img_url, f"{record.get('name')} - Görsel {global_idx+1}")
            else:
                st.write("-")
        with col4:
            if st.button("✏️ Düzenle", key=f"edit_{record.get('id', 0)}"):
                st.session_state.edit_id = record.get('id')
                st.rerun()
        with col5:
            if st.button("🗑️ Sil", key=f"del_{record.get('id', 0)}"):
                if delete_record_db(record.get('id')):
                    if st.session_state.edit_id == record.get('id'):
                        st.session_state.edit_id = None
                    st.success("Kayıt veritabanından silindi.")
                    st.rerun()
        st.markdown("---")
else:
    st.info("Aramanıza uygun veya henüz eklenmiş bir kayıt bulunmuyor.")

# --- İSTATİSTİKLER VE GRAFİKLER ---
if records:
    st.markdown("---")
    st.subheader("📊 İstatistikler ve Grafikler")
    
    df = pd.DataFrame(records)
    if "date" in df.columns and not df.empty:
        date_counts = df["date"].value_counts().reset_index()
        date_counts.columns = ["Tarih", "Kayıt Sayısı"]
        date_counts = date_counts.sort_values("Tarih")
        
        fig = px.bar(date_counts, x="Tarih", y="Kayıt Sayısı", title="Günlük Kayıt Dağılımı", text="Kayıt Sayısı")
        st.plotly_chart(fig, use_container_width=True)

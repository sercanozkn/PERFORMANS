import os
import json
from datetime import datetime
import uuid
import streamlit as st
import plotly.express as px
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
    return create_client(url, key), url

supabase, SUPABASE_URL = init_supabase()
BUCKET_NAME = "notes-media"

# --- OTURUM & KULLANICI YÖNETİMİ ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# Varsayılan kimlik bilgilerini session state üzerinde tutma (Ayarlar sekmesinden güncellenebilmesi için)
if "username" not in st.session_state:
    st.session_state["username"] = st.secrets.get("APP_USERNAME", "admin")
if "password" not in st.session_state:
    st.session_state["password"] = st.secrets.get("APP_PASSWORD", "1234")

if not st.session_state["logged_in"]:
    st.title("🔐 Notes - Kullanıcı Girişi")
    with st.form("login_form"):
        username_input = st.text_input("Kullanıcı Adı:")
        password_input = st.text_input("Şifre:", type="password")
        login_btn = st.form_submit_button("Giriş Yap")
        
        if login_btn:
            if username_input == st.session_state["username"] and password_input == st.session_state["password"]:
                st.session_state["logged_in"] = True
                st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")
    st.stop()  # Giriş yapılmadıysa uygulamanın devamını çalıştırma

# --- VERİLERİ YÜKLEME ---
def load_records():
    try:
        response = supabase.table("notes_records").select("*").order("id", desc=True).execute()
        records = response.data if response and response.data else []
        
        for r in records:
            paths = []
            raw_paths = r.get("image_paths", [])
            
            if isinstance(raw_paths, str):
                try:
                    raw_paths = json.loads(raw_paths.replace("'", '"'))
                except Exception:
                    raw_paths = [raw_paths]
            
            if not isinstance(raw_paths, list):
                raw_paths = [raw_paths]
            
            for p in raw_paths:
                if p:
                    p_str = str(p).strip("[]'\" ")
                    if p_str.startswith("http"):
                        for sub_p in p_str.split("https://"):
                            if sub_p.strip():
                                clean_url = "https://" + sub_p.strip("[]'\" ,")
                                if clean_url not in paths:
                                    paths.append(clean_url)
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
                
                supabase.storage.from_(BUCKET_NAME).upload(
                    path=unique_filename,
                    file=file_bytes,
                    file_options={"content-type": uploaded_file.type}
                )
                
                clean_base_url = SUPABASE_URL.rstrip('/')
                public_url = f"{clean_base_url}/storage/v1/object/public/{BUCKET_NAME}/{unique_filename}"
                image_paths.append(public_url)
            except Exception as e:
                st.error(f"Resim ({uploaded_file.name}) yüklenirken hata oluştu: {e}")
    return image_paths

# --- SOL MENÜ / YÖNETİM PANELİ ---
st.sidebar.title("🛠️ Yönetim Paneli")

# 1. Yeni Kayıt Ekleme Bölümü
with st.sidebar.expander("➕ Yeni Kayıt / Hata Ekle", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        new_name = st.text_input("İsim / Başlık:")
        new_date = st.text_input("Tarih:", value=datetime.now().strftime("%d/%m/%Y"))
        new_note = st.text_area("Not / Açıklama:")
        new_images = st.file_uploader("Görsel Yükle (Çoklu Seçim):", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        submit_btn = st.form_submit_button("Tabloya Ekle")
        if submit_btn:
            if not new_name.strip():
                st.warning("Lütfen bir isim/başlık girin.")
            else:
                uploaded_urls = save_images(new_images)
                
                # 'id' alanını kaldırarak ekleme yapıyoruz; Supabase auto-increment ID üretsin.
                new_record = {
                    "name": new_name,
                    "date": new_date,
                    "note": new_note,
                    "image_paths": uploaded_urls
                }
                try:
                    supabase.table("notes_records").insert(new_record).execute()
                    st.success("Kayıt başarıyla eklendi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kayıt eklenirken hata oluştu: {e}")

# 2. Ayarlar Sekmesi (Şifre & Kullanıcı Adı Güncelleme)
with st.sidebar.expander("⚙️ Ayarlar", expanded=False):
    with st.form("settings_form"):
        st.write("**Kullanıcı Bilgileri Değiştir**")
        current_user_check = st.text_input("Mevcut Kullanıcı Adı:")
        new_username = st.text_input("Yeni Kullanıcı Adı:")
        
        st.write("**Şifre Değiştir**")
        current_password = st.text_input("Mevcut Şifre:", type="password")
        new_password = st.text_input("Yeni Şifre:", type="password")
        confirm_password = st.text_input("Yeni Şifre (Tekrar):", type="password")
        
        settings_submit = st.form_submit_button("Değişiklikleri Kaydet")
        if settings_submit:
            # Doğrulama Kontrolleri
            if current_user_check != st.session_state["username"] or current_password != st.session_state["password"]:
                st.error("Mevcut kullanıcı adı veya şifre yanlış!")
            elif new_password and new_password != confirm_password:
                st.error("Yeni şifreler birbiriyle uyuşmuyor!")
            else:
                if new_username.strip():
                    st.session_state["username"] = new_username.strip()
                if new_password.strip():
                    st.session_state["password"] = new_password.strip()
                st.success("Ayarlar başarıyla güncellendi!")

st.sidebar.markdown("---")

# 3. Çıkış Yap Butonu
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state["logged_in"] = False
    st.rerun()

# --- ANA EKRAN ---
st.title("📝 Notes - Hata ve Kayıt Takip Paneli")

records = load_records()

# --- İSTATİSTİKLER VE GRAFİKLER ---
if records:
    st.subheader("📊 İstatistikler ve Grafikler")
    col_g1, col_g2 = st.columns(2)
    
    name_counts = {}
    detailed_data = []
    
    for r in records:
        name_val = str(r.get("name", "") or r.get("text", "İsimsiz")).strip()
        if not name_val:
            name_val = "İsimsiz"
            
        name_counts[name_val] = name_counts.get(name_val, 0) + 1
        
        imgs = r.get("image_paths", [])
        valid_imgs = [img for img in imgs if img and str(img).startswith("http")]
        has_image = "Resimli Kayıt" if valid_imgs else "Resimsiz Kayıt"
        
        detailed_data.append({"İsimler": name_val, "Durum": has_image})
    
    chart_data1 = [{"İsimler": k, "Kayıt Sayısı": v} for k, v in name_counts.items()]
    
    with col_g1:
        fig1 = px.bar(
            chart_data1, 
            x="İsimler", 
            y="Kayıt Sayısı", 
            title="👤 İsimlere Göre Toplam Kayıt İstatistikleri",
            text="Kayıt Sayısı"
        )
        fig1.update_traces(textposition='outside')
        fig1.update_layout(xaxis_title="İsimler", yaxis_title="Kayıt Sayısı", margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig1, use_container_width=True)
        
    with col_g2:
        fig2 = px.histogram(
            detailed_data,
            x="İsimler",
            color="Durum",
            barmode="group",
            title="📈 İsimlere Göre Resimli / Resimsiz Detaylı Dağılım",
            color_discrete_map={"Resimli Kayıt": "#00CC96", "Resimsiz Kayıt": "#EF553B"}
        )
        fig2.update_layout(xaxis_title="İsimler", yaxis_title="Kayıt Sayısı", margin=dict(t=40, b=25, l=20, r=20))
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.subheader("🗂️ Tüm Kayıtlar")

# --- ARAMA VE LİSTELEME ---
search_query = st.text_input("🔍 Kayıtlarda Arama Yap:")

filtered_records = records
if search_query:
    query_lower = search_query.lower()
    filtered_records = [
        r for r in records 
        if query_lower in str(r.get("name", "") or "").lower() or query_lower in str(r.get("note", "") or "").lower()
    ]

if filtered_records:
    st.write(f"Toplam **{len(filtered_records)}** kayıt gösteriliyor.")
    
    col_h1, col_h2, col_h3, col_h4 = st.columns([2, 1, 1, 1])
    col_h1.markdown("**İsim & Not**")
    col_h2.markdown("**Tarih**")
    col_h3.markdown("**Görsel**")
    col_h4.markdown("**İşlem**")
    st.markdown("---")

    for r in filtered_records:
        rec_id = r.get("id")
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            name_val = r.get('name', '') or r.get('text', 'İsimsiz')
            st.markdown(f"**{name_val}**")
            note_val = r.get('note', '')
            if note_val:
                st.caption(note_val)
            
        with col2:
            st.write(r.get('date', ''))
            
        with col3:
            imgs = r.get("image_paths", [])
            valid_imgs = [img for img in imgs if img and str(img).startswith("http")]
            if valid_imgs:
                with st.expander(f"📷 Görseller ({len(valid_imgs)})"):
                    for idx, img_url in enumerate(valid_imgs):
                        st.markdown(f"[Görseli Aç {idx+1}]({img_url})", unsafe_allow_html=True)
            else:
                st.text("-")
                    
        with col4:
            if st.button("Sil", key=f"del_{rec_id}"):
                try:
                    supabase.table("notes_records").delete().eq("id", rec_id).execute()
                    st.success("Kayıt silindi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Silinirken hata oluştu: {e}")
                
        st.markdown("---")
else:
    st.info("Gösterilecek kayıt bulunamadı.")

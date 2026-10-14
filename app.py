import streamlit as st
import os
import pandas as pd
from collections import Counter

# --- SAYFA AYARI ---
st.set_page_config(page_title="Kişi ve Not Yönetim Sistemi", layout="centered")

# --- OTURUM (SESSION STATE) BAŞLANGIÇ DEĞERLERİ ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "username" not in st.session_state:
    st.session_state.username = "admin"

if "password" not in st.session_state:
    st.session_state.password = "1234"

if "records" not in st.session_state:
    st.session_state.records = []

# Düzenleme modu için state
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

# --- KULLANICI GİRİŞ FONKSİYONU ---
def check_password():
    """Kullanıcı adı ve şifre kontrolü yapar."""
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

# Eğer giriş yapılmadıysa programın geri kalanını çalıştırma
if not check_password():
    st.stop()

# --- GİRİŞ BAŞARILIYSA AÇILACAK ANA UYGULAMA ---
UPLOAD_DIR = "uploaded_images"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

st.title("📝 Kişi ve Not Yönetim Sistemi")
st.write("Bu program ile isim, not, isteğe bağlı çoklu resim kaydedebilir; kayıtları silebilir, düzenleyebilir ve grafik analizi yapabilirsiniz.")

# --- KULLANICI ADI VE ŞİFRE DEĞİŞTİRME PANELİ ---
with st.sidebar.expander("⚙️ Hesap Ayarları"):
    yeni_kullanici = st.text_input("Yeni Kullanıcı Adı", value=st.session_state.username)
    yeni_sifre = st.text_input("Yeni Şifre", type="password")
    
    if st.button("Bilgileri Güncelle"):
        st.session_state.username = yeni_kullanici
        if yeni_sifre:
            st.session_state.password = yeni_sifre
        st.success("Bilgiler güncellendi! Lütfen yeni bilgilerinizle tekrar giriş yapın.")
        st.session_state.authenticated = False
        st.rerun()

# Çıkış yap butonu
if st.sidebar.button("Çıkış Yap"):
    st.session_state.authenticated = False
    st.rerun()

st.markdown("---")

# --- DÜZENLEME MODU VEYA YENİ KAYIT FORMU ---
if st.session_state.edit_index is not None:
    # --- DÜZENLEME FORMU ---
    idx = st.session_state.edit_index
    current_record = st.session_state.records[idx]
    
    st.subheader(f"✏️ '{current_record['name']}' Kaydını Düzenle")
    
    with st.form("edit_form"):
        edit_name = st.text_input("İsim:", value=current_record["name"])
        edit_date = st.date_input("Tarih:", value=pd.to_datetime(current_record["date"]).date(), format="DD/MM/YYYY")
        edit_note = st.text_area("Not:", value=current_record["note"])
        edit_uploaded_files = st.file_uploader("Yeni Resimler Ekle (İsteğe Bağlı)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            update_button = st.form_submit_button(label="Değişiklikleri Kaydet")
        with col_f2:
            cancel_button = st.form_submit_button(label="İptal")
            
        if update_button:
            if edit_name and edit_note:
                image_paths = current_record.get("image_paths", [])
                if current_record.get("image_path") and not image_paths:
                    image_paths = [current_record["image_path"]]
                
                # Yeni yüklenen resimleri listeye ekle
                if edit_uploaded_files:
                    for uf in edit_uploaded_files:
                        img_path = os.path.join(UPLOAD_DIR, uf.name)
                        with open(img_path, "wb") as f:
                            f.write(uf.getbuffer())
                        image_paths.append(img_path)
                
                has_img = len(image_paths) > 0
                
                # Kaydı güncelle
                st.session_state.records[idx] = {
                    "name": edit_name,
                    "date": str(edit_date),
                    "note": edit_note,
                    "image_path": image_paths[0] if image_paths else None,
                    "image_paths": image_paths,
                    "has_image": has_img
                }
                st.session_state.edit_index = None
                st.success("Kayıt başarıyla güncellendi!")
                st.rerun()
            else:
                st.warning("Lütfen İsim ve Not alanlarını boş bırakmayın.")
                
        if cancel_button:
            st.session_state.edit_index = None
            st.rerun()
            
else:
    # --- YENİ KAYIT EKLEME FORMU ---
    with st.form("entry_form", clear_on_submit=True):
        st.subheader("Yeni Kayıt Ekle")
        name = st.text_input("İsim:")
        date = st.date_input("Tarih:", format="DD/MM/YYYY")
        note = st.text_area("Not:")
        uploaded_files = st.file_uploader("Bir veya Birden Fazla Resim Yükle (İsteğe Bağlı)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        
        submit_button = st.form_submit_button(label="Kaydet")
        
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
                
                if "records" not in st.session_state:
                    st.session_state.records = []
                    
                st.session_state.records.append({
                    "name": name,
                    "date": str(date),
                    "note": note,
                    "image_path": image_paths[0] if image_paths else None,
                    "image_paths": image_paths,
                    "has_image": has_image
                })
                st.success(f"'{name}' başarıyla kaydedildi!")
                st.rerun()
            else:
                st.warning("Lütfen İsim ve Not alanlarını doldurun.")

# --- GRAFİKLER BÖLÜMÜ ---
if "records" in st.session_state and st.session_state.records:
    st.markdown("---")
    st.subheader("📊 İstatistik ve Grafik Paneli")
    
    resimli_records = [r for r in st.session_state.records if r["has_image"]]
    resimsiz_records = [r for r in st.session_state.records if not r["has_image"]]
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("### 🖼️ 1. Resimli Kayıtlar Grafiği")
        if resimli_records:
            img_names = [r["name"] for r in resimli_records]
            df_img = pd.DataFrame(list(Counter(img_names).items()), columns=["İsim", "Tekrar Sayısı"])
            df_img = df_img.sort_values(by="Tekrar Sayısı", ascending=False).set_index("İsim")
            st.bar_chart(df_img)
        else:
            st.info("Henüz resimli kayıt eklenmedi.")
            
    with col_g2:
        st.markdown("### 📄 2. Resimsiz Kayıtlar Grafiği")
        if resimsiz_records:
            no_img_names = [r["name"] for r in resimsiz_records]
            df_no_img = pd.DataFrame(list(Counter(no_img_names).items()), columns=["İsim", "Tekrar Sayısı"])
            df_no_img = df_no_img.sort_values(by="Tekrar Sayısı", ascending=False).set_index("İsim")
            st.bar_chart(df_no_img)
        else:
            st.info("Henüz resimsiz kayıt eklenmedi.")

# --- KAYITLARI LİSTELEME, DÜZENLEME VE SİLME ---
st.markdown("---")
st.subheader("📋 Kayıtlı Veriler ve İşlemler")

if "records" in st.session_state and st.session_state.records:
    for idx, record in enumerate(st.session_state.records):
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                # Çoklu resimleri listeleme
                if "image_paths" in record and record["image_paths"]:
                    for img_p in record["image_paths"]:
                        if os.path.exists(img_p):
                            st.image(img_p, width=120)
                elif record.get("image_path") and os.path.exists(record["image_path"]):
                    st.image(record["image_path"], width=120)
                else:
                    st.info("Resim yok")
            with col2:
                st.markdown(f"### **{record['name']}**")
                st.markdown(f"**Tarih:** {record['date']}")
                st.write(f"**Not:** {record['note']}")
            with col3:
                # Düzenle ve Sil butonları yan yana
                if st.button("Düzenle", key=f"edit_{idx}"):
                    st.session_state.edit_index = idx
                    st.rerun()
                if st.button("Sil", key=f"del_{idx}"):
                    st.session_state.records.pop(idx)
                    st.rerun()
            st.markdown("---")
else:
    st.info("Henüz kayıt eklenmedi.")

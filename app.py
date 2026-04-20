import streamlit as st
import cv2
import numpy as np
import pandas as pd
from datetime import datetime
from PIL import Image
import re
import base64

# ===== CONFIG =====
st.set_page_config(page_title="QR Scanner Modern", layout="wide")

# ===== SIDEBAR =====
def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

img = get_base64("bg_sidebar.png")

st.sidebar.image("logo.png", width=100)
st.sidebar.markdown("## 📌 Sistem Scanner QR")

st.markdown(f"""
<style>
section[data-testid="stSidebar"] {{
    background: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)),
                url("data:image/png;base64,{img}");
    background-size: cover;
}}
section[data-testid="stSidebar"] * {{
    color: white !important;
}}
</style>
""", unsafe_allow_html=True)

# ===== DATA =====
try:
    df = pd.read_csv("data.csv")
except:
    df = pd.DataFrame(columns=[
        "Nama","NIM","Prodi","Pelayanan","Petugas","Status","Waktu"
    ])

# ===== FUNCTION =====
def clean_text(text):
    text = text.split(":", 1)[-1]
    return re.sub(r"[^a-zA-Z0-9\s]", "", text).strip()

def process_qr_data(data):
    try:
        p = data.split("|")
        return clean_text(p[0]), clean_text(p[1]), clean_text(p[2]), clean_text(p[3])
    except:
        return None

def is_duplicate_today(nim, pelayanan):
    if df.empty:
        return False
    df["Waktu"] = pd.to_datetime(df["Waktu"])
    today = datetime.now().date()
    return any(
        (df["NIM"].astype(str)==str(nim)) &
        (df["Pelayanan"].astype(str)==str(pelayanan)) &
        (df["Waktu"].dt.date==today)
    )

def save_data(row):
    global df
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv("data.csv", index=False)

def generate_pdf(filtered_df, bulan):
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet

    doc = SimpleDocTemplate("laporan.pdf")
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"LAPORAN BULAN {bulan}", styles["Title"]))
    elements.append(Paragraph("<br/><br/>", styles["Normal"]))

    data = [["Nama","NIM","Prodi","Pelayanan","Petugas","Status","Waktu"]]
    for _,r in filtered_df.iterrows():
        data.append(list(r.astype(str)))

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.grey),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("FONTSIZE",(0,0),(-1,-1),8)
    ]))

    elements.append(table)
    doc.build(elements)

# ===== UI =====
st.title("📷 DATA SCAN PELAYANAN")

menu = st.sidebar.selectbox("Menu", [
    "Scanner Camera",
    "Upload QR",
    "Dashboard",
    "Data",
    "Cetak PDF"
])

# ===== SCANNER ONLINE =====
if menu == "Scanner Camera":
    st.subheader("📷 Scan QR (Online)")

    img_file = st.camera_input("Ambil foto QR")

    if img_file:
        bytes_data = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
        img = cv2.imdecode(bytes_data, 1)

        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(img)

        if data:
            result = process_qr_data(data)

            if result:
                nama, nim, prodi, pelayanan = result

                st.markdown(f"<h2 style='text-align:center;color:#00ff99'>✔ {nama}</h2>", unsafe_allow_html=True)

                petugas = st.selectbox("Petugas", ["Ikinta Winanto","Gatot Edy Susanto"])
                status = st.selectbox("Status", ["Diambil Sendiri","Orang Lain"])

                if st.button("Simpan"):
                    if not is_duplicate_today(nim, pelayanan):
                        save_data({
                            "Nama":nama,
                            "NIM":nim,
                            "Prodi":prodi,
                            "Pelayanan":pelayanan,
                            "Petugas":petugas,
                            "Status":status,
                            "Waktu":datetime.now()
                        })
                        st.success("Tersimpan!")
                    else:
                        st.warning("Sudah pernah hari ini")
        else:
            st.error("QR tidak terbaca")

# ===== UPLOAD =====
from pyzxing import BarCodeReader
import tempfile

elif menu == "Upload QR":
    st.subheader("Upload QR Code")

    file = st.file_uploader("Upload gambar QR", type=["png","jpg","jpeg"])

    if file:
        # simpan sementara file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(file.read())
            temp_path = tmp.name

        reader = BarCodeReader()
        result = reader.decode(temp_path)

        if result and result[0].get("parsed"):
            data = result[0]["parsed"]

            st.write("DEBUG QR:", data)  # 🔥 buat cek isi QR

            hasil = process_qr_data(data)

            if hasil:
                nama, nim, prodi, pelayanan = hasil

                st.success(f"✔ {nama}")

                petugas = st.selectbox("Petugas", [
                    "Ikinta Winanto", "Gatot Edy Susanto"
                ])

                status = st.selectbox("Status Berkas", [
                    "Diambil Sendiri", "Orang Lain"
                ])

                waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if st.button("Simpan Data"):
                    if not is_duplicate_today(nim, pelayanan):
                        save_data({
                            "Nama": nama,
                            "NIM": nim,
                            "Prodi": prodi,
                            "Pelayanan": pelayanan,
                            "Petugas": petugas,
                            "Status": status,
                            "Waktu": waktu
                        })
                        st.success("Data tersimpan!")
                    else:
                        st.warning("Sudah pernah discan!")

            else:
                st.error("Format QR tidak sesuai")

        else:
            st.error("QR tidak terbaca (ZXing juga gagal)")
# ===== DASHBOARD =====
elif menu == "Dashboard":
    if not df.empty:
        df["Waktu"] = pd.to_datetime(df["Waktu"])
        today = len(df[df["Waktu"].dt.date==datetime.now().date()])
        month = len(df[df["Waktu"].dt.month==datetime.now().month])
        year = len(df[df["Waktu"].dt.year==datetime.now().year])

        c1,c2,c3 = st.columns(3)
        c1.metric("Harian",today)
        c2.metric("Bulanan",month)
        c3.metric("Tahunan",year)
    else:
        st.info("Belum ada data")

# ===== DATA =====
elif menu == "Data":
    if not df.empty:
        df = df.sort_values(by="Waktu", ascending=False)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Kosong")

# ===== PDF =====
elif menu == "Cetak PDF":
    if not df.empty:
        df["Waktu"] = pd.to_datetime(df["Waktu"])
        bulan = st.selectbox("Pilih Bulan", sorted(df["Waktu"].dt.month.unique()))
        filtered = df[df["Waktu"].dt.month==bulan]

        if st.button("Generate PDF"):
            generate_pdf(filtered, bulan)
            with open("laporan.pdf","rb") as f:
                st.download_button("Download PDF", f, "laporan.pdf")

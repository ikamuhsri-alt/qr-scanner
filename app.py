import streamlit as st
import cv2
from pyzbar.pyzbar import decode
import pandas as pd
from datetime import datetime
from PIL import Image
from reportlab.pdfgen import canvas
import re

# ====== CONFIG ======
st.set_page_config(page_title="QR Scanner Modern", layout="wide")

import base64

def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

img = get_base64("bg_sidebar.png")

st.sidebar.image("logo.png", width=120)
st.sidebar.markdown("## 📌 Sistem Scanner QR")

# ====== BACKGROUND SIDEBAR ======
import base64

def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

img = get_base64("bg_sidebar.png")

st.markdown(f"""
<style>

/* ===== SIDEBAR BACKGROUND ===== */
section[data-testid="stSidebar"] {{
    background: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)),
                url("data:image/png;base64,{img}");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}}

/* ===== TEXT SIDEBAR ===== */
section[data-testid="stSidebar"] * {{
    color: white !important;
}}

</style>
""", unsafe_allow_html=True)
# ====== DATA ======
try:
    df = pd.read_csv("data.csv")
except:
    df = pd.DataFrame(columns=[
        "Nama", "NIM", "Prodi", "Pelayanan",
        "Petugas", "Status", "Waktu"
    ])

# ====== FUNCTION ======

# 🔥 BERSIHKAN LABEL
def clean_text(text):
    text = text.split(":", 1)[-1]  # buang "Nama:"
    return re.sub(r"[^a-zA-Z0-9\s]", "", text).strip()

def process_qr_data(data):
    try:
        parts = data.split("|")
        nama = clean_text(parts[0])
        nim = clean_text(parts[1])
        prodi = clean_text(parts[2])
        pelayanan = clean_text(parts[3])
        return nama, nim, prodi, pelayanan
    except:
        return None

def is_duplicate_today(nim, pelayanan):
    if df.empty:
        return False

    df["Waktu"] = pd.to_datetime(df["Waktu"])
    today = datetime.now().date()

    return any(
        (df["NIM"].astype(str) == str(nim)) &
        (df["Pelayanan"].astype(str) == str(pelayanan)) &
        (df["Waktu"].dt.date == today)
    )

def save_data(row):
    global df
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv("data.csv", index=False)

def generate_pdf(filtered_df, bulan):
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet

    doc = SimpleDocTemplate("laporan.pdf")
    elements = []

    styles = getSampleStyleSheet()

    # 🔥 JUDUL
    title = Paragraph(f"LAPORAN PENGAMBILAN BERKAS BULAN {bulan}", styles["Title"])
    elements.append(title)

    # SPASI
    elements.append(Paragraph("<br/><br/>", styles["Normal"]))

    # 🔥 DATA TABLE
    data = [["Nama", "NIM", "Prodi", "Pelayanan", "Petugas", "Status", "Waktu"]]

    for _, row in filtered_df.iterrows():
        data.append([
            row["Nama"],
            row["NIM"],
            row["Prodi"],
            row["Pelayanan"],
            row["Petugas"],
            row["Status"],
            str(row["Waktu"])
        ])

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("FONTSIZE", (0,0), (-1,-1), 8),
    ]))

    elements.append(table)

    doc.build(elements)

# ====== UI ======
st.title("DATA SCAN PELAYANAN")

menu = st.sidebar.selectbox("Menu", [
    "Scanner Camera",
    "Upload QR",
    "Dashboard",
    "Data",
    "View Cetak",
    "Cetak PDF"
])

# ====== SCANNER CAMERA ======
if menu == "Scanner Camera":
    st.subheader("Scan via Camera")

    run = st.checkbox("Aktifkan Kamera")
    FRAME_WINDOW = st.image([])

    cap = cv2.VideoCapture(0)

    # 🔥 SETTING KAMERA BIAR LEBIH TERANG & TAJAM
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 150)

    scanned = set()

    while run:
        ret, frame = cap.read()
        if not ret:
            st.error("Camera tidak terdeteksi")
            break

        # 🔥 ZOOM BIAR QR KECIL TERBACA
        frame = cv2.resize(frame, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_LINEAR)

        # ====== PREPROCESSING ANTI BACKLIGHT ======
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Auto contrast (biar terang walau silau)
        gray = cv2.equalizeHist(gray)

        # Blur untuk noise
        blur = cv2.GaussianBlur(gray, (5,5), 0)

        # Adaptive threshold (penting banget buat backlight)
        thresh = cv2.adaptiveThreshold(
            blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )

        # 🔥 MULTI-DECODE (SUPER SENSITIF)
        decoded = decode(frame) + decode(gray) + decode(thresh)

        for obj in decoded:
            data = obj.data.decode("utf-8")
            result = process_qr_data(data)

            if result:
                nama, nim, prodi, pelayanan = result

                # 🔥 ANTI DOBEL SUPER KETAT
                if nim not in scanned and not is_duplicate_today(nim, pelayanan):

                    scanned.add(nim)  # simpan dulu biar ga double

                    petugas = st.selectbox("Petugas", [
                        "Ikinta Winanto", "Gatot Edy Susanto"
                    ])

                    status = st.selectbox("Status Berkas", [
                        "Diambil Sendiri", "Orang Lain"
                    ])

                    waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    save_data({
                        "Nama": nama,
                        "NIM": nim,
                        "Prodi": prodi,
                        "Pelayanan": pelayanan,
                        "Petugas": petugas,
                        "Status": status,
                        "Waktu": waktu
                    })

                    # 🔥 TAMPIL SUPER CLEAN
                    st.markdown(f"""
                    <div style="
                        font-size:40px;
                        font-weight:bold;
                        color:#00FFAA;
                        text-align:center;
                        margin-top:20px;
                    ">
                    ✔ {nama}
                    </div>
                    """, unsafe_allow_html=True)

                    break  # 🔥 STOP BIAR SEKALI SCAN SAJA

        FRAME_WINDOW.image(frame, channels="BGR")

    cap.release()

# ====== UPLOAD QR ======
elif menu == "Upload QR":
    st.subheader("Upload QR Code")

    file = st.file_uploader("Upload gambar QR")

    if file:
        img = Image.open(file)
        decoded = decode(img)

        for obj in decoded:
            data = obj.data.decode("utf-8")
            result = process_qr_data(data)

            if result:
                nama, nim, prodi, pelayanan = result

                # 🔥 tampil nama saja
                st.markdown(f"<h2>{nama}</h2>", unsafe_allow_html=True)

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

# ====== DASHBOARD ======
elif menu == "Dashboard":
    st.subheader("📊 Dashboard")

    if not df.empty:
        df["Waktu"] = pd.to_datetime(df["Waktu"])

        today = df[df["Waktu"].dt.date == datetime.now().date()]
        month = df[df["Waktu"].dt.month == datetime.now().month]
        year = df[df["Waktu"].dt.year == datetime.now().year]

        col1, col2, col3 = st.columns(3)

        col1.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #22c55e, #16a34a);
            padding:20px;
            border-radius:15px;
            text-align:center;
            font-size:25px;
            font-weight:bold;
        ">
        📅 Harian<br>{len(today)}
        </div>
        """, unsafe_allow_html=True)

        col2.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            padding:20px;
            border-radius:15px;
            text-align:center;
            font-size:25px;
            font-weight:bold;
        ">
        📆 Bulanan<br>{len(month)}
        </div>
        """, unsafe_allow_html=True)

        col3.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #f59e0b, #d97706);
            padding:20px;
            border-radius:15px;
            text-align:center;
            font-size:25px;
            font-weight:bold;
        ">
        📊 Tahunan<br>{len(year)}
        </div>
        """, unsafe_allow_html=True)

    else:
        st.info("Belum ada data")

# ====== DATA ======
elif menu == "Data":
    st.subheader("📋 Data Scan (Filter & Search)")

    if not df.empty:

        df["Waktu"] = pd.to_datetime(df["Waktu"])

        # ===== FILTER =====
        col1, col2, col3 = st.columns(3)

        # 🔍 SEARCH
        keyword = col1.text_input("🔍 Cari Nama / NIM")

        #  FILTER TANGGAL
        tanggal = col2.date_input(" Filter Tanggal", value=None)

        #  FILTER BULAN
        bulan = col3.selectbox(
            " Filter Bulan",
            ["Semua"] + sorted(df["Waktu"].dt.month.unique().tolist())
        )

        filtered = df.copy()

        # ===== APPLY FILTER =====

        # SEARCH
        if keyword:
            filtered = filtered[
                filtered["Nama"].str.contains(keyword, case=False, na=False) |
                filtered["NIM"].astype(str).str.contains(keyword)
            ]

        # FILTER TANGGAL
        if tanggal:
            filtered = filtered[
                filtered["Waktu"].dt.date == tanggal
            ]

        # FILTER BULAN
        if bulan != "Semua":
            filtered = filtered[
                filtered["Waktu"].dt.month == bulan
            ]

        # ===== SORT DESC =====
        filtered = filtered.sort_values(by="Waktu", ascending=False)

        # FORMAT WAKTU
        filtered["Waktu"] = filtered["Waktu"].dt.strftime("%Y-%m-%d %H:%M:%S")

        # ===== TAMPILKAN =====
        st.dataframe(
            filtered,
            use_container_width=True,
            height=500
        )

        # INFO JUMLAH DATA
        st.info(f"Total data: {len(filtered)}")

    else:
        st.info("Belum ada data")

# ====== PDF ======
elif menu == "Cetak PDF":
    st.subheader("🖨 Cetak Laporan Bulanan")

    if not df.empty:

        df["Waktu"] = pd.to_datetime(df["Waktu"])

        import calendar

        # 🔥 PILIH BULAN
        bulan_list = sorted(df["Waktu"].dt.month.unique())
        bulan_pilih = st.selectbox("Pilih Bulan", bulan_list)

        nama_bulan = calendar.month_name[bulan_pilih]

        # FILTER DATA
        filtered = df[df["Waktu"].dt.month == bulan_pilih]

        st.write(f"Total data bulan {nama_bulan}: {len(filtered)}")

        if st.button("Generate PDF"):
            
            # 🔥 NAMA FILE DINAMIS
            nama_file = f"laporan_{nama_bulan}.pdf"

            generate_pdf(filtered, nama_bulan)

            st.success(f"PDF berhasil dibuat: {nama_file}")

            # 🔥 DOWNLOAD BUTTON
            with open("laporan.pdf", "rb") as f:
                st.download_button(
                    label="⬇️ Download PDF",
                    data=f,
                    file_name=nama_file,
                    mime="application/pdf"
                )

            st.info("File juga tersimpan di folder project")

    else:
        st.info("Belum ada data")
elif menu == "View Cetak":
    st.subheader("📄 Preview Laporan (View Cetak)")

    if not df.empty:

        df["Waktu"] = pd.to_datetime(df["Waktu"])

        import calendar

        # 🔥 PILIH BULAN
        bulan_list = sorted(df["Waktu"].dt.month.unique())
        bulan_pilih = st.selectbox("Pilih Bulan", bulan_list)

        nama_bulan = calendar.month_name[bulan_pilih]

        # FILTER DATA
        filtered = df[df["Waktu"].dt.month == bulan_pilih]

        # 🔥 SORT TERBARU DI ATAS
        filtered = filtered.sort_values(by="Waktu", ascending=False)

        st.markdown(f"## 📊 Laporan Bulan {nama_bulan}")
        st.markdown(f"Total Data: **{len(filtered)}**")

        # FORMAT WAKTU
        filtered["Waktu"] = filtered["Waktu"].dt.strftime("%Y-%m-%d %H:%M:%S")

        # 🔥 TAMPIL TABEL
        st.dataframe(filtered, use_container_width=True, height=500)

        # 🔥 TOMBOL CETAK LANGSUNG
        if st.button("🖨 Cetak PDF"):
            generate_pdf(filtered, nama_bulan)
            st.success("PDF berhasil dibuat!")

    else:
        st.info("Belum ada data")        
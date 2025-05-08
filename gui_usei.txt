import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from PIL import Image, ImageTk
import sqlite3
import cv2
import pytesseract

# Cấu hình Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Hàm khởi tạo cơ sở dữ liệu
def initialize_database():
    conn = sqlite3.connect("parking.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bien_so TEXT NOT NULL,
        thoi_gian_vao TEXT NOT NULL,
        khu_vuc TEXT NOT NULL,
        trang_thai INTEGER NOT NULL,
        loai_xe TEXT NOT NULL,
        phi REAL,
        thoi_gian_ra TEXT
    )
    """)
    conn.commit()
    conn.close()

# Hàm mở cửa sổ chọn ảnh
def select_image():
    file_path = filedialog.askopenfilename(title="Chọn ảnh biển số", filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp")])
    return file_path

# Nhận diện biển số xe
def recognize_plate(image_path):
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
        text = pytesseract.image_to_string(thresh, lang='eng')
        text = text.strip().upper().replace(" ", "")
        if len(text) >= 6:
            return text
        return "UNKNOWN"
    except Exception as e:
        print(f"OCR Error: {str(e)}")
        return "ERROR"

# Hàm xử lý đặt chỗ
def dat_cho():
    ngay_dat = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duong_dan_anh = select_image()

    if duong_dan_anh:
        try:
            # Nhận diện biển số
            bien_so = recognize_plate(duong_dan_anh)
            if bien_so == "UNKNOWN":
                messagebox.showwarning("Không nhận diện được", "Không thể nhận diện biển số từ ảnh này.")
                return

            # Phân loại xe
            loai_xe = "Xe máy" if len(bien_so) < 8 else "Ô tô"
            khu_vuc = "A" if loai_xe == "Xe máy" else "B"

            # Lưu vào cơ sở dữ liệu
            conn = sqlite3.connect("parking.db")
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO parking (bien_so, thoi_gian_vao, khu_vuc, trang_thai, loai_xe, phi, thoi_gian_ra)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (bien_so, ngay_dat, khu_vuc, 1, loai_xe, None, None))
            conn.commit()
            conn.close()

            # Cập nhật Label hiển thị biển số xe
            label_bien_so.config(text=f"Biển số xe: {bien_so}", fg="green")

            messagebox.showinfo("Thành công", f"Đặt chỗ thành công!\nBiển số: {bien_so}\nLoại xe: {loai_xe}\nKhu vực: {khu_vuc}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi xử lý: {e}")
    else:
        messagebox.showwarning("Chưa chọn ảnh", "Vui lòng chọn ảnh biển số.")

# Giao diện chính
window = tk.Tk()
window.title("Bãi Giữ Xe Thông Minh")
window.geometry("600x500")
window.configure(bg="#f0f8ff")  # Màu nền xanh nhạt

# Tiêu đề
label_title = tk.Label(window, text="🚗 Bãi Giữ Xe Thông Minh 🚗", font=("Arial", 20, "bold"), bg="#f0f8ff", fg="#4682b4")
label_title.pack(pady=20)

# Label hiển thị thông tin biển số xe
label_bien_so = tk.Label(window, text="Biển số xe sẽ hiển thị ở đây", font=("Arial", 14), bg="#f0f8ff", fg="blue")
label_bien_so.pack(pady=10)

# Nút đặt chỗ
btn_dat_cho = tk.Button(window, text="Đặt chỗ và nhận diện biển số", font=("Arial", 14), bg="#32cd32", fg="white", command=dat_cho)
btn_dat_cho.pack(pady=20)

# Khởi tạo cơ sở dữ liệu
initialize_database()

window.mainloop()
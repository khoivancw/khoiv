import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import sqlite3
import time
import cv2
import pytesseract

# Cấu hình Tesseract OCR (nếu cần)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Cấu hình cơ sở dữ liệu
DB_NAME = "parking.db"

# Hàm khởi tạo cơ sở dữ liệu
def initialize_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_plate TEXT NOT NULL,
        time_in TEXT NOT NULL,
        time_out TEXT,
        fee REAL,
        vehicle_type TEXT NOT NULL,
        area TEXT NOT NULL
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

# Phân biệt loại xe dựa trên biển số
def check_vehicle_type(license_plate):
    motorbike_keywords = ["AH", "H1", "AB", "C1", "E1", "G1", "F1", "K1"]
    for keyword in motorbike_keywords:
        if keyword in license_plate:
            return 'motorbike', "Khu A"
    return 'car', "Khu B"

# Tính phí đậu xe
def calculate_parking_fee(vehicle_type, time_in):
    current_time = time.time()
    time_parked = current_time - time_in
    hours_parked = time_parked / 3600
    if vehicle_type == 'motorbike':
        fee = 1000 * hours_parked
    else:
        fee = 2000 * hours_parked
    return round(fee, 2)

# Lưu xe vào cơ sở dữ liệu
def park_vehicle(tree, license_plate, vehicle_type, area):
    time_in = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO parking (license_plate, time_in, vehicle_type, area)
    VALUES (?, ?, ?, ?)
    """, (license_plate, time_in, vehicle_type, area))
    conn.commit()
    conn.close()

    tree.insert("", "end", values=(license_plate, time_in, "None", "None", vehicle_type, area))
    messagebox.showinfo("Thông báo", f"{vehicle_type.capitalize()} {license_plate} đã được đậu vào {area}.")

# Xử lý xe vào bãi
def process_parking(tree, image_canvas):
    image_path = select_image()
    if image_path:
        # Hiển thị ảnh trong khung nhỏ
        img = Image.open(image_path)
        img = img.resize((200, 150), Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(img)
        image_canvas.image = img_tk
        image_canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)

        # Nhận diện biển số
        license_plate_text = recognize_plate(image_path)
        if license_plate_text and license_plate_text != "UNKNOWN":
            vehicle_type, area = check_vehicle_type(license_plate_text)
            park_vehicle(tree, license_plate_text, vehicle_type, area)
        else:
            messagebox.showwarning("Không nhận diện được", "Không thể nhận diện biển số từ ảnh này.")
    else:
        messagebox.showwarning("Chưa chọn ảnh", "Bạn chưa chọn ảnh biển số.")

# Xử lý xe ra bãi
def process_exit(tree):
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Chưa chọn xe", "Vui lòng chọn xe muốn ra.")
        return

    item = tree.item(selected_item)
    license_plate = item["values"][0]
    time_in_str = item["values"][1]
    vehicle_type = item["values"][4]

    # Tính phí và cập nhật thời gian ra
    time_in = time.mktime(time.strptime(time_in_str, "%Y-%m-%d %H:%M:%S"))
    fee = calculate_parking_fee(vehicle_type, time_in)
    time_out = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE parking
    SET time_out = ?, fee = ?
    WHERE license_plate = ? AND time_out IS NULL
    """, (time_out, fee, license_plate))
    conn.commit()
    conn.close()

    tree.item(selected_item, values=(license_plate, time_in_str, time_out, f"{fee} VND", vehicle_type, item["values"][5]))
    messagebox.showinfo("Thanh toán", f"Phí đậu xe cho {license_plate} là {fee} VND.")

# Xóa tất cả dữ liệu
def clear_all(tree):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM parking")
    conn.commit()
    conn.close()

    tree.delete(*tree.get_children())
    messagebox.showinfo("Thông báo", "Đã xóa tất cả dữ liệu trong bãi đậu.")

# Giao diện người dùng
def create_gui():
    root = tk.Tk()
    root.title("Hệ thống Bãi Đậu Xe Thông Minh")
    root.geometry("1000x600")
    root.configure(bg="#f0f8ff")  # Màu nền xanh nhạt

    # Frame chính
    main_frame = tk.Frame(root, bg="#DF062D")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Phần trên: Bảng dữ liệu
    table_frame = tk.Frame(main_frame, bg="#87ceeb")
    table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

    columns = ["Biển số", "Giờ vào", "Giờ ra", "Phí", "Loại xe", "Khu"]
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100, anchor=tk.CENTER)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Thanh cuộn cho bảng
    scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Phần bên phải: Hiển thị ảnh biển số
    image_frame = tk.Frame(main_frame, bg="#5376F6", width=200)
    image_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

    image_label = tk.Label(image_frame, text="Ảnh biển số xe", bg="#5376F6", fg="white", font=("Arial", 12, "bold"))
    image_label.pack(pady=10)

    image_canvas = tk.Canvas(image_frame, width=200, height=150, bg="#f0f8ff", relief=tk.SUNKEN)
    image_canvas.pack()

    # Phần dưới: Các nút chức năng và trạng thái
    bottom_frame = tk.Frame(main_frame, bg="")
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

    # Các nút chức năng
    button_frame = tk.Frame(bottom_frame, bg="")
    button_frame.pack(side=tk.LEFT, padx=10)

    tk.Button(button_frame, text="Xe vào (Ảnh)", bg="#32cd32", fg="white", font=("Arial", 12), width=15, command=lambda: process_parking(tree, image_canvas)).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Xe ra", bg="#ff4500", fg="white", font=("Arial", 12), width=15, command=lambda: process_exit(tree)).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Xóa tất cả", bg="#7f8c8d", fg="white", font=("Arial", 12), width=15, command=lambda: clear_all(tree)).pack(side=tk.LEFT, padx=5)

    root.mainloop()

# Chạy chương trình
initialize_database()
create_gui()
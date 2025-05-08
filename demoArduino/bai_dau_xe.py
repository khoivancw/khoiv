# main_gui_full.py - Gộp toàn bộ + xác nhận phí khi xe ra + thêm nút xóa lịch sử
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
import cv2
import os
import sqlite3
import platform
from datetime import datetime

# ======================= UTILS =========================
def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def play_sound(action):
    if platform.system() == "Windows":
        path = f"./sounds/{action}.wav"
        if os.path.exists(path):
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME)

# ====================== OCR ============================
import easyocr
reader = easyocr.Reader(['en'], gpu=False)

def recognize_plate(image_path):
    result = reader.readtext(image_path)
    if result:
        return result[0][1].upper().replace(" ", "")
    return "UNKNOWN"

# =================== DATABASE ==========================
class DBHelper:
    def __init__(self):
        self.conn = sqlite3.connect('parking.db')
        self.create_table()

    def create_table(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS parking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bien_so TEXT,
                thoi_gian_vao TEXT,
                thoi_gian_ra TEXT,
                phi INTEGER
            )
        ''')
        self.conn.commit()

    def insert_entry(self, bien_so, thoi_gian_vao):
        self.conn.execute("INSERT INTO parking (bien_so, thoi_gian_vao) VALUES (?, ?)", (bien_so, thoi_gian_vao))
        self.conn.commit()

    def update_exit(self, bien_so, thoi_gian_ra):
        cur = self.conn.cursor()
        cur.execute("SELECT thoi_gian_vao FROM parking WHERE bien_so = ? AND thoi_gian_ra IS NULL", (bien_so,))
        row = cur.fetchone()
        if row:
            vao = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
            ra = datetime.strptime(thoi_gian_ra, "%Y-%m-%d %H:%M:%S")
            minutes = max(int((ra - vao).total_seconds() / 60), 1)
            phi = minutes * 1000
            cur.execute("UPDATE parking SET thoi_gian_ra = ?, phi = ? WHERE bien_so = ? AND thoi_gian_ra IS NULL",
                        (thoi_gian_ra, phi, bien_so))
            self.conn.commit()
            return vao.strftime("%H:%M:%S"), ra.strftime("%H:%M:%S"), phi
        return None, None, None

    def fetch_all(self):
        return self.conn.execute("SELECT bien_so, thoi_gian_vao, thoi_gian_ra, phi FROM parking ORDER BY id DESC").fetchall()

    def count_active(self):
        return self.conn.execute("SELECT COUNT(*) FROM parking WHERE thoi_gian_ra IS NULL").fetchone()[0]

    def delete_all(self):
        self.conn.execute("DELETE FROM parking")
        self.conn.commit()

# ===================== GUI =============================
class ParkingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("BÃI GIỮ XE - AI SMART SYSTEM")
        self.db = DBHelper()
        self.init_ui()

    def init_ui(self):
        tk.Label(self.root, text="HỆ THỐNG BÃI GIỮ XE THÔNG MINH", font=("Helvetica", 20, "bold"), fg="blue").pack(pady=10)

        self.tree = ttk.Treeview(self.root, columns=("Biển số", "Giờ vào", "Giờ ra", "Phí"), show='headings')
        for col in self.tree['columns']:
            self.tree.heading(col, text=col)
        self.tree.pack(pady=5, padx=10, fill=tk.X)

        self.image_label = tk.Label(self.root)
        self.image_label.pack(pady=5)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Xe vào (webcam)", bg="green", fg="white", command=self.xe_vao_cam, width=18).grid(row=0, column=0, padx=5)
        tk.Button(button_frame, text="Xe vào (ảnh)", bg="orange", fg="black", command=self.xe_vao_anh, width=18).grid(row=0, column=1, padx=5)
        tk.Button(button_frame, text="Xe ra", bg="red", fg="white", command=self.xe_ra, width=18).grid(row=0, column=2, padx=5)
        tk.Button(button_frame, text="Lịch sử", bg="blue", fg="white", command=self.load_data, width=15).grid(row=0, column=3, padx=5)
        tk.Button(button_frame, text="Xóa lịch sử", bg="gray", fg="black", command=self.clear_all, width=15).grid(row=0, column=4, padx=5)

        self.status_label = tk.Label(self.root, text="Sẵn sàng", font=("Arial", 12), fg="darkgreen")
        self.status_label.pack(pady=5)

        self.active_count_label = tk.Label(self.root, text="", font=("Arial", 11), fg="black")
        self.active_count_label.pack()

        self.load_data()

    def xe_vao_cam(self):
        bien_so = self.capture_plate_via_webcam()
        self.insert_vehicle(bien_so)

    def xe_vao_anh(self):
        path = filedialog.askopenfilename(title="Chọn ảnh biển số xe", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if not path:
            return
        bien_so = recognize_plate(path)
        self.insert_vehicle(bien_so)
        self.show_image(path)

    def insert_vehicle(self, bien_so):
        if bien_so:
            self.db.insert_entry(bien_so, get_current_time())
            self.status_label.config(text=f"Xe {bien_so} vào bãi")
            play_sound("in")
            self.load_data()

    def xe_ra(self):
        selected = self.tree.selection()
        if selected:
            bien_so = self.tree.item(selected[0])['values'][0]
        else:
            choice = messagebox.askquestion("Xác nhận", "Xe ra bằng ảnh (Yes) hay nhập biển số (No)?")
            if choice == 'yes':
                path = filedialog.askopenfilename(title="Chọn ảnh xe ra", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
                if not path:
                    return
                bien_so = recognize_plate(path)
                self.show_image(path)
            else:
                bien_so = simpledialog.askstring("Nhập biển số", "Nhập biển số xe:")

        if bien_so:
            vao, ra, phi = self.db.update_exit(bien_so.upper(), get_current_time())
            if phi:
                messagebox.showinfo("Thanh toán", f"Xe: {bien_so}\nVào: {vao}\nRa: {ra}\nPhí: {phi:,} VND")
            self.status_label.config(text=f"Xe {bien_so.upper()} đã rời bãi")
            play_sound("out")
            self.load_data()

    def clear_all(self):
        if messagebox.askyesno("Xác nhận", "Bạn chắc chắn muốn xóa toàn bộ dữ liệu không?"):
            self.db.delete_all()
            self.load_data()
            self.status_label.config(text="Đã xóa toàn bộ lịch sử")

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.db.fetch_all():
            self.tree.insert('', 'end', values=row)
        active = self.db.count_active()
        self.active_count_label.config(text=f"Số xe đang gửi trong bãi: {active}")

    def show_image(self, path):
        img = Image.open(path)
        img.thumbnail((300, 200))
        photo = ImageTk.PhotoImage(img)
        self.image_label.config(image=photo)
        self.image_label.image = photo

    def capture_plate_via_webcam(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Lỗi", "Không mở được camera")
            return None

        messagebox.showinfo("Hướng dẫn", "Nhấn SPACE để chụp ảnh biển số, ESC để thoát")

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow("Camera - Nhấn SPACE để chụp", frame)
            key = cv2.waitKey(1)
            if key == 27:
                cap.release()
                cv2.destroyAllWindows()
                return None
            if key == 32:
                cap.release()
                cv2.destroyAllWindows()
                temp_path = "temp_plate.jpg"
                cv2.imwrite(temp_path, frame)
                plate = recognize_plate(temp_path)
                self.show_image(temp_path)
                os.remove(temp_path)
                return plate

# ===================== MAIN ============================
if __name__ == '__main__':
    root = tk.Tk()
    app = ParkingGUI(root)
    root.mainloop()

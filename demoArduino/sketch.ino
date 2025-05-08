#include <Servo.h>
#include <LiquidCrystal_I2C.h>

Servo motor;
String inputString = "";
bool stringComplete = false;

// Giới hạn 3 chỗ đậu xe
const int MAX_SLOTS = 3;

// Mảng thẻ và biển số
String cards[MAX_SLOTS] = {
  "TX001", "TX002", "TX003"
};

String bienSoArr[MAX_SLOTS];
unsigned long thoiGianVao[MAX_SLOTS];

// Định nghĩa chân
const int ledXanh = 6;         // LED báo xe vào/ra
const int ledDo = 7;           // LED báo lỗi
const int ledVang = 8;         // LED báo đang xử lý
const int nutThanhToan = 2;    // Nút xác nhận thanh toán
const int nutTienMat = 3;      // Nút chọn thanh toán tiền mặt
const int nutChuyenKhoan = 4;  // Nút chọn thanh toán chuyển khoản
const int ledThanhToan = 5;    // LED báo đang thanh toán

LiquidCrystal_I2C lcd(0x27, 16, 2);

// Biến theo dõi trạng thái thanh toán
bool dangThanhToan = false;
int phuongThucThanhToan = 0; // 0: chưa chọn, 1: tiền mặt, 2: chuyển khoản

// Thời gian hệ thống
const String CURRENT_TIME = "2025-05-06 21:06:45";
const String CURRENT_USER = "khoivancw";
const unsigned long UNIX_TIME = 1746832005; // 2025-05-06 21:06:45 UTC

// Hàm lấy thời gian hiện tại
unsigned long getCurrentTime() {
  return UNIX_TIME + (millis() / 1000);
}

// Hàm chuyển thời gian Unix thành chuỗi định dạng
String formatDateTime(unsigned long unix_time) {
  unsigned long seconds = unix_time % 60;
  unsigned long minutes = (unix_time / 60) % 60;
  unsigned long hours = (unix_time / 3600) % 24;
  
  return String(hours) + ":" + 
         (minutes < 10 ? "0" : "") + String(minutes) + ":" +
         (seconds < 10 ? "0" : "") + String(seconds);
}

// Hàm tính thời gian gửi xe
String formatParkingTime(unsigned long startTime, unsigned long endTime) {
  unsigned long duration = endTime - startTime;
  unsigned long hours = duration / 3600;
  unsigned long minutes = (duration % 3600) / 60;
  return String(hours) + "h" + (minutes < 10 ? "0" : "") + String(minutes) + "p";
}

// Hàm tính phí gửi xe
unsigned long tinhPhiGuiXe(unsigned long startTime, unsigned long endTime) {
  unsigned long duration = endTime - startTime;
  unsigned long hours = (duration + 3599) / 3600; // Làm tròn lên giờ
  if(hours == 0) hours = 1;
  return hours * 5000;
}

// Hàm in thông tin debug qua Serial
void inThongTinXe() {
  Serial.println("\n=== DANH SACH XE TRONG BAI ===");
  for(int i = 0; i < MAX_SLOTS; i++) {
    if(bienSoArr[i] != "") {
      Serial.print("Vi tri ");
      Serial.print(i);
      Serial.print(": ");
      Serial.print(bienSoArr[i]);
      Serial.print(" (Thoi gian vao: ");
      Serial.print(formatDateTime(thoiGianVao[i]));
      Serial.println(")");
    }
  }
  Serial.println("==============================\n");
}

void setup() {
  Serial.begin(9600);
  Serial.println("HE THONG BAI GIU XE THONG MINH");
  Serial.println("READY - " + CURRENT_TIME);
  Serial.println("User: " + CURRENT_USER);

  // Khởi tạo servo
  motor.attach(9);
  motor.write(0);  // Đóng barrier
  inputString.reserve(200);

  // Cấu hình các chân
  pinMode(ledXanh, OUTPUT);
  pinMode(ledDo, OUTPUT);
  pinMode(ledVang, OUTPUT);
  pinMode(ledThanhToan, OUTPUT);
  pinMode(nutThanhToan, INPUT_PULLUP);
  pinMode(nutTienMat, INPUT_PULLUP);
  pinMode(nutChuyenKhoan, INPUT_PULLUP);

  // Khởi tạo mảng
  for(int i = 0; i < MAX_SLOTS; i++) {
    bienSoArr[i] = "";
    thoiGianVao[i] = 0;
  }

  // Khởi tạo LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("BAI XE THONG MINH");
  lcd.setCursor(0, 1);
  lcd.print("User: " + CURRENT_USER);
  delay(2000);
}

// Hàm điều khiển barrier
void moBarrier() {
  digitalWrite(ledVang, HIGH);
  motor.write(90);
  delay(1000);
  motor.write(0);
  delay(500);
  digitalWrite(ledVang, LOW);
}

// Hàm xử lý thanh toán
bool xuLyThanhToan(String bienSo, unsigned long phi) {
  dangThanhToan = true;
  phuongThucThanhToan = 0;
  
  unsigned long startTime = millis();
  const unsigned long TIMEOUT = 30000; // Timeout 30 giây
  
  while (dangThanhToan && (millis() - startTime < TIMEOUT)) {
    if (phuongThucThanhToan == 0) {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Chon thanh toan:");
      lcd.setCursor(0, 1);
      lcd.print("1.Tien 2.Chuyen");
      
      if (digitalRead(nutTienMat) == LOW) {
        phuongThucThanhToan = 1;
        delay(200);
      }
      else if (digitalRead(nutChuyenKhoan) == LOW) {
        phuongThucThanhToan = 2;
        delay(200);
      }
    }
    
    if (phuongThucThanhToan == 1) {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Tien mat:");
      lcd.setCursor(0, 1);
      lcd.print(String(phi) + " VND");
      
      digitalWrite(ledThanhToan, HIGH);
      
      if (digitalRead(nutThanhToan) == LOW) {
        dangThanhToan = false;
        digitalWrite(ledThanhToan, LOW);
        Serial.println("THANH_TOAN_OK|" + bienSo + "|TIEN_MAT|" + String(phi));
        return true;
      }
    }
    
    if (phuongThucThanhToan == 2) {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Quet ma QR:");
      lcd.setCursor(0, 1);
      lcd.print(String(phi) + " VND");
      
      digitalWrite(ledThanhToan, HIGH);
      Serial.println("SHOW_QR|" + bienSo + "|" + String(phi));
      
      if (digitalRead(nutThanhToan) == LOW) {
        dangThanhToan = false;
        digitalWrite(ledThanhToan, LOW);
        Serial.println("THANH_TOAN_OK|" + bienSo + "|CHUYEN_KHOAN|" + String(phi));
        return true;
      }
    }
    delay(100);
  }
  
  digitalWrite(ledThanhToan, LOW);
  lcd.clear();
  lcd.print("Het thoi gian!");
  delay(2000);
  return false;
}

void loop() {
  if (stringComplete) {
    lcd.clear();
    
    if (inputString.startsWith("PHAT_THE|")) {
      String bienSo = inputString.substring(9);
      bienSo.trim();
      
      int index = -1;
      for (int i = 0; i < MAX_SLOTS; i++) {
        if (bienSoArr[i] == "") {
          index = i;
          break;
        }
      }

      if (index != -1) {
        String maThe = cards[index];
        bienSoArr[index] = bienSo;
        thoiGianVao[index] = getCurrentTime();

        digitalWrite(ledXanh, HIGH);
        delay(500);
        digitalWrite(ledXanh, LOW);
        
        moBarrier();

        Serial.println("DA_NHA_THE|" + maThe + "|" + bienSo);
        
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("DA NHAN THE:");
        lcd.setCursor(0, 1);
        lcd.print(maThe);
        
        Serial.println("\nXe vao luc: " + formatDateTime(getCurrentTime()));
        Serial.println("Bien so: " + bienSo);
        Serial.println("The: " + maThe);
        inThongTinXe();
      } else {
        digitalWrite(ledDo, HIGH);
        Serial.println("HET_THE");
        
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("HET CHO!");
        delay(1000);
        digitalWrite(ledDo, LOW);
      }
    }
    
    else if (inputString.startsWith("LAY_XE|")) {
      String bienSo = inputString.substring(7);
      bienSo.trim();
      
      Serial.println("\nTim xe: " + bienSo);
      inThongTinXe();
      
      bool timThay = false;
      int index = -1;
      
      for (int i = 0; i < MAX_SLOTS; i++) {
        if (bienSoArr[i] == bienSo) {
          timThay = true;
          index = i;
          Serial.println("Tim thay xe tai vi tri: " + String(i));
          break;
        }
      }

      if (timThay) {
        unsigned long thoiGianRa = getCurrentTime();
        String thoiGianHienThi = formatParkingTime(thoiGianVao[index], thoiGianRa);
        unsigned long phi = tinhPhiGuiXe(thoiGianVao[index], thoiGianRa);

        Serial.println("\n=== THONG TIN THANH TOAN ===");
        Serial.println("Bien so: " + bienSo);
        Serial.println("Thoi gian vao: " + formatDateTime(thoiGianVao[index]));
        Serial.println("Thoi gian ra: " + formatDateTime(thoiGianRa));
        Serial.println("Thoi gian gui: " + thoiGianHienThi);
        Serial.println("Phi gui xe: " + String(phi) + " VND");
        Serial.println("===========================\n");

        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("XE: " + bienSo);
        lcd.setCursor(0, 1);
        lcd.print(thoiGianHienThi + "=" + String(phi) + "d");
        delay(2000);
        
        if (xuLyThanhToan(bienSo, phi)) {
          moBarrier();
          
          bienSoArr[index] = "";
          thoiGianVao[index] = 0;
          
          lcd.clear();
          lcd.setCursor(0, 0);
          lcd.print("DA THANH TOAN");
          lcd.setCursor(0, 1);
          lcd.print("Tam biet!");
          delay(2000);
          
          Serial.println("\nXe ra luc: " + formatDateTime(getCurrentTime()));
          Serial.println("Bien so: " + bienSo);
          inThongTinXe();
        }
      } else {
        digitalWrite(ledDo, HIGH);
        Serial.println("KHONG_TIM_THAY|" + bienSo);
        
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("KHONG TIM THAY");
        lcd.setCursor(0, 1);
        lcd.print("XE: " + bienSo);
        delay(2000);
        digitalWrite(ledDo, LOW);
      }
    }

    inputString = "";
    stringComplete = false;
  }
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}
# 🧵 Hệ thống Quản lý Xưởng Thêu AI (Embroidery Manager Pro)

Ứng dụng quản lý đơn hàng xưởng thêu tích hợp AI (Gemini) giúp trích xuất thông tin từ đoạn chat và tự động tạo mẫu thiết kế thêu từ ảnh thật của thú cưng.

## ✨ Tính năng chính
- **📦 Quản lý Đơn hàng**: Theo dõi, lọc và cập nhật trạng thái đơn hàng thời gian thực.
- **🪄 AI Input Hub**: Tự động trích xuất thông tin đơn hàng từ nội dung chat (Zalo, Facebook...) bằng Gemini AI.
- **🎨 AI Design Assistant**: Tạo mẫu thêu từ ảnh thú cưng bằng model Nano Banana (Gemini Image Preview).
- **📊 Dashboard**: Thống kê doanh thu, tiến độ và hiệu suất xưởng (Sắp ra mắt lại).
- **⚙️ Cấu hình động**: Tùy chỉnh danh sách trạng thái và màu sắc hiển thị.
- **🔔 Thông báo**: Tự động gửi cập nhật trạng thái qua Telegram Bot.

## 🛠 Công nghệ sử dụng
- **Frontend**: Streamlit
- **Backend/Database**: Supabase
- **AI**: Google Gemini API (Flash-Preview & Image-Preview)
- **Notification**: Telegram Bot API

## 🚀 Cài đặt

1. Clone repository:
```bash
git clone <repository-url>
cd c-app-theu
```

2. Cài đặt thư viện:
```bash
pip install -r requirements.txt
```

3. Cấu hình biến môi trường:
Tạo file `.env` và điền các thông tin sau:
```env
GOOGLE_API_KEY=your_key
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_id
```

4. Chạy ứng dụng:
```bash
streamlit run app.py
```

## 📝 Giấy phép
Bản quyền thuộc về Xưởng Thêu 4.0.


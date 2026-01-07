# 🧵 Embroidery Manager Pro - Hệ thống Quản lý Xưởng Thêu AI

Ứng dụng quản lý xưởng thêu thông minh, tích hợp trí tuệ nhân tạo (Google Gemini) để tối ưu hóa quy trình từ khâu tiếp nhận đơn hàng đến sản xuất.

## ✨ Tính năng nổi bật

- **📦 Quản lý Đơn hàng Tập trung**: Giao diện dashboard hiện đại, hỗ trợ lọc, tìm kiếm và cập nhật trạng thái đơn hàng theo thời gian thực.
- **🪄 AI Input Hub**: Sử dụng Gemini AI để tự động trích xuất thông tin khách hàng, sản phẩm, màu sắc, size từ nội dung chat (Zalo/Messenger) chỉ trong 1 giây.
- **🎨 AI Edit Ảnh (Beta)**: Tích hợp model `gemini-3-pro-image-preview` để chỉnh sửa mẫu thêu, đổi màu sắc hoặc thêm chi tiết dựa trên ảnh gốc và yêu cầu bằng văn bản.
- **🖨️ In Phiếu Sản Xuất Thông Minh**: 
    - Layout dọc chuẩn A4, tối ưu diện tích (fit ~4 đơn/trang).
    - **Logic Dynamic Images**: Tự động ẩn các ô ảnh trống, chỉ hiển thị những ảnh thực tế có trong đơn (Ảnh gốc, Ảnh AI, Design).
    - Hỗ trợ in gộp nhiều đơn hàng chỉ với 1 click.
- **📊 Xuất Excel (Nobita Format)**: Xuất dữ liệu đơn hàng ra file Excel chuẩn định dạng template Nobita để dễ dàng nhập vào các hệ thống vận chuyển.
- **☁️ Cloud Storage Integration**: Đồng bộ ảnh trực tiếp lên Supabase Storage, hỗ trợ xem ảnh full-size sắc nét.
- **🔔 Telegram Notification**: Tự động gửi thông báo cập nhật trạng thái đơn hàng và đơn hàng mới về nhóm Telegram.

## 🛠 Công nghệ sử dụng

- **Frontend/UI**: [Streamlit](https://streamlit.io/) (Giao diện dashboard tương tác)
- **Database & Storage**: [Supabase](https://supabase.com/) (PostgreSQL & Object Storage)
- **AI Engine**: [Google Gemini Pro API](https://ai.google.dev/) (Text processing & Image generation)
- **Excel Logic**: `Openpyxl` & `Pandas`
- **Notification**: Telegram Bot API

## 🚀 Hướng dẫn cài đặt

1. **Clone repository**:
   ```bash
   git clone <repository-url>
   cd app_theu
   ```

2. **Cài đặt thư viện**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Cấu hình biến môi trường**:
   Tạo file `.env` tại thư mục gốc:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_anon_key
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_group_id
   ```

4. **Khởi chạy ứng dụng**:
   ```bash
   streamlit run app.py
   ```

---
© 2026 - Phát triển bởi **Xưởng Thêu 4.0**

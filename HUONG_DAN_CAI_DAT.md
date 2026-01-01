# Hướng dẫn cài đặt App Quản lý Đơn hàng Thêu - AI Powered

## 📋 Yêu cầu hệ thống

- Python 3.8 trở lên
- Kết nối Internet (để sử dụng Gemini AI)

## 🚀 Bước 1: Cài đặt thư viện

Mở terminal/cmd tại thư mục `c:\app_theu` và chạy lệnh:

```bash
pip install -r requirements.txt
```

## 🔑 Bước 2: Cấu hình Google Gemini API Key

### 2.1. Lấy API Key miễn phí

1. Truy cập: https://aistudio.google.com/app/apikey
2. Đăng nhập bằng tài khoản Google
3. Bấm "Create API Key" để tạo key mới
4. Copy API key vừa tạo

### 2.2. Tạo file .env

Tạo file mới tên `.env` trong thư mục `c:\app_theu` với nội dung:

```
GOOGLE_API_KEY=your_google_api_key_here
```

**Thay thế** `your_google_api_key_here` bằng API key bạn vừa copy ở bước 2.1

**Ví dụ:**
```
GOOGLE_API_KEY=AIzaSyAbc123def456ghi789jkl012mno345pqr
```

## ▶️ Bước 3: Chạy ứng dụng

Chạy lệnh:

```bash
streamlit run app.py
```

Ứng dụng sẽ tự động mở trong trình duyệt tại địa chỉ: http://localhost:8501

## 💡 Cách sử dụng AI-Powered Input Hub

### Quy trình nhanh (3 bước):

1. **Dán chat** → Copy nội dung chat chốt đơn từ khách → Paste (Ctrl+V) vào ô text
2. **Trích xuất** → Bấm nút "🪄 Tự động trích xuất thông tin"
3. **Kiểm tra & Lưu** → Kiểm tra thông tin AI đã điền → Sửa nếu cần → Bấm "💾 Lưu đơn hàng"

### Ví dụ nội dung chat:

```
Nguyên Nguyên
Số 10 Phạm Văn Bạch, Cầu Giấy, Hà Nội
Sđt: 0379651197
1 áo đen M thêu logo Harry
1 áo xám 2xl thêu Sue
Tổng 790k cọc 300k
```

AI sẽ tự động trích xuất:
- ✅ Tên: Nguyên Nguyên
- ✅ SĐT: 0379651197
- ✅ Địa chỉ: Số 10 Phạm Văn Bạch, Cầu Giấy, Hà Nội
- ✅ Số lượng: 2
- ✅ Tổng tiền: 790,000đ
- ✅ SKU: TS-DEN-M, TS-XAM-2XL
- ✅ Yêu cầu thêu: Chi tiết về logo Harry và Sue

## ⚠️ Xử lý sự cố

### Lỗi: "Chưa cấu hình GOOGLE_API_KEY"
- Kiểm tra file `.env` đã tạo đúng chưa
- Kiểm tra API key có đúng không
- Đảm bảo file `.env` nằm cùng thư mục với `app.py`

### Lỗi: "Không thể trích xuất thông tin"
- Kiểm tra kết nối Internet
- Thử dán lại nội dung chat
- Nếu vẫn lỗi, có thể nhập thủ công vào form

### AI trích xuất sai thông tin
- Không sao! Bạn có thể sửa tay bất kỳ trường nào trước khi bấm "Lưu đơn hàng"
- Hệ thống chỉ lưu dữ liệu cuối cùng sau khi bạn kiểm duyệt

## 🎯 Tính năng nổi bật

### Trang "Quản lý Đơn hàng"
- 🤖 **AI tự động trích xuất** thông tin từ chat (Gemini 1.5 Flash)
- 🏷️ **Tự động sinh SKU** theo quy tắc TS-MÀU-SIZE
- 💾 **Lưu trữ session** - dữ liệu không mất khi chuyển trang
- ✏️ **Sửa tay linh hoạt** - AI chỉ hỗ trợ, con người quyết định cuối cùng
- 📊 **Thống kê tự động** - Tổng đơn, doanh thu tự cập nhật

### Trang "Trợ lý AI Design" - MỚI! 🎨
- 🖼️ **Tạo mẫu thêu tự động** từ ảnh pet bằng Nano Banana Pro (Gemini 3 Pro Image)
- 🎯 **Style transfer** - Áp dụng phong cách thêu từ ảnh mẫu
- 💾 **Tải file về** để làm tư liệu vẽ Wilcom
- 🚀 **Tiết kiệm 70% thời gian** thiết kế ban đầu

## 🎨 Hướng dẫn sử dụng Trợ lý AI Design

### Bước chuẩn bị (chỉ làm 1 lần):

1. **Chuẩn bị file style reference:**
   - Chụp ảnh một sản phẩm thêu thực tế có style bạn muốn
   - Đổi tên thành: `style_ref.jpg`
   - Đặt vào thư mục: `c:\app_theu\assets\`

2. **Ví dụ file style tốt:**
   - Ảnh thêu logo pet trên áo
   - Ảnh thêu hình chó/mèo trên gối
   - Ảnh rõ nét, thấy được chi tiết đường chỉ

### Quy trình tạo mẫu thêu (3 bước):

1. **Upload ảnh pet** → Chọn ảnh pet của khách hàng (rõ nét, đầu pet nhìn thẳng)
2. **Gen ảnh** → Bấm nút "🎨 Gen ảnh mẫu thêu" → Đợi 30-60 giây
3. **Tải về** → Bấm "📥 Tải ảnh về máy" → Sử dụng trong Wilcom

### Tips để có kết quả tốt:

**Về ảnh pet:**
- ✅ Rõ nét, độ phân giải cao
- ✅ Đầu pet nhìn thẳng hoặc nghiêng 3/4
- ✅ Nền đơn giản
- ✅ Ánh sáng tốt, màu lông rõ ràng

**Về style reference:**
- ✅ Sử dụng ảnh thêu thực tế
- ✅ Chi tiết rõ ràng
- ✅ Có thể thay đổi bất cứ lúc nào

## 📞 Hỗ trợ

Nếu cần hỗ trợ, vui lòng liên hệ team phát triển.

---

**Phiên bản:** 3.0 - AI Powered + Nano Banana Pro Design
**Cập nhật:** Tháng 1/2025


# Thư mục Assets - Tài nguyên cho Trợ lý AI Design

## 📁 Mục đích

Thư mục này chứa các file tài nguyên cần thiết cho tính năng **Trợ lý AI Design**.

## 📋 Yêu cầu

### File bắt buộc: `style_ref.jpg`

Đây là file ảnh thêu mẫu mà AI sẽ sử dụng làm **style reference** (tham chiếu phong cách) khi tạo thiết kế thêu mới.

**Cách đặt file:**

1. Chụp ảnh một sản phẩm thêu thực tế có style bạn muốn AI học theo
2. Đổi tên file thành: `style_ref.jpg`
3. Đặt file vào thư mục này (`c:\app_theu\assets\`)

**Ví dụ về ảnh thêu mẫu tốt:**
- ✅ Ảnh thêu logo trên áo
- ✅ Ảnh thêu hình pet trên gối
- ✅ Ảnh thêu họa tiết trên khăn
- ✅ Ảnh rõ nét, thấy được chi tiết đường chỉ thêu

**Lưu ý:**
- File phải có tên chính xác: `style_ref.jpg` (chữ thường)
- Định dạng hỗ trợ: JPG/JPEG
- Nên dùng ảnh có độ phân giải trung bình - cao (800x800 trở lên)
- Ảnh càng rõ chi tiết thêu, AI càng học tốt style

## 🎨 Cách hoạt động

Khi nhân viên sử dụng tính năng "Trợ lý AI Design":

1. Upload ảnh pet của khách hàng
2. AI tự động load file `style_ref.jpg` từ thư mục này
3. AI phân tích style thêu từ file mẫu
4. AI tạo thiết kế thêu mới cho pet với **phong cách giống** file mẫu

## 🔄 Thay đổi style

Nếu muốn AI tạo ảnh theo style khác:
- Thay file `style_ref.jpg` bằng ảnh thêu mẫu mới
- Không cần restart app, chỉ cần refresh trang "Trợ lý AI Design"

## ⚠️ Xử lý sự cố

**Lỗi: "Không tìm thấy file style_ref.jpg"**
- Kiểm tra xem file có tên chính xác không (chữ thường)
- Kiểm tra xem file có đúng trong thư mục `assets` không
- Đảm bảo đuôi file là `.jpg` (không phải `.jpeg` hay `.png`)

**App không nhận file:**
- Thử đổi tên file khác rồi đổi lại thành `style_ref.jpg`
- Restart lại Streamlit app
- Kiểm tra quyền đọc file (file không bị lock)

---

**Cập nhật:** 2025


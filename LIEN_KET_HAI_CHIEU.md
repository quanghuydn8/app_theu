# 🔗 Tính năng Liên kết Hai chiều - Quản lý Đơn hàng ↔ AI Design

## 📋 Tổng quan

Tính năng **Liên kết Hai chiều** cho phép nhân viên tạo thiết kế thêu từ **2 nơi**:
1. Trực tiếp trong trang **Quản lý Đơn hàng** (khi xem chi tiết đơn)
2. Trong trang **Trợ lý AI Design** (workflow chuyên nghiệp)

Thiết kế được tạo ra sẽ **tự động lưu vào đơn hàng** và có thể xem/tải về bất cứ lúc nào.

---

## 🎯 Workflow 1: Tạo thiết kế từ Trang Quản lý Đơn hàng

### Bước 1: Vào chi tiết đơn hàng
- Vào trang "📦 Quản lý Đơn hàng"
- Kéo xuống phần "🔍 Tra cứu chi tiết đơn"
- Chọn mã đơn hàng cần làm thiết kế

### Bước 2: Upload ảnh và Gen thiết kế
- Kéo xuống phần "🎨 Thiết kế thêu cho đơn hàng này"
- **Cột trái**: Upload ảnh pet của khách hàng
- Bấm nút "🎨 Gen thiết kế ngay"
- Đợi AI xử lý (30-60 giây)

### Bước 3: Xem kết quả
- **Cột phải**: Ảnh thiết kế sẽ hiện ra ngay
- Bấm "📥 Tải thiết kế về máy" để lưu file
- Thiết kế đã được **lưu tự động** vào đơn hàng này

### Lợi ích:
- ✅ Nhanh chóng - không cần chuyển trang
- ✅ Thiết kế gắn liền với đơn hàng ngay lập tức
- ✅ Phù hợp khi cần làm thiết kế cấp tốc

---

## 🎨 Workflow 2: Tạo thiết kế từ Trang AI Design

### Bước 1: Chọn đơn hàng
- Vào trang "🎨 Trợ lý AI Design"
- Ở phần "📋 Chọn đơn hàng cần làm thiết kế"
- Chọn mã đơn hàng từ dropdown

### Bước 2: Upload và Gen
- **Cột trái**: Upload ảnh pet
- **Cột phải**: Bấm "🎨 Gen ảnh mẫu thêu"
- Đợi AI xử lý

### Bước 3: Tự động lưu vào đơn hàng
- Ảnh thiết kế hiện ra
- Hệ thống tự động cập nhật vào đơn hàng đã chọn
- Thông báo: "✅ Đã cập nhật thiết kế cho đơn hàng [Mã đơn]"

### Lợi ích:
- ✅ Giao diện chuyên nghiệp, layout 2 cột
- ✅ Có thể xem style reference (nếu cần)
- ✅ Phù hợp khi làm nhiều thiết kế liên tiếp

---

## 💾 Lưu trữ & Bảo toàn dữ liệu

### Tự động lưu CSV
- Mỗi khi tạo đơn hàng mới → Lưu vào `don_hang.csv`
- Mỗi khi cập nhật thiết kế → Lưu vào `don_hang.csv`
- File CSV chứa toàn bộ dữ liệu bao gồm cả ảnh thiết kế (dạng bytes)

### Tải lại khi F5
- Khi refresh trang → Tự động load từ `don_hang.csv`
- Tất cả đơn hàng và thiết kế đều được giữ nguyên
- Không mất dữ liệu khi đóng/mở lại app

### Vị trí file:
```
c:\app_theu\
├── app.py
├── don_hang.csv          ← File lưu trữ chính
├── assets/
│   └── style_ref.jpg
```

---

## 🔍 Xem thiết kế đã lưu

### Cách 1: Trong phần Chi tiết đơn hàng
1. Vào trang "📦 Quản lý Đơn hàng"
2. Chọn đơn hàng trong "🔍 Tra cứu chi tiết đơn"
3. Kéo xuống phần "🎨 Thiết kế thêu"
4. **Cột phải** sẽ hiển thị ảnh thiết kế nếu đã có
5. Bấm "📥 Tải thiết kế về máy" để download

### Cách 2: Trong trang AI Design
1. Vào trang "🎨 Trợ lý AI Design"
2. Chọn mã đơn hàng đã có thiết kế
3. Nếu đơn đó đã có thiết kế, **cột phải** sẽ hiển thị ngay

---

## 📊 Cấu trúc dữ liệu

### DataFrame chính (st.session_state.df_don_hang):
```python
{
    "Mã đơn hàng": "DH001",
    "Khách hàng": "Nguyễn Văn A",
    "Sản phẩm": "Áo thun thêu logo",
    "Số lượng": 50,
    "Mã SKU": "TS-DEN-M",
    "Trạng thái": "Đang thiết kế",
    "Ngày tạo": "01/01/2025",
    "Tổng tiền": "5,000,000đ",
    "Anh_Design": b'\x89PNG\r\n...'  ← Dữ liệu ảnh (bytes)
}
```

### File CSV (don_hang.csv):
- Lưu tất cả thông tin đơn hàng
- Cột `Anh_Design` chứa dữ liệu ảnh dạng bytes
- Encoding: UTF-8 with BOM

---

## 🎯 Use Cases thực tế

### Use Case 1: Nhân viên Sales nhận đơn mới
1. Nhận chat chốt đơn từ khách
2. Vào trang "Quản lý Đơn hàng" → Tạo đơn mới (AI tự động điền)
3. Khách gửi ảnh pet → Upload ngay trong phần chi tiết đơn
4. Gen thiết kế → Gửi preview cho khách duyệt
5. Khách đồng ý → Tải file thiết kế về làm Wilcom

### Use Case 2: Team Design làm hàng loạt
1. Vào trang "Trợ lý AI Design"
2. Chọn đơn DH001 → Upload ảnh pet → Gen → Lưu
3. Chọn đơn DH002 → Upload ảnh pet → Gen → Lưu
4. Chọn đơn DH003 → Upload ảnh pet → Gen → Lưu
5. Sau đó vào "Quản lý Đơn hàng" → Xem từng đơn → Tải tất cả thiết kế về

### Use Case 3: Kiểm tra lại thiết kế cũ
1. Khách hàng gọi lại hỏi về đơn DH005 từ tuần trước
2. Vào "Tra cứu chi tiết đơn" → Chọn DH005
3. Ảnh thiết kế hiện ra ngay → Gửi lại cho khách
4. Hoặc tải về để xem chi tiết

---

## ⚠️ Lưu ý quan trọng

### File don_hang.csv có thể lớn
- Mỗi ảnh thiết kế ~ 1-5 MB
- 100 đơn hàng có thiết kế ~ 100-500 MB
- Nên sao lưu định kỳ

### Backup dữ liệu
- Copy file `don_hang.csv` ra nơi khác định kỳ
- Hoặc commit vào Git (nếu có)
- Tránh mất dữ liệu khi sửa code

### Xóa thiết kế cũ
- Hiện tại chưa có chức năng xóa thiết kế
- Nếu muốn làm lại, chỉ cần gen mới (sẽ ghi đè)
- Ảnh cũ sẽ bị thay thế bằng ảnh mới

---

## 🚀 Lợi ích tổng thể

✅ **Tích hợp chặt chẽ**: Thiết kế gắn với đơn hàng, không bao giờ lạc  
✅ **Linh hoạt**: 2 cách tạo thiết kế, phù hợp mọi workflow  
✅ **Tự động lưu**: Không cần nhấn Save, không sợ quên  
✅ **Bảo toàn dữ liệu**: File CSV backup tự động, F5 không mất dữ liệu  
✅ **Truy xuất dễ dàng**: Xem lại thiết kế cũ bất cứ lúc nào  

---

**Phiên bản:** 3.1 - Liên kết Hai chiều  
**Cập nhật:** Tháng 1/2025


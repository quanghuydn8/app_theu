# 🔧 Cập nhật Phiên bản 3.2 - Sửa lỗi UnicodeDecodeError

## ❌ Vấn đề trước đây (v3.1)

### Lỗi:
```
UnicodeDecodeError: 'utf-8' codec can't decode bytes...
```

### Nguyên nhân:
- Lưu dữ liệu ảnh (bytes) trực tiếp vào file CSV
- CSV không được thiết kế để lưu binary data
- Khi đọc lại CSV → Lỗi decode

## ✅ Giải pháp (v3.2)

### Thay đổi cách lưu trữ:

**Trước (v3.1):**
```
CSV: Anh_Design = b'\x89PNG\r\n...' (bytes)
                    ↓
            Lỗi UnicodeDecodeError
```

**Sau (v3.2):**
```
Ảnh thiết kế → Lưu file PNG → saved_designs/design_DH001.png
                                        ↓
CSV: Anh_Design = "saved_designs/design_DH001.png" (path string)
                                        ↓
                            Không còn lỗi ✅
```

---

## 🆕 Thay đổi chính

### 1. Tạo thư mục `saved_designs/`
```
c:\app_theu\
├── app.py
├── don_hang.csv
├── saved_designs/           ← Thư mục mới
│   ├── design_DH001.png
│   ├── design_DH002.png
│   └── ...
```

### 2. Hàm mới: `luu_anh_design()`
```python
def luu_anh_design(image_data, ma_don_hang):
    """
    Lưu ảnh thiết kế thành file PNG
    Tham số:
        - image_data: bytes - Dữ liệu ảnh
        - ma_don_hang: str - Mã đơn hàng (DH001, DH002, ...)
    Trả về: str - Đường dẫn file (saved_designs/design_DH001.png)
    """
```

**Chức năng:**
- Nhận bytes ảnh từ AI Nano Banana Pro
- Tạo thư mục `saved_designs` nếu chưa có
- Lưu ảnh thành file: `design_{ma_don_hang}.png`
- Trả về đường dẫn file

### 3. Hàm mới: `tai_anh_design()`
```python
def tai_anh_design(file_path):
    """
    Tải ảnh từ file path
    Tham số: file_path - Đường dẫn đến file ảnh
    Trả về: PIL Image hoặc None
    """
```

**Chức năng:**
- Kiểm tra file có tồn tại không
- Load ảnh thành PIL Image
- Trả về để hiển thị trong Streamlit

### 4. Cập nhật logic lưu thiết kế

**Nơi 1: Trang Quản lý Đơn hàng**
```python
# Trước:
st.session_state.df_don_hang.at[idx, 'Anh_Design'] = image_data

# Sau:
file_path = luu_anh_design(image_data, ma_don_chon)
st.session_state.df_don_hang.at[idx, 'Anh_Design'] = file_path
```

**Nơi 2: Trang AI Design**
```python
# Trước:
st.session_state.df_don_hang.at[idx, 'Anh_Design'] = image_data

# Sau:
file_path = luu_anh_design(image_data, ma_don_chon_design)
st.session_state.df_don_hang.at[idx, 'Anh_Design'] = file_path
```

### 5. Cập nhật hiển thị ảnh

**Trước:**
```python
design_image = Image.open(io.BytesIO(don_hang['Anh_Design']))
```

**Sau:**
```python
design_image = tai_anh_design(don_hang['Anh_Design'])
```

### 6. Ẩn cột 'Anh_Design' trong bảng

**Trước:**
- Cột `Anh_Design` hiển thị trong bảng (gây lỗi)

**Sau:**
```python
# Tạo DataFrame hiển thị (ẩn cột Anh_Design)
df_display = df.drop(columns=['Anh_Design'], errors='ignore')
st.dataframe(df_display, ...)
```

- Cột `Anh_Design` bị ẩn
- Chỉ dùng để load ảnh trong phần chi tiết

---

## 📊 Cấu trúc dữ liệu mới

### DataFrame:
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
    "Anh_Design": "saved_designs/design_DH001.png"  ← String path
}
```

### File CSV:
```csv
Mã đơn hàng,Khách hàng,Sản phẩm,Số lượng,Mã SKU,Trạng thái,Ngày tạo,Tổng tiền,Anh_Design
DH001,Nguyễn Văn A,Áo thun thêu logo,50,TS-DEN-M,Đang thiết kế,01/01/2025,"5,000,000đ",saved_designs/design_DH001.png
```

### File hệ thống:
```
saved_designs/
├── design_DH001.png  (1.2 MB)
├── design_DH002.png  (1.5 MB)
└── design_DH003.png  (0.9 MB)
```

---

## 🚀 Lợi ích của thay đổi

✅ **Không còn lỗi UnicodeDecodeError**
- CSV chỉ chứa text, không còn bytes
- Đọc/ghi CSV hoàn toàn ổn định

✅ **Dễ quản lý**
- Ảnh là file riêng biệt, dễ xem trực tiếp
- Có thể mở ảnh bằng Windows Explorer
- Có thể backup/restore độc lập

✅ **Linh hoạt hơn**
- Có thể xóa ảnh cũ không cần
- Có thể share ảnh qua email/chat
- Có thể chỉnh sửa ảnh bằng Photoshop nếu muốn

✅ **Hiệu suất tốt hơn**
- CSV nhẹ hơn (không chứa bytes ảnh)
- Load/save nhanh hơn
- Không giới hạn kích thước ảnh

---

## ⚠️ Breaking Changes (Lưu ý quan trọng)

### File CSV cũ không tương thích
- File `don_hang.csv` từ v3.1 chứa bytes → Không đọc được
- **Giải pháp**: Xóa file CSV cũ, app sẽ tạo mới

### Dữ liệu cũ bị mất
- Các đơn hàng cũ sẽ bị reset
- Các thiết kế cũ bị mất (vì lưu dạng bytes không restore được)
- **Giải pháp**: Backup trước khi cập nhật (nếu có dữ liệu quan trọng)

### Cần tạo thư mục mới
- Thư mục `saved_designs/` cần được tạo
- App sẽ tự động tạo nếu chưa có

---

## 📝 Checklist Cập nhật

### Bước 1: Backup (nếu cần)
- [ ] Backup file `don_hang.csv` (nếu có dữ liệu quan trọng)
- [ ] Backup thư mục `saved_designs/` (nếu có)

### Bước 2: Xóa dữ liệu cũ
- [ ] Xóa file `don_hang.csv` cũ (chứa bytes gây lỗi)
- [ ] Hoặc di chuyển sang thư mục backup

### Bước 3: Cập nhật code
- [x] File `app.py` đã được cập nhật
- [x] Thêm hàm `luu_anh_design()`
- [x] Thêm hàm `tai_anh_design()`
- [x] Cập nhật logic lưu/tải ảnh

### Bước 4: Tạo thư mục
- [x] Tạo thư mục `saved_designs/`
- [x] Tạo file `saved_designs/README.md`

### Bước 5: Chạy thử
- [ ] Chạy app: `streamlit run app.py`
- [ ] Tạo đơn hàng mới
- [ ] Gen thiết kế
- [ ] Kiểm tra ảnh trong `saved_designs/`
- [ ] Kiểm tra hiển thị ảnh trong chi tiết đơn
- [ ] F5 refresh → Kiểm tra dữ liệu còn

---

## 🔄 Migration Guide (Di chuyển dữ liệu)

Nếu bạn có dữ liệu quan trọng từ v3.1:

### Cách 1: Tạo lại thủ công
1. Lưu thông tin đơn hàng ra file Excel/Note
2. Cập nhật lên v3.2
3. Nhập lại đơn hàng thủ công
4. Gen lại thiết kế

### Cách 2: Chạy script migration (nếu có)
- Hiện tại chưa có script tự động
- Nếu cần, có thể viết script Python để:
  - Đọc CSV cũ
  - Extract bytes ảnh
  - Lưu thành file PNG
  - Tạo CSV mới với path

---

## 📞 Hỗ trợ

Nếu gặp vấn đề khi cập nhật:
1. Kiểm tra lại file `don_hang.csv` đã xóa chưa
2. Kiểm tra thư mục `saved_designs/` đã được tạo chưa
3. Chạy lại app và kiểm tra console có lỗi không
4. Liên hệ team phát triển nếu vẫn lỗi

---

**Phiên bản:** 3.2 - File-based Storage  
**Ngày cập nhật:** Tháng 1/2026  
**Breaking Change:** ⚠️ Yes - CSV cũ không tương thích


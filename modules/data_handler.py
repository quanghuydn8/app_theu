import pandas as pd
import os
import random
from datetime import datetime, timedelta
from PIL import Image

# Định nghĩa các thư mục lưu trữ tập trung
DIR_DESIGNS = "saved_designs"
DIR_PETS = "saved_pets"
CSV_FILE = "don_hang.csv"

def check_file_exists(file_path):
    if file_path and isinstance(file_path, str) and pd.notna(file_path):
        return os.path.exists(file_path)
    return False

def luu_anh_pet(image_file, ma_don_hang):
    try:
        if not os.path.exists(DIR_PETS):
            os.makedirs(DIR_PETS)
        file_name = f"pet_{ma_don_hang}.png"
        file_path = os.path.join(DIR_PETS, file_name)
        if isinstance(image_file, Image.Image):
            image_file.save(file_path, 'PNG')
        else:
            img = Image.open(image_file)
            img.save(file_path, 'PNG')
        return file_path
    except Exception as e:
        return None

def luu_anh_design(image_data, ma_don_hang):
    try:
        if not os.path.exists(DIR_DESIGNS):
            os.makedirs(DIR_DESIGNS)
        file_name = f"design_{ma_don_hang}.png"
        file_path = os.path.join(DIR_DESIGNS, file_name)
        with open(file_path, 'wb') as f:
            f.write(image_data)
        return file_path
    except Exception:
        return None

def tai_anh_design(file_path):
    try:
        if file_path and os.path.exists(file_path):
            return Image.open(file_path)
        return None
    except Exception:
        return None

def luu_du_lieu_csv(df):
    try:
        df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
        return True
    except Exception:
        return False

def tai_du_lieu_csv():
    try:
        if os.path.exists(CSV_FILE):
            df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
            if 'Anh_Pet' not in df.columns: df['Anh_Pet'] = None
            if 'Anh_Design' not in df.columns: df['Anh_Design'] = None
            return df
        return None
    except Exception:
        return None

def tao_du_lieu_mau():
    trang_thai_list = ["New", "Đã xác nhận", "Đang thiết kế", "Chờ duyệt thiết kế", "Đã duyệt thiết kế", 
                      "Đang sản xuất", "Hoàn thành sản xuất", "Đang đóng gói", "Sẵn sàng giao hàng", 
                      "Đang giao hàng", "Đã gửi vận chuyển"]
    so_luong_don = len(trang_thai_list)
    ten_mau = ["Nguyễn Văn A", "Trần Thị B", "Lê Văn C", "Phạm Thị D", "Hoàng Văn E"]
    san_pham_mau = ["Áo thun thêu logo", "Khăn tay thêu", "Mũ lưỡi trai thêu"]
    mau_sac_list = ["DO", "TRANG", "DEN", "XANH"]
    size_list = ["S", "M", "L", "XL"]
    
    data = {
        "Mã đơn hàng": [f"DH{str(i).zfill(3)}" for i in range(1, so_luong_don + 1)],
        "Khách hàng": [ten_mau[i % len(ten_mau)] for i in range(so_luong_don)],
        "Sản phẩm": [san_pham_mau[i % len(san_pham_mau)] for i in range(so_luong_don)],
        "Số lượng": [random.randint(10, 200) for _ in range(so_luong_don)],
        "Mã SKU": [f"TS-{random.choice(mau_sac_list)}-{random.choice(size_list)}" for _ in range(so_luong_don)],
        "Trạng thái": trang_thai_list,
        "Ngày tạo": [(datetime.now() - timedelta(days=i*2)).strftime("%d/%m/%Y") for i in range(so_luong_don)],
        "Tổng tiền": [f"{random.randint(50, 5000) * 10000:,}đ".replace(",", ",") for _ in range(so_luong_don)],
        "Anh_Pet": [None for _ in range(so_luong_don)],
        "Anh_Design": [None for _ in range(so_luong_don)]
    }
    return pd.DataFrame(data)

def tao_chi_tiet_don_hang(df):
    chi_tiet = {}
    for idx, row in df.iterrows():
        ma_don = row['Mã đơn hàng']
        chi_tiet[ma_don] = {
            "Tên khách hàng": row['Khách hàng'],
            "Số điện thoại": f"09{random.randint(10000000, 99999999)}",
            "Địa chỉ": "123 Đường Lê Lợi, Quận 1, TP.HCM",
            "Yêu cầu thêu": "Thêu logo công ty ở giữa ngực áo"
        }
    return chi_tiet

def sync_images_with_dataframe(df):
    updated = False
    for idx, row in df.iterrows():
        ma_don = row['Mã đơn hàng']
        pet_path = os.path.join(DIR_PETS, f"pet_{ma_don}.png")
        if os.path.exists(pet_path) and (pd.isna(row['Anh_Pet']) or row['Anh_Pet'] is None):
            df.at[idx, 'Anh_Pet'] = pet_path
            updated = True
        design_path = os.path.join(DIR_DESIGNS, f"design_{ma_don}.png")
        if os.path.exists(design_path) and (pd.isna(row['Anh_Design']) or row['Anh_Design'] is None):
            df.at[idx, 'Anh_Design'] = design_path
            updated = True
    if updated:
        luu_du_lieu_csv(df)
        return True
    return False


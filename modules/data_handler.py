import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from PIL import Image
import io

# 1. Setup Supabase
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    print(f"❌ Lỗi config Supabase: {e}")
    supabase = None

STATUS_FILE = "trang_thai.csv"

# --- DATABASE FUNCTIONS ---

def kiem_tra_ket_noi():
    try:
        supabase.table("orders").select("ma_don").limit(1).execute()
        return True
    except:
        return False

def fetch_all_orders():
    try:
        response = supabase.table("orders").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        print(f"Lỗi fetch data: {e}")
        return pd.DataFrame()

def get_order_details(ma_don):
    try:
        order = supabase.table("orders").select("*").eq("ma_don", ma_don).single().execute()
        # Lấy items và sắp xếp theo ID để tránh nhảy thứ tự
        items = supabase.table("order_items").select("*").eq("order_id", ma_don).order("id").execute()
        return order.data, items.data
    except:
        return None, []

def save_full_order(order_data, items_list):
    try:
        supabase.table("orders").insert(order_data).execute()
        for item in items_list:
            item['order_id'] = order_data['ma_don']
        if items_list:
            supabase.table("order_items").insert(items_list).execute()
        return True
    except Exception as e:
        print(f"Lỗi save: {e}")
        return False

def update_order_status(ma_don, new_status):
    try:
        supabase.table("orders").update({"trang_thai": new_status}).eq("ma_don", ma_don).execute()
        return True
    except:
        return False

# --- CONFIG HELPERS ---

def tai_danh_sach_trang_thai():
    if os.path.exists(STATUS_FILE):
        return pd.read_csv(STATUS_FILE)
    return pd.DataFrame({"Trạng thái": ["New", "Hoàn thành"], "Màu sắc": ["#808080", "#4CAF50"]})

def luu_danh_sach_trang_thai(df):
    df.to_csv(STATUS_FILE, index=False)
    return True

# --- CLOUD STORAGE FUNCTIONS (NEW) ---

def compress_image(image_file, max_width=1024):
    """
    Hàm nén ảnh: Resize lại và giảm chất lượng xuống mức hợp lý
    """
    try:
        # Mở ảnh bằng PIL
        img = Image.open(image_file)
        
        # Convert sang RGB nếu là ảnh PNG/RGBA để lưu được JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Resize nếu ảnh quá to (giữ nguyên tỷ lệ)
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
        # Lưu vào bộ nhớ đệm (RAM) dưới dạng JPEG
        output_io = io.BytesIO()
        # quality=85 là mức cân bằng hoàn hảo giữa dung lượng và độ nét
        img.save(output_io, format='JPEG', quality=85, optimize=True) 
        output_io.seek(0)
        
        return output_io.getvalue()
    except Exception as e:
        print(f"Lỗi nén ảnh: {e}")
        return None # Trả về None nếu lỗi, để code dùng ảnh gốc

def upload_image_to_supabase(file_data, file_name, folder="items"):
    try:
        bucket_name = "images"
        file_path = f"{folder}/{file_name}"
        
        # --- BƯỚC 1: NÉN ẢNH ---
        # Nếu file_data là file upload từ Streamlit
        compressed_data = compress_image(file_data)
        
        # Nếu nén lỗi (hoặc file không phải ảnh), dùng dữ liệu gốc
        if compressed_data is None:
            if hasattr(file_data, "getvalue"):
                final_data = file_data.getvalue()
            else:
                final_data = file_data
            mime = "image/png" # Mặc định
        else:
            final_data = compressed_data
            mime = "image/jpeg" # Sau khi nén luôn là JPEG

        # --- BƯỚC 2: UPLOAD ---
        supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=final_data,
            file_options={"content-type": mime, "upsert": "true"}
        )
        
        # --- BƯỚC 3: TRẢ VỀ LINK ---
        # Thêm timestamp ?t=... để tránh trình duyệt cache ảnh cũ khi update
        import time
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
        return f"{public_url}?t={int(time.time())}"

    except Exception as e:
        st.error(f"❌ Lỗi Upload: {e}")
        return None

    except Exception as e:
        # --- DÒNG CODE DEBUG THẦN THÁNH ---
        st.error(f"❌ BUG REPORT: {str(e)}") # In lỗi ra màn hình
        print(f"❌ Lỗi chi tiết: {e}")       # In lỗi ra terminal
        return None

def update_item_image(item_id, image_url, column_name="img_main"):
    """Cập nhật link ảnh vào bảng order_items cho từng sản phẩm"""
    try:
        supabase.table("order_items").update({column_name: image_url}).eq("id", item_id).execute()
        return True
    except Exception as e:
        print(f"❌ Lỗi cập nhật DB: {e}")
        return False

# ... (Các hàm cũ giữ nguyên) ...

def update_order_info(ma_don, update_data):
    """
    Cập nhật thông tin chung của đơn hàng (Khách, Tiền, Shop, Trạng thái...)
    """
    try:
        supabase.table("orders").update(update_data).eq("ma_don", ma_don).execute()
        return True
    except Exception as e:
        print(f"❌ Lỗi update đơn: {e}")
        return False
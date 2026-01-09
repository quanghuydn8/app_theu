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

# DANH SÁCH TRẠNG THÁI CỐ ĐỊNH
ORDER_STATUSES = [
    "Mới", "Đã xác nhận", "Chờ sản xuất", "Đang thiết kế", 
    "Chờ duyệt thiết kế", "Đã duyệt thiết kế", "Đang sản xuất", 
    "Đổi/sửa/đền", "Đã gửi vận chuyển", "Hoàn thành", "Hủy"
]

STATUS_DONE = ["Hoàn thành", "Done", "Đã giao", "Completed", "Success"]
STATUS_CANCEL = ["Đã hủy", "Cancelled", "Hủy", "Fail", "Aborted"]

# DANH SÁCH TAG SẢN XUẤT GỢI Ý
PRODUCTION_TAGS = [
    "Thêu",
    "May",
    "Chờ phôi",
    "Chờ thu gom",
    "Thiếu file tk"
]

# --- DATABASE FUNCTIONS ---

def kiem_tra_ket_noi():
    try:
        supabase.table("orders").select("ma_don").limit(1).execute()
        return True
    except:
        return False

def fetch_all_orders():
    print("--- DEBUG: Đang lấy dữ liệu từ Supabase ---")
    try:
        response = supabase.table("orders").select("*").order("created_at", desc=True).execute()
        data = response.data
        print(f"--- DEBUG: Lấy được {len(data)} dòng dữ liệu ---")
        return pd.DataFrame(data)
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

def lay_hoac_tao_khach_hang(ten_khach, sdt, dia_chi, shop, facebook_id=None):
    """
    Kiểm tra SĐT đã tồn tại chưa:
    - Nếu có: Trả về ID, update thông tin mới (bao gồm facebook_id nếu có).
    - Nếu chưa: Tạo mới và trả về ID.
    """
    try:
        # 1. Tìm khách hàng theo SĐT
        response = supabase.table("khach_hang").select("*").eq("sdt", sdt).execute()
        
        if response.data:
            # Khách đã tồn tại -> Update thông tin & Tăng số đơn
            khach = response.data[0]
            khach_id = khach['id']
            so_don_cu = khach.get('so_don_hang', 0) or 0
            
            update_data = {
                "ho_ten": ten_khach, # Cập nhật tên mới nhất (nếu thay đổi)
                "dia_chi": dia_chi,  # Cập nhật địa chỉ mới nhất
                "so_don_hang": so_don_cu + 1,
                "nguon_shop": shop   # Cập nhật shop gần nhất
            }
            if facebook_id:
                update_data["facebook_id"] = facebook_id
                
            supabase.table("khach_hang").update(update_data).eq("id", khach_id).execute()
            return khach_id
            
        else:
            # Khách chưa tồn tại -> Tạo mới
            new_customer = {
                "ho_ten": ten_khach,
                "sdt": sdt,
                "dia_chi": dia_chi,
                "nguon_shop": shop,
                "so_don_hang": 1
            }
            if facebook_id:
                new_customer["facebook_id"] = facebook_id
                
            res = supabase.table("khach_hang").insert(new_customer).execute()
            if res.data:
                return res.data[0]['id']
            return None
            
    except Exception as e:
        print(f"❌ Lỗi xử lý khách hàng: {e}")
        return None

def lay_danh_sach_khach_hang(search_term=None):
    """Lấy danh sách khách hàng, có hỗ trợ tìm kiếm"""
    try:
        query = supabase.table("khach_hang").select("*").order("created_at", desc=True) # Sort by recently created
        
        if search_term:
            # Tìm theo SĐT hoặc Tên (dùng ilike cho tên)
            # Cú pháp OR trong Supabase: .or_("col1.op.val,col2.op.val")
            query = query.or_(f"sdt.ilike.%{search_term}%,ho_ten.ilike.%{search_term}%")
        
        response = query.execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        return pd.DataFrame()

def lay_lich_su_khach(khach_hang_id):
    """Lấy danh sách đơn hàng của một khách"""
    try:
        response = supabase.table("orders").select("*").eq("khach_hang_id", khach_hang_id).order("created_at", desc=True).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        return pd.DataFrame()

def save_full_order(order_data, items_list):
    try:
        # BƯỚC 1: XỬ LÝ THÔNG TIN KHÁCH HÀNG (CRM)
        # Trích xuất thông tin từ order_data
        ten_khach = order_data.get('ten_khach', '')
        sdt = order_data.get('sdt', '')
        dia_chi = order_data.get('dia_chi', '')
        shop = order_data.get('shop', '')
        facebook_id = order_data.get('facebook_id', None) # Lấy facebook_id từ order_data
        
        khach_id = None
        if sdt: # Chỉ xử lý nếu có SĐT
            khach_id = lay_hoac_tao_khach_hang(ten_khach, sdt, dia_chi, shop, facebook_id)
        
        # Thêm khach_hang_id vào order_data trước khi lưu
        if khach_id:
            order_data['khach_hang_id'] = khach_id
        
        # BƯỚC 2: TẠO ĐƠN HÀNG
        supabase.table("orders").insert(order_data).execute()
        
        # BƯỚC 3: LƯU SẢN PHẨM
        for item in items_list:
            item['order_id'] = order_data['ma_don']
        
        if items_list:
            supabase.table("order_items").insert(items_list).execute()
            
        # BƯỚC 4: CẬP NHẬT TỔNG CHI TIÊU KHÁCH HÀNG
        if khach_id:
            try:
                # Tính tổng tiền đơn vừa tạo
                tong_tien_don = int(order_data.get('thanh_tien', 0))
                
                # Gọi RPC (Stored Procedure) hoặc query lấy tổng cũ
                # Cách đơn giản: Lấy tổng hiện tại + đơn mới
                k_res = supabase.table("khach_hang").select("tong_tieu").eq("id", khach_id).single().execute()
                if k_res.data:
                    tong_cu = k_res.data.get('tong_tieu', 0) or 0
                    supabase.table("khach_hang").update({"tong_tieu": tong_cu + tong_tien_don}).eq("id", khach_id).execute()
            except Exception as e:
                print(f"⚠️ Lỗi update tổng tiêu: {e}")

        return True
    except Exception as e:
        print(f"Lỗi save: {e}")
        return False

def sync_all_customer_totals():
    """Đồng bộ lại tổng tiêu, số đơn hàng và địa chỉ cho tất cả khách hàng từ bảng orders"""
    try:
        # 1. Lấy tất cả orders
        all_orders = fetch_all_orders()
        if all_orders.empty: return False
        
        # 2. Group by khach_hang_id
        # - Sum thanh_tien -> total spent
        # - Count ma_don -> total orders
        # - Last dia_chi -> latest address
        grouped = all_orders.groupby("khach_hang_id").agg({
            "thanh_tien": "sum",
            "ma_don": "count",
            "dia_chi": "last" # Lấy địa chỉ từ đơn mới nhất
        }).reset_index()
        
        # 3. Update từng khách hàng
        count = 0
        for _, row in grouped.iterrows():
            kid = row['khach_hang_id']
            if pd.isna(kid): continue
            
            supabase.table("khach_hang").update({
                "tong_tieu": int(row['thanh_tien']),
                "so_don_hang": int(row['ma_don']),
                "dia_chi": row['dia_chi']
            }).eq("id", int(kid)).execute()
            count += 1
            
        print(f"Đã đồng bộ {count} khách hàng.")
        return True
    except Exception as e:
        print(f"Lỗi sync: {e}")
        return False

def update_order_status(ma_don, new_status):
    try:
        supabase.table("orders").update({"trang_thai": new_status}).eq("ma_don", ma_don).execute()
        return True
    except:
        return False

# --- CONFIG HELPERS ---

def tai_danh_sach_trang_thai():
    return pd.DataFrame({"Trạng thái": ORDER_STATUSES})


# --- CLOUD STORAGE FUNCTIONS (NEW) ---

def compress_image(image_file, max_width=1024):
    """
    Hàm nén ảnh: Resize lại và giảm chất lượng xuống mức hợp lý
    """
    try:
        # Nếu là bytes, bọc vào BytesIO để PIL có thể đọc được
        if isinstance(image_file, bytes):
            image_file = io.BytesIO(image_file)
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
        print(f"❌ Lỗi Upload: {e}")
        return None

    except Exception as e:
        # --- DÒNG CODE DEBUG THẦN THÁNH ---
        print(f"❌ BUG REPORT: {str(e)}") # In lỗi ra màn hình
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

def update_item_field(item_id, field_name, new_value):
    """Cập nhật một trường bất kỳ của item trong bảng order_items"""
    try:
        supabase.table("order_items").update({field_name: new_value}).eq("id", item_id).execute()
        return True
    except Exception as e:
        print(f"❌ Lỗi cập nhật field {field_name}: {e}")
        return False

def mark_order_as_printed(ma_don):
    """Đánh dấu đơn hàng đã được in phiếu"""
    try:
        supabase.table("orders").update({"da_in": True}).eq("ma_don", ma_don).execute()
        return True
    except Exception as e:
        print(f"❌ Lỗi mark_order_as_printed: {e}")
        return False

def upload_multiple_files_to_supabase(files, item_id):
    """
    Upload nhiều file thiết kế cùng lúc lên Supabase.
    
    Args:
        files: List các file upload từ Streamlit
        item_id: ID của item trong order_items
    
    Returns:
        String chứa các URL nối với nhau bằng dấu chấm phẩy " ; "
    """
    try:
        uploaded_urls = []
        
        for idx, file_data in enumerate(files):
            # Tạo tên file unique
            file_name = f"item_{item_id}_design_{idx}_{file_data.name}"
            
            # Upload từng file
            url = upload_image_to_supabase(file_data, file_name, folder="designs")
            
            if url:
                uploaded_urls.append(url)
            else:
                print(f"⚠️ Không upload được file {file_data.name}")
        
        # Nối các URL bằng dấu " ; "
        if uploaded_urls:
            return " ; ".join(uploaded_urls)
        else:
            return None
            
    except Exception as e:
        print(f"❌ Lỗi upload multiple files: {e}")
        return None

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
# ==============================================================================
# AUTHENTICATION FUNCTIONS
# ==============================================================================

def login_user(email, password):
    """
    Đăng nhập bằng Email/Pass qua Supabase Auth
    Trả về: User Object nếu thành công, None nếu thất bại
    """
    try:
        # Gọi hàm sign_in_with_password của Supabase
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        # Nếu có user và session nghĩa là đăng nhập thành công
        if response.user and response.session:
            return response.user
            
        return None
    except Exception as e:
        print(f"❌ Lỗi đăng nhập: {str(e)}")
        return None

import google.generativeai as genai
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont # Thêm thư viện xử lý ảnh
import io

# Load biến môi trường
load_dotenv()

def configure_ai():
    # Ưu tiên lấy từ .env, dự phòng lấy từ st.secrets (khi deploy)
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets["GOOGLE_API_KEY"]
        except:
            pass

    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def xuly_ai_gemini(text_input):
    """
    Hàm trích xuất thông tin đơn hàng và xác định Shop (Line sản phẩm).
    OUTPUT: Trả về TUPLE (Mapped_Data_Dict, Raw_String)
    """
    if not configure_ai(): 
        return None, "Lỗi: Chưa cấu hình Google API Key"
    
    try:
        today_str = datetime.now().strftime("%d/%m/%Y")
        
        # PROMPT MỚI: Tách mảng sản phẩm & Nhận diện Shop
        system_instruction = f"""
        Hôm nay là: {today_str}.
        Nhiệm vụ: Phân tích đoạn chat thành JSON và xác định mã SHOP.
        
        1. XÁC ĐỊNH SHOP (Quan trọng):
           Nhân viên sẽ ghi mã shop trong đoạn chat. Hãy bắt các từ khóa sau:
           - "TGTD" hoặc "TGTĐ" -> shop: "TGTĐ"
           - "Inside" hoặc "IS"   -> shop: "Inside"
           - "Lanh Canh" hoặc "LC" -> shop: "Lanh Canh"
           - Nếu không tìm thấy mã, mặc định là: "Inside"
        
        2. QUY TẮC CHUNG:
           - Tách từng sản phẩm vào mảng "products".
           - Tiền tệ: Chỉ lấy số nguyên.
           - Ngày trả: Tính ra YYYY-MM-DD.
        
        OUTPUT FORMAT (JSON):
        {{
            "customer_info": {{
                "ten_khach": "...",
                "sdt": "...",
                "dia_chi": "...",
                "ngay_tra": "YYYY-MM-DD",
                "shop": "TGTĐ" | "Inside" | "Lanh Canh",
                "tong_tien": 0,
                "da_coc": 0,
                "httt": "Ship COD",
                "van_chuyen": "Thường",
                "ghi_chu_chung": "..."
            }},
            "products": [
                {{
                    "ten_sp": "Tên SP 1",
                    "mau": "Màu",
                    "size": "Size",
                    "kieu_theu": "...",
                    "ghi_chu_sp": "..."
                }},
                {{ "ten_sp": "Tên SP 2", ... }}
            ]
        }}
        """
        
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash', 
            system_instruction=system_instruction,
            generation_config={"response_mime_type": "application/json"}
        )
        
        full_prompt = f"Phân tích đơn này: {text_input}"
        response = model.generate_content(full_prompt)
        raw_text = response.text 
        
        if raw_text:
            data = json.loads(raw_text)
            
            # --- FIX LỖI: AI trả về List thay vì Dict ---
            if isinstance(data, list):
                if len(data) > 0:
                    data = data[0]
                else:
                    return None, "AI trả về danh sách rỗng"
            # -------------------------------------------
            
            # Lấy dữ liệu an toàn
            cust = data.get("customer_info", {})
            products = data.get("products", [])
            
            # Fallback nếu AI trả về cấu trúc cũ
            if not cust and not products:
                 cust = data
                 products = [{
                     "ten_sp": data.get("san_pham", ""),
                     "mau": data.get("mau_sac", ""),
                     "size": data.get("size", ""),
                     "kieu_theu": data.get("yeu_cau_theu", ""),
                     "ghi_chu_sp": data.get("ghi_chu", "")
                 }]
            
            # Chuẩn hóa tên Shop (để chắc chắn mapping đúng 100% với Code UI)
            raw_shop = cust.get("shop", "Inside")
            final_shop = "Inside" # Mặc định
            if raw_shop in ["TGTĐ", "TGTD"]: final_shop = "TGTĐ"
            elif raw_shop in ["Inside", "IS"]: final_shop = "Inside"
            elif raw_shop in ["Lanh Canh", "LC"]: final_shop = "Lanh Canh"

            # Mapping dữ liệu trả về cho UI
            mapped_data = {
                # Thông tin khách
                "ten_khach_hang": cust.get("ten_khach", ""),
                "so_dien_thoai": cust.get("sdt", ""),
                "dia_chi": cust.get("dia_chi", ""),
                "ngay_tra": cust.get("ngay_tra", None),
                "shop": final_shop, # <--- Trường Shop đã chuẩn hóa
                "tong_tien": int(cust.get("tong_tien", 0)),
                "da_coc": int(cust.get("da_coc", 0)),
                "httt": cust.get("httt", "Ship COD"),
                "van_chuyen": cust.get("van_chuyen", "Thường"),
                
                # DANH SÁCH SẢN PHẨM (List of Dicts)
                "items": products 
            }
            
            return mapped_data, raw_text
            
    except Exception as e:
        return None, f"Lỗi Exception: {str(e)}"
    
    return None, "AI trả về rỗng"

# --- HÀM TẠO ẢNH GIẢ LẬP (ĐỂ TEST QUY TRÌNH) ---
def create_placeholder_image(text="AI Generated"):
    """Tạo một ảnh PNG đơn giản chứa text"""
    try:
        img = Image.new('RGB', (512, 512), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((50, 250), f"AI DESIGN:\n{text}", fill=(255, 255, 0))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except:
        return None

def gen_anh_mau_theu(prompt_text):
    """
    Hàm gọi AI vẽ mẫu. 
    Hiện tại dùng giả lập để test luồng upload Supabase.
    Sau này có key xịn thì thay bằng code gọi API Imagen.
    """
    if not configure_ai(): return None
    
    # Giả lập delay như đang vẽ thật
    import time
    time.sleep(1) 
    
    # Trả về bytes của ảnh giả lập
    return create_placeholder_image(prompt_text)
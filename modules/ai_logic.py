import google.generativeai as genai
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image
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
    Hàm trích xuất thông tin đơn hàng và xác định Shop.
    """
    if not configure_ai(): 
        return None, "Lỗi: Chưa cấu hình Google API Key"
    
    try:
        today_str = datetime.now().strftime("%d/%m/%Y")
        
        system_instruction = f"""
        Hôm nay là: {today_str}.
        Nhiệm vụ: Phân tích đoạn chat thành JSON và xác định mã SHOP.
        
        1. XÁC ĐỊNH SHOP (Quan trọng):
           - "TGTD" hoặc "TGTĐ" -> shop: "TGTĐ"
           - "Inside" hoặc "IS"   -> shop: "Inside"
           - "Lanh Canh" hoặc "LC" -> shop: "Lanh Canh"
           - Default: "Inside"
        
        2. OUTPUT JSON FORMAT:
        {{
            "customer_info": {{
                "ten_khach": "...", "sdt": "...", "dia_chi": "...",
                "ngay_tra": "YYYY-MM-DD", "shop": "...",
                "tong_tien": 0, "da_coc": 0, "httt": "...", "van_chuyen": "..."
            }},
            "products": [ {{ "ten_sp": "...", "mau": "...", "size": "...", "kieu_theu": "..." }} ]
        }}
        """
        
        # Lưu ý: Model 2.5 flash cho text analysis (nếu key hỗ trợ)
        # Nếu lỗi model not found, bro đổi về 'gemini-1.5-flash' nhé.
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash', 
            system_instruction=system_instruction,
            generation_config={"response_mime_type": "application/json"}
        )
        
        response = model.generate_content(f"Phân tích đơn: {text_input}")
        
        if response.text:
            data = json.loads(response.text)
            if isinstance(data, list): data = data[0] if len(data) > 0 else {}
            
            cust = data.get("customer_info", {}) or data
            products = data.get("products", []) or [{
                "ten_sp": data.get("san_pham", ""), "mau": data.get("mau_sac", ""), 
                "size": data.get("size", ""), "kieu_theu": data.get("yeu_cau_theu", "")
            }]
            
            # Chuẩn hóa Shop
            raw_shop = cust.get("shop", "Inside")
            shop = "Inside"
            if raw_shop in ["TGTĐ", "TGTD"]: shop = "TGTĐ"
            elif raw_shop in ["Lanh Canh", "LC"]: shop = "Lanh Canh"

            return {
                "ten_khach_hang": cust.get("ten_khach", ""),
                "so_dien_thoai": cust.get("sdt", ""),
                "dia_chi": cust.get("dia_chi", ""),
                "ngay_tra": cust.get("ngay_tra", None),
                "shop": shop,
                "tong_tien": int(cust.get("tong_tien", 0)),
                "da_coc": int(cust.get("da_coc", 0)),
                "httt": cust.get("httt", "Ship COD"),
                "van_chuyen": cust.get("van_chuyen", "Thường"),
                "items": products 
            }, response.text
            
    except Exception as e:
        return None, f"Lỗi: {str(e)}"
    
    return None, "AI rỗng"

def gen_anh_mau_theu(image_input_bytes, custom_prompt):
    """
    Hàm tạo ảnh mẫu thêu bằng Google Gemini 3 Image Preview.
    Gửi: [Prompt + Ảnh Upload + Ảnh Style Ref]
    """
    if not configure_ai(): 
        print("❌ Chưa cấu hình AI")
        return None
    
    try:
        # 1. Cấu hình model Image Generation mới nhất
        model = genai.GenerativeModel(model_name='gemini-3-pro-image-preview')
        
        # 2. Load ảnh input
        img_input = Image.open(io.BytesIO(image_input_bytes))
        
        # 3. Load ảnh style reference
        style_img = None
        style_path = "style_mau.jpg"
        
        if os.path.exists(style_path):
            try:
                style_img = Image.open(style_path)
                print("✅ Đã load style_mau.jpg")
            except: pass
        
        # 4. Prompt Engineering cho Thêu
        full_prompt = f"""tạo file thêu cho phần đầu của con vật, giữ đúng góc mặt, màu lông, chi tiết. tương tự như mẫu file thêu ở hình mẫu
        """
        
        # 5. Payload
        content_parts = [full_prompt, img_input]
        if style_img:
            content_parts.append("Style Reference:")
            content_parts.append(style_img)
        
        # 6. Generate
        print(f"🎨 Đang gen ảnh với {model.model_name}...")
        response = model.generate_content(content_parts)
        
        # 7. Extract Image Data
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    print("✅ Đã nhận được ảnh từ AI!")
                    return part.inline_data.data
                
        print("⚠️ Không tìm thấy ảnh trong response.")
        return None
        
    except Exception as e:
        print(f"❌ Lỗi gen ảnh AI: {e}")
        return None
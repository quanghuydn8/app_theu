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
    """
    Cấu hình Google Gemini AI từ biến môi trường.
    Đã loại bỏ fallback sang streamlit.secrets để code độc lập.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if api_key:
        genai.configure(api_key=api_key)
        return True
    else:
        print("❌ Lỗi: Không tìm thấy GOOGLE_API_KEY trong file .env")
        return False

def xuly_ai_gemini(text_input):
    """
    Hàm trích xuất thông tin đơn hàng và xác định Shop từ đoạn chat.
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
        
        2. QUY TẮC TÍNH NGÀY TRẢ HÀNG (ngay_tra):
           - Bước 1: Kiểm tra xem trong tin nhắn có ghi rõ ngày trả/ngày nhận không?
             -> Nếu CÓ: Sử dụng ngày đó (định dạng YYYY-MM-DD).
             -> Nếu KHÔNG: Tính toán tự động dựa trên ngày hôm nay ({today_str}) theo quy tắc sau:
                + Phân loại sản phẩm trong đơn:
                  * Loại 1 (Áo): Sweater, Hoodie, Tshirt, Polo, Áo thun, Zip...
                  * Loại 2 (Quần): Quần short, Quần dài, Jogger...
                  * Loại 3 (Phụ kiện): Túi, Mũ, Khác...
                + Logic cộng ngày:
                  * Trường hợp A: Nếu đơn hàng chỉ chứa 1 Loại sản phẩm duy nhất (Ví dụ: Chỉ toàn Áo, hoặc chỉ toàn Quần) -> Ngày trả = Ngày đặt hàng + 12 ngày.
                  * Trường hợp B: Nếu đơn hàng mix từ 2 Loại trở lên (Ví dụ: Áo + Quần, Áo + Túi, Quần + Túi...) -> Ngày trả = Ngày đặt hàng + 22 ngày.
        3. XÁC ĐỊNH NGÀY ĐẶT (ngay_dat):
           - Kiểm tra xem khách có nhắc đến "ngày đặt", "đơn ngày...", "hôm qua", "hôm kia"... không?
           - Nếu CÓ: Trích xuất và định dạng YYYY-MM-DD.
           - Nếu KHÔNG: Mặc định là ngày hôm nay ({today_str}).
        4. XÁC ĐỊNH VẬN CHUYỂN & THANH TOÁN (Quan trọng):
           A. Vận chuyển (van_chuyen):
              - Nếu thấy "bay", "máy bay", "đường bay" -> "Bay ✈"
              - Nếu thấy "xe ôm", "grap", "hỏa tốc", "gấp", "nhanh" -> "Xe Ôm 🏍"
              - Mặc định còn lại -> "Thường"
           
           B. Hình thức thanh toán (httt):
              - Nếu thấy "0đ" -> "0đ 📷"
              - Mặc định còn lại (hoặc ghi COD, thu hộ) -> "Ship COD 💵"
        5. XÁC ĐỊNH CO_HEN_NGAY (Quan trọng):
           - Nếu khách dùng từ: "cần trước ngày", "lấy đúng ngày", "deadline", "gấp", "kịp ngày", "chốt ngày"...
           -> co_hen_ngay: true
           - Còn lại (để shop tự tính hoặc thoải mái thời gian) -> co_hen_ngay: false
        6. XÁC ĐỊNH GHI CHÚ ĐẶC BIỆT (ghi_chu):
           - Trích xuất tất cả thông tin quan trọng mà không nằm trong các trường trên (Ví dụ: khách cho nhiều SĐT, yêu cầu đóng gói, lưu ý về khách hàng, hoặc bất kỳ thông tin bổ sung nào).
        7. OUTPUT JSON FORMAT:
        {{
            "customer_info": {{
                "ten_khach": "...", "sdt": "...", "dia_chi": "...",
                "ngay_dat": "YYYY-MM-DD", "ngay_tra": "YYYY-MM-DD", "shop": "...",
                "tong_tien": 0, "da_coc": 0, "httt": "...", "van_chuyen": "...", 
                "co_hen_ngay": false, "ghi_chu": "..."
            }},
            "products": [ {{ "ten_sp": "...", "mau": "...", "size": "...", "kieu_theu": "..." }} ]
        }}
        """
        
        # Cấu hình Model
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash', # Update lên bản 2.0 Flash mới nhất nếu có, hoặc giữ 1.5-flash
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
                "ngay_dat": cust.get("ngay_dat", None),
                "ngay_tra": cust.get("ngay_tra", None),
                "shop": shop,
                "tong_tien": int(cust.get("tong_tien", 0)),
                "da_coc": int(cust.get("da_coc", 0)),
                "httt": cust.get("httt", "Ship COD"),
                "van_chuyen": cust.get("van_chuyen", "Thường"),
                "co_hen_ngay": cust.get("co_hen_ngay", False),
                "ghi_chu": cust.get("ghi_chu", ""),
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
        return None
    
    try:
        # 1. Cấu hình model Image Generation
        model = genai.GenerativeModel(model_name='gemini-2.0-flash') # Hoặc gemini-pro-vision tùy key
        
        # 2. Load ảnh input
        img_input = Image.open(io.BytesIO(image_input_bytes))
        
        # 3. Load ảnh style reference
        style_img = None
        style_path = "style_mau.jpg" # Đảm bảo file này có trong thư mục gốc
        
        if os.path.exists(style_path):
            try:
                style_img = Image.open(style_path)
            except: pass
        
        # 4. Prompt Engineering
        full_prompt = f"tạo file thêu cho phần đầu của con vật, giữ đúng góc mặt, màu lông, chi tiết. tương tự như mẫu file thêu ở hình mẫu"
        
        # 5. Payload
        content_parts = [full_prompt, img_input]
        if style_img:
            content_parts.append("Style Reference:")
            content_parts.append(style_img)
        
        # 6. Generate
        print(f"🎨 Đang gen ảnh với {model.model_name}...")
        response = model.generate_content(content_parts)
        
        # 7. Extract Image Data
        # Lưu ý: Gemini trả về inline_data hoặc link tùy phiên bản, cần check kỹ output thực tế
        # Đoạn code dưới đây giả định trả về inline_data như bản cũ
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

def generate_image_from_ref(image_bytes, prompt_text):
    """
    Tạo ảnh mới dựa trên ảnh gốc và câu lệnh prompt.
    """
    if not configure_ai():
        return None

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        img_input = Image.open(io.BytesIO(image_bytes))
        content = [prompt_text, img_input]
        
        print(f"🎨 Đang edit ảnh với prompt: {prompt_text}...")
        response = model.generate_content(content)
        
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    print("✅ Generate thành công!")
                    return part.inline_data.data
        
        print("⚠️ Không có dữ liệu ảnh trong response")
        return None
        
    except Exception as e:
        print(f"❌ Lỗi generate_image_from_ref: {e}")
        return None
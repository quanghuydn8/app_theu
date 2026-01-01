import google.generativeai as genai
import os
import json

def configure_ai():
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def xuly_ai_gemini(text_input):
    if not configure_ai(): return None
    try:
        system_instruction = """
        Bạn là trợ lý quản lý đơn hàng thêu chuyên nghiệp. Trích xuất thông tin dưới dạng JSON:
        ten_khach, sdt, dia_chi, san_pham, so_luong (int), tong_tien (int VND), yeu_cau_theu, sku (TS-MAU-SIZE).
        """
        model = genai.GenerativeModel(model_name='gemini-3-flash-preview', system_instruction=system_instruction)
        response = model.generate_content(f"Trích xuất JSON từ chat sau:\n{text_input}")
        response_text = response.text.strip()
        if response_text.startswith("```"):
            start = response_text.find("{")
            end = response_text.rfind("}")
            response_text = response_text[start:end+1]
        data = json.loads(response_text)
        return {
            "ten_khach_hang": data.get("ten_khach", ""),
            "so_dien_thoai": data.get("sdt", ""),
            "dia_chi": data.get("dia_chi", ""),
            "san_pham": data.get("san_pham", "Áo thun thêu logo"),
            "so_luong": int(data.get("so_luong", 1)),
            "tong_tien": int(data.get("tong_tien", 0)),
            "yeu_cau_theu": data.get("yeu_cau_theu", ""),
            "sku": data.get("sku", "TS-DEN-M")
        }
    except Exception:
        return None

def gen_anh_mau_theu(anh_pet, anh_style_ref):
    if not configure_ai(): return None
    try:
        model = genai.GenerativeModel(model_name='gemini-3-pro-image-preview')
        prompt = "Tạo file thêu cho phần đầu của con vật trong ảnh pet, giữ đúng góc mặt, màu lông, chi tiết. Sử dụng phong cách thêu như ảnh mẫu."
        response = model.generate_content([prompt, anh_pet, "Ảnh thêu mẫu:", anh_style_ref])
        if hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'inline_data'):
                    return part.inline_data.data
        return None
    except Exception:
        return None


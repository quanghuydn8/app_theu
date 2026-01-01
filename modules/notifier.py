import requests
import os
import streamlit as st

def send_telegram_notification(message):
    """
    Hàm gửi thông báo qua Telegram Bot
    Tham số: message - Nội dung thông báo (hỗ trợ HTML)
    """
    # Lấy thông tin cấu hình từ biến môi trường (File .env hoặc st.secrets)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    # Kiểm tra nếu chưa cấu hình thì thông báo nhẹ, không làm crash app
    if not token or not chat_id:
        # st.toast("⚠️ Chưa cấu hình Telegram Bot. Vui lòng kiểm tra .env", icon="🤖")
        return False

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        # Gửi yêu cầu POST tới Telegram API với timeout 5 giây
        response = requests.post(api_url, data=payload, timeout=5)
        
        # Kiểm tra kết quả trả về
        if response.status_code == 200:
            st.toast("🔔 Đã gửi thông báo Telegram thành công!", icon="🚀")
            return True
        else:
            st.toast(f"❌ Lỗi gửi Telegram: {response.status_code}", icon="⚠️")
            return False
            
    except Exception as e:
        # Xử lý lỗi mạng hoặc lỗi API mà không làm dừng ứng dụng
        st.toast(f"📡 Lỗi kết nối Telegram: {str(e)}", icon="🌐")
        return False


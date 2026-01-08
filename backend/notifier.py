import requests
import os

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
            print("LOG NOTIFICATION: 🔔 Đã gửi thông báo Telegram thành công!")
            return True
        else:
            print(f"LOG NOTIFICATION: ❌ Lỗi gửi Telegram: {response.status_code}")
            return False
            
    except Exception as e:
        # Xử lý lỗi mạng hoặc lỗi API mà không làm dừng ứng dụng
        print(f"LOG NOTIFICATION: 📡 Lỗi kết nối Telegram: {str(e)}")
        return False

def check_order_notifications(ma_don, old_tags, new_tags):
    """
    Kiểm tra các rule gửi thông báo dựa trên tag
    1. Chờ phôi -> Hết phôi
    2. Thiếu file tk -> Thiếu file thiết kế
    """
    if not isinstance(old_tags, list): old_tags = []
    if not isinstance(new_tags, list): new_tags = []

    # Rule 1: "Chờ phôi" (Gửi nếu mới được thêm vào)
    if "Chờ phôi" in new_tags and "Chờ phôi" not in old_tags:
        msg = f"⚠️ <b>Đã hết phôi áo của đơn hàng {ma_don}, Xin hãy đặt thêm phôi!</b>"
        send_telegram_notification(msg)

    # Rule 2: "Thiếu file tk" (Gửi nếu mới được thêm vào)
    if "Thiếu file tk" in new_tags and "Thiếu file tk" not in old_tags:
        msg = f"📂 <b>Đơn hàng {ma_don} đang thiếu file thiết kế, hãy kiểm tra!</b>"
        send_telegram_notification(msg)

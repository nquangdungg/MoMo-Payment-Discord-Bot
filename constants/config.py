"""Cấu hình toàn cục và biến môi trường cho bot."""
import logging
from datetime import timezone, timedelta

from decouple import config

# Hằng số toàn cục
MAX_RETRIES = 3
REQUEST_DELAY = 20  # Delay 20s
POLLING_INTERVAL = 30  # Kiểm tra giao dịch mỗi 30s
SO_LAN_TOI_DA_MOI_NGUOI = 3
THOI_GIAN_CHO = 600  # 10 phút
SO_TIEN_TOI_THIEU = 2000
THOI_GIAN_GIOI_HAN = 60
VN_TIMEZONE = timezone(timedelta(hours=7))
REDIRECT_URL = "https://panel.minecraftvn.xyz/return"
IPN_URL = "https://panel.minecraftvn.xyz/notify"

# Biến môi trường
PARTNER_CODE = config("PARTNER_CODE")
ACCESS_KEY = config("ACCESS_KEY")
SECRET_KEY = config("SECRET_KEY")
ENDPOINT = config("MOMO_ENDPOINT", default="https://payment.momo.vn/v2/gateway/api")
ipnUrl = config("ipnUrl", default=IPN_URL)
redirectUrl = config("redirectUrl", default=REDIRECT_URL)
TOKEN_BOT = config("DISCORD_BOT_TOKEN")
KENH_NHAN_VIEN = int(config("STAFF_CHANNEL_ID", default=1375077234611720202))


def validate_config() -> None:
    """Kiểm tra các biến môi trường bắt buộc. Gọi một lần khi khởi động bot."""
    if not TOKEN_BOT:
        raise ValueError("TOKEN_BOT không được thiết lập trong biến môi trường")
    if not PARTNER_CODE or not ACCESS_KEY or not SECRET_KEY:
        raise ValueError("PARTNER_CODE, ACCESS_KEY, SECRET_KEY phải được thiết lập")
    if not ipnUrl.startswith("https") or not redirectUrl.startswith("https"):
        raise ValueError("ipnUrl và redirectUrl phải là HTTPS")
    if PARTNER_CODE == "MOMORGVR20250913" or ACCESS_KEY == "Z5yhbmx1zPGnkKk1":
        logging.warning(
            "Cảnh báo: Sử dụng PARTNER_CODE hoặc ACCESS_KEY mặc định. "
            "Vui lòng cập nhật giá trị thực từ MoMo Business Portal."
        )

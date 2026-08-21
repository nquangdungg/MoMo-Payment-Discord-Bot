"""Tiện ích chuyển đổi dữ liệu sang file đính kèm Discord."""
import base64
import io
import logging
from typing import Optional

import discord


def base64_to_discord_file(base64_string: str, filename: str = "qr_code.png") -> Optional[discord.File]:
    """Chuyển chuỗi base64 (ảnh QR lấy từ trang thanh toán MoMo) thành discord.File."""
    try:
        # Loại bỏ phần tiền tố "data:image/png;base64,"
        if base64_string.startswith("data:image/png;base64,"):
            base64_string = base64_string.split(",")[1]

        # Giải mã base64 thành bytes
        image_data = base64.b64decode(base64_string)

        # Tạo BytesIO object để lưu dữ liệu hình ảnh
        image_buffer = io.BytesIO(image_data)

        # Tạo discord.File từ BytesIO
        return discord.File(image_buffer, filename=filename)
    except Exception as e:
        logging.error(f"Lỗi khi chuyển đổi base64 sang discord.File: {e}")
        return None

"""Các model dữ liệu dùng để theo dõi giao dịch thanh toán và giới hạn tần suất."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class GiaoDich:
    """Đại diện cho một giao dịch thanh toán MoMo đang được theo dõi."""

    ma_giao_dich: int
    noi_dung: str
    sotien: int
    thoi_gian_tao: datetime
    channel_id: int
    user_id: int
    request_id: str
    message_id: int
    pay_url: str


@dataclass
class RateLimitInfo:
    """Theo dõi số giao dịch đang chờ và thời điểm gần nhất của một người dùng."""

    so_lan: int = 0
    lan_thu_truoc: float = 0.0

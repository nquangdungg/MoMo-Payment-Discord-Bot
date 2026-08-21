"""Hàm bảo mật: băm dữ liệu nhạy cảm và tạo chữ ký HMAC cho MoMo."""
import hashlib
import hmac
import logging


def hash_sensitive(data: str) -> str:
    """Băm dữ liệu nhạy cảm bằng SHA-256 (dùng khi ghi log, không lộ giá trị gốc)."""
    return hashlib.sha256(data.encode()).hexdigest()


def create_signature(data: dict, secret_key: str, endpoint: str = "/create") -> str:
    """Tạo chữ ký HMAC-SHA256 cho MoMo theo API v3."""
    if endpoint == "/create":
        required_params = [
            "accessKey", "amount", "extraData", "ipnUrl",
            "orderId", "orderInfo", "partnerCode", "redirectUrl",
            "requestId", "requestType"
        ]
    elif endpoint == "/query":
        required_params = ["accessKey", "orderId", "partnerCode", "requestId"]
    else:
        raise ValueError(f"Unsupported endpoint: {endpoint}")

    raw_signature = "&".join(
        [f"{key}={data[key]}" for key in sorted(required_params) if key in data]
    )
    logging.debug(f"Raw signature for {endpoint}: {raw_signature}")
    return hmac.new(
        secret_key.encode("utf-8"), raw_signature.encode("utf-8"), hashlib.sha256
    ).hexdigest()

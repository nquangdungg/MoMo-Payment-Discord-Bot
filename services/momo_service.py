"""Service giao tiếp trực tiếp với MoMo API: tạo link thanh toán và tra cứu trạng thái."""
import asyncio
import base64
import json
import logging
import time
import uuid

import requests
from bs4 import BeautifulSoup

from constants.config import (
    ACCESS_KEY,
    ENDPOINT,
    MAX_RETRIES,
    PARTNER_CODE,
    REQUEST_DELAY,
    SECRET_KEY,
    ipnUrl,
    redirectUrl,
)
from utils.discord_files import base64_to_discord_file
from utils.security import create_signature, hash_sensitive

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)


async def tao_link_thanh_toan(sotien: int, ma_giao_dich: int) -> tuple:
    """Gọi /create để tạo link thanh toán, sau đó lấy ảnh QR (base64) từ payUrl.

    Trả về (pay_url, request_id, qr_file).
    """
    try:
        request_id = str(uuid.uuid4())
        order_id = f"GD{ma_giao_dich}"
        order_info = f"TT-{order_id}"
        extra_data = base64.b64encode(json.dumps({"username": "momo"}).encode()).decode()

        code_data = {
            "partnerCode": PARTNER_CODE,
            "accessKey": ACCESS_KEY,
            "requestId": request_id,
            "orderId": order_id,
            "amount": str(sotien),
            "orderInfo": order_info,
            "redirectUrl": redirectUrl,
            "ipnUrl": ipnUrl,
            "extraData": extra_data,
            "requestType": "captureWallet"
        }

        for key in ["partnerCode", "accessKey", "requestId", "amount", "orderId", "orderInfo", "redirectUrl", "ipnUrl", "requestType"]:
            if not code_data.get(key):
                raise ValueError(f"Thiếu hoặc sai tham số: {key}")
            if key in ["orderId", "orderInfo", "requestId"]:
                if not all(c.isalnum() or c in ['-', '_'] for c in str(code_data[key])):
                    raise ValueError(f"Tham số {key} chứa ký tự không hợp lệ: {code_data[key]}")

        code_data["signature"] = create_signature(code_data, SECRET_KEY, "/create")

        logging.debug(f"Tạo payment request: {json.dumps({k: v if k != 'signature' else '[hidden]' for k, v in code_data.items()}, ensure_ascii=False)}")
        start_time = time.time()
        response = requests.post(
            f"{ENDPOINT}/create",
            json=code_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': USER_AGENT
            }
        )
        response_data = response.json()
        elapsed = time.time() - start_time
        delay = max(0, REQUEST_DELAY - elapsed)
        logging.debug(f"Request create_payment took {elapsed:.3f}s, delaying {delay:.3f}s")
        logging.debug(f"Payment response (hash): {hash_sensitive(json.dumps(response_data))}")
        logging.debug(f"Full response: {json.dumps(response_data, ensure_ascii=False)}")
        await asyncio.sleep(delay)

        if response.status_code != 200 or response_data.get("resultCode") != 0:
            sub_errors = response_data.get("subErrors", [])
            error_details = "\n".join([f"- {err['field']}: {err['message']}" for err in sub_errors]) if sub_errors else "Không có chi tiết lỗi."
            if response_data.get("resultCode") == 41:
                error_details += "\n- OrderId đã được sử dụng. Vui lòng tạo giao dịch mới với mã giao dịch khác."
            raise Exception(f"Lỗi MoMo API: {response_data.get('message', 'Unknown error')} (resultCode: {response_data.get('resultCode', 'N/A')})\nChi tiết: {error_details}")

        pay_url = response_data.get("payUrl")
        qr_file = None
        try:
            qr_response = requests.get(
                pay_url,
                headers={'User-Agent': USER_AGENT}
            )
            if qr_response.status_code == 200:
                soup = BeautifulSoup(qr_response.text, 'html.parser')
                img_tag = soup.find('img', alt='paymentcode')
                if img_tag and 'src' in img_tag.attrs:
                    base64_qr = img_tag['src']
                    qr_file = base64_to_discord_file(base64_qr)
                    logging.debug("QR code base64 extracted successfully")
                else:
                    logging.warning("Không tìm thấy thẻ <img alt='paymentcode'> trong payUrl")
            else:
                logging.error(f"Lỗi truy cập payUrl: HTTP {qr_response.status_code}")
        except Exception as e:
            logging.error(f"Lỗi lấy QR code từ payUrl: {e}")

        return pay_url, request_id, qr_file
    except Exception as e:
        logging.error(f"Lỗi tạo link thanh toán: {e}")
        raise


async def kiem_tra_giao_dich(order_id: str) -> dict:
    """Gọi /query để kiểm tra trạng thái giao dịch, tự động thử lại khi lỗi."""
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            request_id = str(uuid.uuid4())
            query_data = {
                "partnerCode": PARTNER_CODE,
                "accessKey": ACCESS_KEY,
                "requestId": request_id,
                "orderId": order_id
            }

            query_data["signature"] = create_signature(query_data, SECRET_KEY, "/query")

            logging.debug(f"Query request: {json.dumps({k: v if k != 'signature' else '[hidden]' for k, v in query_data.items()}, ensure_ascii=False)}")
            start_time = time.time()
            response = requests.post(
                f"{ENDPOINT}/query",
                json=query_data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': USER_AGENT
                }
            )
            response_data = response.json()
            elapsed = time.time() - start_time
            delay = max(0, REQUEST_DELAY - elapsed)
            logging.debug(f"Request query_transaction took {elapsed:.3f}s, delaying {delay:.3f}s")
            logging.debug(f"Query response (hash): {hash_sensitive(json.dumps(response_data))}")
            logging.debug(f"Full query response: {json.dumps(response_data, ensure_ascii=False)}")
            await asyncio.sleep(delay)

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response_data.get('message', 'Unknown error')}")
            return response_data
        except Exception as e:
            retry_count += 1
            logging.error(f"Lỗi kiểm tra giao dịch (lần {retry_count}/{MAX_RETRIES}): {e}")
            if retry_count < MAX_RETRIES:
                delay = REQUEST_DELAY * (retry_count * 2)
                logging.info(f"Thử lại sau {delay}s...")
                await asyncio.sleep(delay)
                continue
            raise Exception(f"Thất bại sau {MAX_RETRIES} lần thử: {e}")

# MoMo Payment Bot

Discord bot tích hợp **MoMo Payment API**, cho phép người dùng tạo và theo dõi yêu cầu thanh toán trực tiếp trong Discord thông qua slash command. Bot tự động kiểm tra trạng thái giao dịch và thông báo cho kênh nhân viên khi thanh toán thành công.

🇬🇧 [English](README.md)

## Tính năng

* `/thanhtoan <số_tiền>` — tạo yêu cầu thanh toán MoMo.

  * Số tiền tối thiểu: **2.000 VNĐ**.
  * Trả về **link thanh toán** và **mã QR**.
  * Tự động kiểm tra trạng thái giao dịch cho đến khi:

    * Thanh toán thành công.
    * Thanh toán thất bại.
    * Giao dịch hết hạn sau **10 phút**.
* `/huygiaodich <mã_giao_dịch>` — hủy một giao dịch đang chờ xử lý.
* **Rate limit theo người dùng**:

  * Chờ **60 giây** giữa các lần tạo giao dịch.
  * Tối đa **3 giao dịch đang chờ** cùng lúc.
* Tự động thông báo vào **kênh nhân viên** khi giao dịch thanh toán thành công.
* Ánh xạ mã lỗi và trạng thái từ **MoMo API v3** thành thông báo tiếng Việt dễ hiểu.
* Ghi log có cấu trúc vào `bot.log`.
* Dữ liệu nhạy cảm được **băm SHA-256** trước khi ghi vào log.

## Cấu trúc dự án

```text
momo-bot/
├── main.py                     # Điểm khởi chạy bot
├── constants/
│   ├── config.py               # Biến môi trường và hằng số toàn cục
│   └── momo_errors.py          # Bảng mã lỗi/trạng thái MoMo API
├── model/
│   └── transaction.py          # Dataclass GiaoDich và RateLimitInfo
├── utils/
│   ├── logger.py               # Cấu hình logging
│   ├── security.py             # HMAC signature và hashing dữ liệu
│   ├── discord_files.py        # Chuyển base64 thành discord.File
│   └── embeds.py               # Hàm tạo footer cho Discord Embed
├── services/
│   ├── momo_service.py         # Giao tiếp với MoMo API /create và /query
│   └── transaction_service.py  # Quản lý giao dịch, rate limit và polling
├── command/
│   └── payment_commands.py     # Slash command /thanhtoan và /huygiaodich
├── requirements.txt
└── .env.example
```

## Yêu cầu

* **Python 3.10+**
* Một ứng dụng **Discord Bot** và bot token.
* Tài khoản **MoMo Business** đã được cấp quyền sử dụng API.
* Hai endpoint **HTTPS public** cho:

  * `ipnUrl`
  * `redirectUrl`

## Cài đặt

### 1. Cài đặt dependencies

Clone hoặc copy project về máy, sau đó chạy:

```bash
pip install -r requirements.txt
```

### 2. Cấu hình biến môi trường

Copy file `.env.example` thành `.env`:

```bash
cp .env.example .env
```

Sau đó điền các giá trị tương ứng:

| Biến                | Mô tả                                       |
| ------------------- | ------------------------------------------- |
| `DISCORD_BOT_TOKEN` | Token của Discord bot                       |
| `STAFF_CHANNEL_ID`  | ID kênh nhận thông báo giao dịch thành công |
| `PARTNER_CODE`      | Partner Code từ MoMo Business               |
| `ACCESS_KEY`        | Access Key từ MoMo Business                 |
| `SECRET_KEY`        | Secret Key từ MoMo Business                 |
| `MOMO_ENDPOINT`     | URL MoMo API gateway                        |
| `ipnUrl`            | HTTPS endpoint nhận callback từ MoMo        |
| `redirectUrl`       | HTTPS endpoint chuyển hướng sau thanh toán  |

> **Lưu ý:** Không commit file `.env` hoặc bất kỳ credential nào của MoMo/Discord lên Git.

### 3. Mời bot vào Discord server

Bot cần các scope:

* `bot`
* `applications.commands`

Bot cũng cần các permission Discord phù hợp để gửi message và embed vào các channel được cấu hình.

### 4. Khởi động bot

```bash
python main.py
```

Slash command sẽ được đồng bộ khi bot hoàn tất quá trình khởi động.

## Luồng thanh toán

```text
User
  │
  │ /thanhtoan <số_tiền>
  ▼
Discord Bot
  │
  │ Create payment
  ▼
MoMo API
  │
  ├── Payment URL
  └── QR Code
  │
  ▼
User thực hiện thanh toán
  │
  ▼
Bot polling /query mỗi 30 giây
  │
  ├── Thành công ──────► Thông báo kênh nhân viên
  ├── Thất bại ────────► Cập nhật trạng thái
  └── Hết hạn 10 phút ─► Kết thúc giao dịch
```

## Lưu ý

### Production và Sandbox

Mặc định bot sử dụng **MoMo production endpoint**. Các giao dịch tạo từ production là giao dịch thật.

Khi phát triển hoặc kiểm thử, cần cấu hình `MOMO_ENDPOINT` sang môi trường **sandbox** tương ứng của MoMo.

### Lưu trữ giao dịch

Trạng thái giao dịch và thông tin rate limit hiện được lưu **in-memory**.

Điều này có nghĩa:

* Dữ liệu sẽ mất khi bot restart.
* Không phù hợp để chạy nhiều instance/shard cùng lúc.
* Chưa có cơ chế phục hồi trạng thái giao dịch sau khi process bị dừng.

### QR Code

Bot hiện lấy QR code bằng cách scrape trang thanh toán MoMo thông qua `BeautifulSoup` thay vì lấy trực tiếp từ response của API `/create`.

Cách triển khai này phụ thuộc vào cấu trúc HTML của trang thanh toán và có thể ngừng hoạt động nếu MoMo thay đổi giao diện hoặc HTML.

### Kiểm tra trạng thái giao dịch

Bot hiện **chưa sử dụng webhook/IPN để xác nhận thanh toán**.

Thay vào đó, bot polling endpoint `/query` của MoMo mỗi **30 giây** cho đến khi giao dịch có trạng thái cuối cùng hoặc hết thời gian chờ.

## Bảo mật

* Không hard-code `SECRET_KEY`, `ACCESS_KEY` hoặc Discord bot token trong source code.
* Sử dụng file `.env` cho credential.
* Không commit `.env` lên Git.
* Dữ liệu nhạy cảm trong log được hash bằng **SHA-256**.
* Chỉ sử dụng endpoint HTTPS cho callback của MoMo.

## Giấy phép

Dự án được phát hành theo **GNU General Public License v3.0 (GPL-3.0)**.

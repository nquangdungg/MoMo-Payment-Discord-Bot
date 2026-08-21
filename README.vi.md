# MoMo Payment Bot

Bot Discord cho phép người dùng tạo yêu cầu thanh toán MoMo thật ngay trong server, tự động theo dõi trạng thái giao dịch, và thông báo cho nhân viên khi thanh toán thành công — tất cả thông qua slash command.

🇬🇧 [English](README.md)

## Tính năng

- `/thanhtoan <số_tiền>` — tạo yêu cầu thanh toán MoMo (tối thiểu 2,000 VNĐ), trả về link thanh toán + mã QR, tự động kiểm tra trạng thái với MoMo cho đến khi giao dịch thành công, thất bại, hoặc hết hạn (10 phút).
- `/huygiaodich <mã_giao_dịch>` — hủy một giao dịch đang chờ xử lý.
- Giới hạn tần suất theo từng người dùng (chờ 60s giữa các lần tạo, tối đa 3 giao dịch chờ xử lý cùng lúc).
- Tự động gửi thông báo đến kênh nhân viên khi có giao dịch thành công.
- Ánh xạ đầy đủ mã lỗi/trạng thái của MoMo API v3 sang thông điệp tiếng Việt dễ hiểu.
- Ghi log có cấu trúc vào `bot.log` (dữ liệu nhạy cảm được băm SHA-256 trước khi ghi log).

## Cấu trúc dự án

```
momo-bot/
├── main.py                     # điểm khởi chạy: nạp cấu hình, chạy bot
├── constants/
│   ├── config.py                # biến môi trường & hằng số toàn cục
│   └── momo_errors.py           # bảng tra mã lỗi/kết quả của MoMo API
├── model/
│   └── transaction.py           # dataclass GiaoDich / RateLimitInfo
├── utils/
│   ├── logger.py                 # cấu hình ghi log
│   ├── security.py               # tạo chữ ký HMAC + hàm băm dữ liệu
│   ├── discord_files.py          # chuyển base64 -> discord.File
│   └── embeds.py                 # hàm dựng footer embed dùng chung
├── services/
│   ├── momo_service.py           # gọi API MoMo /create và /query
│   └── transaction_service.py    # lưu trạng thái, giới hạn tần suất, vòng lặp kiểm tra
├── command/
│   └── payment_commands.py       # slash command /thanhtoan và /huygiaodich (Cog)
├── requirements.txt
└── .env.example
```

## Yêu cầu

- Python 3.10 trở lên
- Một ứng dụng bot Discord + token ([Discord Developer Portal](https://discord.com/developers/applications))
- Tài khoản MoMo Business đã được cấp quyền truy cập API ([business.momo.vn](https://business.momo.vn))
- Hai endpoint **HTTPS** có thể truy cập công khai cho `ipnUrl` và `redirectUrl` (MoMo sẽ gọi callback về hai địa chỉ này)

## Cài đặt

1. Clone/copy dự án, sau đó cài các thư viện cần thiết:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy file mẫu biến môi trường và điền giá trị thật:

   ```bash
   cp .env.example .env
   ```

   | Biến | Mô tả |
   |---|---|
   | `DISCORD_BOT_TOKEN` | Token của bot Discord |
   | `STAFF_CHANNEL_ID` | ID kênh dùng để thông báo khi giao dịch thành công |
   | `PARTNER_CODE` / `ACCESS_KEY` / `SECRET_KEY` | Thông tin xác thực lấy từ MoMo Business Portal |
   | `MOMO_ENDPOINT` | URL gốc của MoMo gateway (mặc định là production) |
   | `ipnUrl` / `redirectUrl` | URL callback HTTPS đã đăng ký với MoMo |

3. Mời bot vào server với scope `applications.commands` và `bot` (bật intent message content).

4. Chạy bot:

   ```bash
   python main.py
   ```

   Slash command sẽ tự động được đồng bộ khi bot khởi động (`on_ready`).

## Lưu ý

- Mặc định bot gọi đến endpoint **production** của MoMo — mọi giao dịch tạo ra đều là yêu cầu thanh toán thật. Nếu muốn test mà không mất tiền thật, hãy trỏ `MOMO_ENDPOINT` sang môi trường sandbox của MoMo.
- Trạng thái giao dịch (`giao_dich_active`, dữ liệu giới hạn tần suất) chỉ được lưu **trong bộ nhớ (in-memory)** — sẽ mất khi tiến trình restart, và không hoạt động đúng nếu chạy nhiều instance/shard bot cùng lúc.
- Bot lấy mã QR bằng cách scrape trang thanh toán của MoMo (`BeautifulSoup`) thay vì lấy trực tiếp từ response của API `/create` — cách này khá dễ vỡ nếu MoMo đổi cấu trúc HTML trang thanh toán.
- Dự án chưa có webhook nhận IPN; việc xác nhận thanh toán hoàn toàn dựa vào polling `/query` mỗi 30 giây.

## Giấy phép

Dự án công khai - Giấy phép GPL-3.0

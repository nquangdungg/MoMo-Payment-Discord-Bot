"""Các slash command Discord liên quan đến thanh toán MoMo."""
import logging
import random
import time
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from constants.config import (
    PARTNER_CODE,
    POLLING_INTERVAL,
    SO_LAN_TOI_DA_MOI_NGUOI,
    SO_TIEN_TOI_THIEU,
    THOI_GIAN_CHO,
    THOI_GIAN_GIOI_HAN,
    VN_TIMEZONE,
    ipnUrl,
    redirectUrl,
)
from model.transaction import GiaoDich, RateLimitInfo
from services.momo_service import tao_link_thanh_toan
from services.transaction_service import (
    giao_dich_active,
    giao_dich_dang_thuc_hien,
    kiem_tra_gioi_han_thoi_gian,
    kiem_tra_trang_thai_thanh_toan,
)
from utils.embeds import with_footer


class PaymentCommands(commands.Cog):
    """Nhóm lệnh tạo và quản lý giao dịch thanh toán MoMo."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="thanhtoan", description="Tạo giao dịch thanh toán MoMo (tối thiểu 2,000 VNĐ)")
    @app_commands.describe(sotien="Số tiền thanh toán (VNĐ)")
    async def thanh_toan(self, interaction: discord.Interaction, sotien: float):
        response_data = None
        noi_dung = None
        try:
            await interaction.response.defer(ephemeral=False)
        except discord.errors.NotFound:
            logging.error("Tương tác không hợp lệ (404)")
            return

        try:
            ten_nguoi_dung = str(interaction.user)
            ma_nguoi_dung = interaction.user.id

            if kiem_tra_gioi_han_thoi_gian(ten_nguoi_dung):
                await interaction.followup.send(
                    embed=with_footer(discord.Embed(
                        title="⏳ Vui Lòng Chờ",
                        description=(
                            f"⏱ **Bạn cần chờ {THOI_GIAN_GIOI_HAN} giây trước khi tạo giao dịch mới.**\n\n"
                            "**Lý do:** Hệ thống giới hạn tần suất để đảm bảo hiệu suất và công bằng.\n"
                            "**Hành động:**\n"
                            "- Đợi một chút trước khi thử lại.\n"
                            "- Liên hệ hỗ trợ qua DM hoặc kênh nhân viên nếu cần gấp."
                        ),
                        color=discord.Color.red(),
                        timestamp=datetime.now(VN_TIMEZONE)
                    )),
                    ephemeral=True
                )
                return

            info = giao_dich_dang_thuc_hien.get(ten_nguoi_dung)
            if info and info.so_lan >= SO_LAN_TOI_DA_MOI_NGUOI:
                await interaction.followup.send(
                    embed=with_footer(discord.Embed(
                        title="⚠️ Quá Giới Hạn Giao Dịch",
                        description=(
                            f"🚫 **Bạn đang có {SO_LAN_TOI_DA_MOI_NGUOI} giao dịch đang chờ xử lý.**\n\n"
                            "**Hành động:**\n"
                            "- Hoàn tất hoặc hủy giao dịch cũ trước khi tạo mới.\n"
                            "- Sử dụng lệnh `/huygiaodich <mã_giao_dich>` để hủy.\n"
                            "**Lý do:** Giới hạn này giúp bảo vệ tài khoản và hệ thống."
                        ),
                        color=discord.Color.red(),
                        timestamp=datetime.now(VN_TIMEZONE)
                    )),
                    ephemeral=True
                )
                return

            if ten_nguoi_dung not in giao_dich_dang_thuc_hien:
                giao_dich_dang_thuc_hien[ten_nguoi_dung] = RateLimitInfo(so_lan=0, lan_thu_truoc=time.time())
            giao_dich_dang_thuc_hien[ten_nguoi_dung].so_lan += 1
            giao_dich_dang_thuc_hien[ten_nguoi_dung].lan_thu_truoc = time.time()

            sotien = int(sotien)
            if sotien < SO_TIEN_TOI_THIEU:
                await interaction.followup.send(
                    embed=with_footer(discord.Embed(
                        title="⚠️ Số Tiền Không Hợp Lệ",
                        description=(
                            f"💸 **Số tiền tối thiểu là {SO_TIEN_TOI_THIEU:,} VNĐ.**\n\n"
                            "**Lý do:** Quy định của MoMo để đảm bảo giao dịch hợp lệ.\n"
                            "**Hành động:**\n"
                            f"- Nhập số tiền lớn hơn hoặc bằng {SO_TIEN_TOI_THIEU:,} VNĐ.\n"
                            "- Kiểm tra số dư ví MoMo trước khi thử lại."
                        ),
                        color=discord.Color.red(),
                        timestamp=datetime.now(VN_TIMEZONE)
                    )),
                    ephemeral=True
                )
                return

            ma_giao_dich = random.randint(1000000000, 9999999999)
            noi_dung = f"GD{ma_giao_dich}"
            pay_url, request_id, qr_file = await tao_link_thanh_toan(sotien, ma_giao_dich)

            embed = with_footer(discord.Embed(
                title="💳 Yêu Cầu Thanh Toán MoMo",
                description=(
                    f"**Chào {ten_nguoi_dung},**\n\n"
                    "Cảm ơn bạn đã sử dụng dịch vụ nPos! Vui lòng làm theo hướng dẫn để hoàn tất thanh toán:\n"
                    "- **Quét QR hoặc nhấp link:** Mở ứng dụng nPos chính thức.\n"
                    "- **Kiểm tra mã giao dịch:** Đảm bảo nội dung chuyển khoản chứa chính xác mã dưới đây.\n"
                    f"- **Thời hạn:** Giao dịch sẽ hết hạn sau {THOI_GIAN_CHO // 60} phút.\n\n"
                    "**Lưu ý:** Chụp màn hình giao dịch và liên hệ hỗ trợ nếu gặp vấn đề."
                ),
                color=discord.Color.from_rgb(213, 0, 96),
                timestamp=datetime.now(VN_TIMEZONE)
            ))
            embed.set_author(
                name="Hệ Thống Thanh Toán nPos - An Toàn & Tiện Lợi",
                url="https://momo.vn",
                icon_url="https://developers.momo.vn/static/img/favicon.png"
            )
            embed.set_thumbnail(url="https://developers.momo.vn/static/img/logo.png")
            embed.add_field(name="💰 Số Tiền Thanh Toán", value=f"**{sotien:,} VNĐ** (Tối thiểu: {SO_TIEN_TOI_THIEU:,} VNĐ)", inline=True)
            embed.add_field(name="📝 Mã Giao Dịch", value=f"**`{noi_dung}`** (Bắt buộc trong nội dung chuyển khoản)", inline=True)
            embed.add_field(name="🔑 Mã Yêu Cầu", value=f"`{request_id[:8]}...{request_id[-8:]}`", inline=True)
            embed.add_field(name="👤 Người Thanh Toán", value=f"{ten_nguoi_dung} (ID: `{ma_nguoi_dung}`)", inline=True)
            embed.add_field(name="🏬 Cửa Hàng", value=f"`NGUYEN QUANG DUNG` (Partner: `{PARTNER_CODE[:4]}...`)", inline=True)
            embed.add_field(name="💳 Phương Thức", value="**MoMo Wallet** (QR Code & Link)", inline=True)
            embed.add_field(
                name="⏰ Thời Gian Tạo",
                value=f"<t:{int(datetime.now(VN_TIMEZONE).timestamp())}:F> (<t:{int(datetime.now(VN_TIMEZONE).timestamp())}:R>)",
                inline=True
            )
            embed.add_field(
                name="⏳ Hết Hạn",
                value=f"<t:{int((datetime.now(VN_TIMEZONE) + timedelta(seconds=THOI_GIAN_CHO)).timestamp())}:F> (<t:{int((datetime.now(VN_TIMEZONE) + timedelta(seconds=THOI_GIAN_CHO)).timestamp())}:R>)",
                inline=True
            )
            embed.add_field(name="📢 Tình Trạng", value=f"⏳ **Đang chờ thanh toán** (Kiểm tra mỗi {POLLING_INTERVAL}s)", inline=True)
            embed.add_field(name="🔗 Link Thanh Toán", value=f"[**Thanh Toán Ngay qua MoMo**]({pay_url})", inline=False)
            embed.add_field(
                name="📋 Hướng Dẫn Thanh Toán",
                value=(
                    "1. **Mở MoMo:** Sử dụng ứng dụng MoMo chính thức (iOS/Android).\n"
                    "2. **Quét QR hoặc nhấp link:** Quét mã QR đính kèm hoặc nhấp link phía trên.\n"
                    f"3. **Nội dung chuyển khoản:** Phải chứa **`{noi_dung}`** chính xác.\n"
                    f"4. **Số tiền:** Đúng **{sotien:,} VNĐ** (không thêm phí).\n"
                    f"5. **Thời hạn:** Hoàn tất trong **{THOI_GIAN_CHO // 60} phút**.\n\n"
                    "**Thông tin thêm:**\n"
                    "- **Môi trường:** Production (giao dịch thực).\n"
                    f"- **Callback URLs:** IPN: `{ipnUrl}`, Redirect: `{redirectUrl}`.\n"
                    "- **Bảo mật:** Không chia sẻ mã giao dịch.\n"
                    "- **Hỗ trợ:** Gửi ảnh chụp màn hình lỗi đến **no-reply@nguyenquangdung.id.vn**."
                ),
                inline=False
            )
            embed.add_field(
                name="⚠️ Quy Định Pháp Lý",
                value="Giao dịch tuân thủ quy định Ngân Hàng Nhà Nước Việt Nam và MoMo. Không hoàn tiền nếu thanh toán sai mã hoặc nội dung.",
                inline=False
            )
            if not qr_file:
                embed.add_field(
                    name="⚠️ Lưu Ý",
                    value="Không tạo được mã QR. Vui lòng sử dụng link thanh toán hoặc liên hệ **no-reply@nguyenquangdung.id.vn**.",
                    inline=False
                )

            message = await interaction.followup.send(embed=embed, file=qr_file, ephemeral=False)

            giao_dich_active[ma_giao_dich] = GiaoDich(
                ma_giao_dich=ma_giao_dich,
                noi_dung=noi_dung,
                sotien=sotien,
                thoi_gian_tao=datetime.now(VN_TIMEZONE),
                channel_id=interaction.channel.id,
                user_id=ma_nguoi_dung,
                request_id=request_id,
                message_id=message.id,
                pay_url=pay_url,
            )

            await kiem_tra_trang_thai_thanh_toan(interaction, ma_giao_dich, sotien, noi_dung, ten_nguoi_dung)

        except Exception as e:
            sub_errors = response_data.get("subErrors", []) if response_data else []
            error_details = "\n".join([f"- {err['field']}: {err['message']}" for err in sub_errors]) if sub_errors else "Không có chi tiết lỗi."
            embed_loi = with_footer(discord.Embed(
                title="❌ Lỗi Thanh Toán",
                description=(
                    f"🚨 **Đã xảy ra lỗi:** {str(e)}\n\n"
                    f"**Mã Lỗi:** `{response_data.get('resultCode', 'N/A') if response_data else 'N/A'}`\n"
                    f"**Thông Điệp:** `{response_data.get('message', 'Unknown error') if response_data else 'Unknown error'}`\n"
                    f"**Chi Tiết:**\n{error_details}\n\n"
                    "**Kiểm Tra:**\n"
                    f"- **Mã Giao Dịch:** `{noi_dung if noi_dung else 'N/A'}`.\n"
                    "- **Ứng Dụng MoMo:** Phải là phiên bản chính thức.\n"
                    "- **MoMo Business:** Xác minh `partnerCode`, `accessKey`, `secretKey` trên [business.momo.vn](https://business.momo.vn).\n"
                    f"- **Callback URLs:** Đảm bảo `{ipnUrl}` và `{redirectUrl}` đã đăng ký.\n"
                    "- **Mạng:** Kiểm tra kết nối internet.\n\n"
                    "**Giải Quyết:**\n"
                    "- Thử lại sau 5 phút.\n"
                    "- Chụp màn hình và gửi đến **no-reply@nguyenquangdung.id.vn**."
                ),
                color=discord.Color.red(),
                timestamp=datetime.now(VN_TIMEZONE)
            ))
            await interaction.followup.send(embed=embed_loi, ephemeral=True)
        finally:
            if ten_nguoi_dung in giao_dich_dang_thuc_hien:
                giao_dich_dang_thuc_hien[ten_nguoi_dung].so_lan -= 1
                if giao_dich_dang_thuc_hien[ten_nguoi_dung].so_lan <= 0:
                    del giao_dich_dang_thuc_hien[ten_nguoi_dung]

    @app_commands.command(name="huygiaodich", description="Hủy một giao dịch thanh toán MoMo")
    @app_commands.describe(ma_giao_dich="Mã giao dịch cần hủy")
    async def huy_giao_dich(self, interaction: discord.Interaction, ma_giao_dich: int):
        await interaction.response.defer(ephemeral=True)
        try:
            if ma_giao_dich in giao_dich_active:
                del giao_dich_active[ma_giao_dich]
                embed = with_footer(discord.Embed(
                    title="✅ Đã Hủy Giao Dịch",
                    description=(
                        f"🗑 **Giao dịch `{ma_giao_dich}` đã được hủy thành công.**\n\n"
                        "**Chi Tiết:**\n"
                        "- **Lý do:** Yêu cầu hủy từ người dùng.\n"
                        "- **Hậu quả:** Giao dịch không còn được theo dõi.\n"
                        "- **Hành động:** Nếu đã thanh toán, liên hệ **no-reply@nguyenquangdung.id.vn** để kiểm tra trạng thái.\n\n"
                        "**Gợi ý:** Tạo giao dịch mới bằng `/thanhtoan` nếu cần."
                    ),
                    color=discord.Color.green(),
                    timestamp=datetime.now(VN_TIMEZONE)
                ))
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                raise Exception("Không tìm thấy giao dịch")
        except Exception as e:
            embed_loi = with_footer(discord.Embed(
                title="❌ Lỗi Hủy Giao Dịch",
                description=(
                    f"🚨 **Lỗi:** {str(e)}\n\n"
                    "**Kiểm Tra:**\n"
                    f"- **Mã Giao Dịch:** Đảm bảo `{ma_giao_dich}` đúng và giao dịch đang hoạt động.\n"
                    "- **Trạng Thái:** Giao dịch có thể đã hoàn tất hoặc không tồn tại.\n\n"
                    "**Gợi ý:**\n"
                    "- Kiểm tra mã giao dịch.\n"
                    "- Dùng `/thanhtoan` để xem giao dịch đang chờ.\n"
                    "- Liên hệ **no-reply@nguyenquangdung.id.vn** với chi tiết."
                ),
                color=discord.Color.red(),
                timestamp=datetime.now(VN_TIMEZONE)
            ))
            await interaction.followup.send(embed=embed_loi, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PaymentCommands(bot))

"""Service theo dõi giao dịch: lưu trạng thái, giới hạn tần suất, và polling xác nhận thanh toán."""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict

import discord

from constants.config import KENH_NHAN_VIEN, MAX_RETRIES, PARTNER_CODE, POLLING_INTERVAL, SO_TIEN_TOI_THIEU, THOI_GIAN_CHO, THOI_GIAN_GIOI_HAN, VN_TIMEZONE, ipnUrl, redirectUrl
from constants.momo_errors import DEFAULT_ERROR_INFO, MOMO_ERROR_CODES
from model.transaction import GiaoDich, RateLimitInfo
from services.momo_service import kiem_tra_giao_dich
from utils.embeds import FOOTER_ICON, FOOTER_TEXT, with_footer

# Trạng thái theo dõi (in-memory) dùng chung cho toàn bộ bot
giao_dich_dang_thuc_hien: Dict[str, RateLimitInfo] = {}
giao_dich_active: Dict[int, GiaoDich] = {}


def kiem_tra_gioi_han_thoi_gian(ten_nguoi_dung: str) -> bool:
    """True nếu người dùng cần chờ thêm trước khi được tạo giao dịch mới."""
    info = giao_dich_dang_thuc_hien.get(ten_nguoi_dung)
    if info and time.time() - info.lan_thu_truoc < THOI_GIAN_GIOI_HAN:
        return True
    return False


async def kiem_tra_trang_thai_thanh_toan(
    interaction: discord.Interaction,
    ma_giao_dich: int,
    sotien: int,
    noi_dung: str,
    ten_nguoi_dung: str,
) -> None:
    """Vòng lặp polling: kiểm tra trạng thái giao dịch mỗi POLLING_INTERVAL giây
    cho đến khi thành công, thất bại, hết hạn, hoặc lỗi quá số lần thử."""
    if ma_giao_dich not in giao_dich_active:
        logging.error(f"Giao dịch {ma_giao_dich} không tồn tại trong giao_dich_active")
        return

    giao_dich_info = giao_dich_active[ma_giao_dich]
    thoi_gian_bat_dau = giao_dich_info.thoi_gian_tao
    thoi_gian_bat_dau_time = thoi_gian_bat_dau.timestamp()
    order_id = f"GD{ma_giao_dich}"
    message_id = giao_dich_info.message_id
    channel = interaction.client.get_channel(interaction.channel.id)
    pay_url = giao_dich_info.pay_url
    user_id = giao_dich_info.user_id

    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            response = await kiem_tra_giao_dich(order_id)

            logging.debug(f"Transaction status for {order_id}: {response}")
            result_code = response.get("resultCode")
            error_info = MOMO_ERROR_CODES.get(result_code, DEFAULT_ERROR_INFO)

            # Try to fetch the message
            try:
                message = await channel.fetch_message(message_id)
            except discord.errors.NotFound:
                logging.error(f"Không thể lấy tin nhắn {message_id} trong kênh {channel.id}")
                await interaction.followup.send(
                    embed=with_footer(discord.Embed(
                        title="❌ Lỗi Hệ Thống",
                        description=(
                            f"🚨 **Không thể cập nhật trạng thái giao dịch `{ma_giao_dich}`.**\n\n"
                            "**Lý do:** Tin nhắn gốc không còn tồn tại.\n"
                            "**Hành động:**\n"
                            f"- Kiểm tra trạng thái giao dịch `{noi_dung}` trên MoMo.\n"
                            "- Tạo giao dịch mới bằng `/thanhtoan`.\n"
                            "- Liên hệ **no-reply@nguyenquangdung.id.vn** với mã giao dịch."
                        ),
                        color=discord.Color.red(),
                        timestamp=datetime.now(VN_TIMEZONE)
                    ))
                )
                del giao_dich_active[ma_giao_dich]
                return
            except Exception as e:
                logging.error(f"Lỗi khi lấy tin nhắn {message_id}: {e}")
                await interaction.followup.send(
                    embed=with_footer(discord.Embed(
                        title="❌ Lỗi Hệ Thống",
                        description=(
                            f"🚨 **Không thể cập nhật trạng thái giao dịch `{ma_giao_dich}`.**\n\n"
                            f"**Lỗi:** {str(e)}\n"
                            "**Hành động:**\n"
                            f"- Kiểm tra trạng thái giao dịch `{noi_dung}` trên MoMo.\n"
                            "- Tạo giao dịch mới bằng `/thanhtoan`.\n"
                            "- Liên hệ **no-reply@nguyenquangdung.id.vn** với mã giao dịch."
                        ),
                        color=discord.Color.red(),
                        timestamp=datetime.now(VN_TIMEZONE)
                    ))
                )
                del giao_dich_active[ma_giao_dich]
                return

            if result_code == 0:
                logging.info(f"Giao dịch {ma_giao_dich} đã hoàn thành thành công với số tiền {sotien:,} VNĐ")
                embed_thanh_cong = with_footer(discord.Embed(
                    title="🎉 Thanh Toán Thành Công",
                    description=(
                        f"✅ **Giao dịch `{ma_giao_dich}` với {sotien:,} VNĐ đã được xác nhận.**\n\n"
                        f"**Cảm ơn {ten_nguoi_dung} đã sử dụng dịch vụ!**\n"
                        "**Tiếp Theo:**\n"
                        "- Kiểm tra lịch sử giao dịch trên MoMo.\n"
                        "- Liên hệ nhà cung cấp để nhận sản phẩm/dịch vụ.\n"
                        "- Lưu mã giao dịch để tra cứu."
                    ),
                    color=discord.Color.green(),
                    timestamp=datetime.now(VN_TIMEZONE)
                ))
                embed_thanh_cong.set_footer(text=f"Cảm ơn bạn! | {FOOTER_TEXT}", icon_url=FOOTER_ICON)
                embed_thanh_cong.set_thumbnail(url="https://developers.momo.vn/static/img/logo.png")
                embed_thanh_cong.add_field(name="💰 Số Tiền", value=f"**{sotien:,} VNĐ**", inline=True)
                embed_thanh_cong.add_field(name="📝 Mã Giao Dịch", value=f"**`{noi_dung}`**", inline=True)
                embed_thanh_cong.add_field(name="🔑 Mã Yêu Cầu", value=f"`{giao_dich_info.request_id[:8]}...{giao_dich_info.request_id[-8:]}`", inline=True)
                embed_thanh_cong.add_field(name="👤 Người Thanh Toán", value=f"{ten_nguoi_dung} (ID: `{giao_dich_info.user_id}`)", inline=True)
                embed_thanh_cong.add_field(name="🏬 Cửa Hàng", value=f"`NGUYEN QUANG DUNG` (Partner: `{PARTNER_CODE[:4]}...`)", inline=True)
                embed_thanh_cong.add_field(name="💳 Phương Thức", value="**MoMo Wallet**", inline=True)
                embed_thanh_cong.add_field(name="⏰ Thời Gian Xác Nhận", value=f"<t:{int(datetime.now(VN_TIMEZONE).timestamp())}:F> (<t:{int(datetime.now(VN_TIMEZONE).timestamp())}:R>)", inline=True)
                embed_thanh_cong.add_field(name="📢 Tình Trạng", value="✅ **Thành công** (Xác nhận tự động)", inline=True)
                embed_thanh_cong.add_field(name="⚠️ Lưu Ý", value="Nếu không nhận được sản phẩm/dịch vụ, liên hệ **no-reply@nguyenquangdung.id.vn** với mã giao dịch.", inline=False)

                # Update the original message
                await message.edit(embed=embed_thanh_cong)

                # Ping the user in the channel
                try:
                    await interaction.followup.send(
                        content=f"<@{user_id}> Giao dịch `{ma_giao_dich}` đã hoàn thành thành công!",
                        ephemeral=False
                    )
                    logging.info(f"Đã ping người dùng <@{user_id}> về giao dịch {ma_giao_dich} trong kênh {channel.id}")
                except Exception as e:
                    logging.error(f"Lỗi khi ping người dùng <@{user_id}> cho giao dịch {ma_giao_dich}: {e}")
                    await interaction.followup.send(
                        embed=with_footer(discord.Embed(
                            title="⚠️ Không Thể Thông Báo",
                            description=(
                                f"✅ Giao dịch `{ma_giao_dich}` đã thành công, nhưng không thể gửi thông báo ping.\n"
                                "Vui lòng kiểm tra lịch sử giao dịch trên MoMo và liên hệ nhà cung cấp."
                            ),
                            color=discord.Color.yellow(),
                            timestamp=datetime.now(VN_TIMEZONE)
                        )),
                        ephemeral=True
                    )

                # Notify staff channel
                kenh_nhan_vien = interaction.client.get_channel(KENH_NHAN_VIEN)
                if kenh_nhan_vien:
                    try:
                        await kenh_nhan_vien.send(
                            embed=with_footer(discord.Embed(
                                title="✅ Giao Dịch Thành Công",
                                description=(
                                    f"💸 **Giao dịch `{ma_giao_dich}`**: **{sotien:,} VNĐ** từ **{ten_nguoi_dung}** (ID: `{giao_dich_info.user_id}`).\n\n"
                                    f"**Chi Tiết:**\n"
                                    f"- **Cửa hàng:** `NGUYEN QUANG DUNG`\n"
                                    f"- **Thời gian:** <t:{int(datetime.now(VN_TIMEZONE).timestamp())}:F>\n"
                                    f"- **Mã yêu cầu:** `{giao_dich_info.request_id[:8]}...`\n"
                                    f"- **Hành động:** Xử lý đơn hàng ngay."
                                ),
                                color=discord.Color.green(),
                                timestamp=datetime.now(VN_TIMEZONE)
                            ))
                        )
                        logging.info(f"Đã gửi thông báo đến kênh nhân viên cho giao dịch {ma_giao_dich}")
                    except Exception as e:
                        logging.error(f"Lỗi gửi thông báo đến kênh nhân viên: {e}")

                del giao_dich_active[ma_giao_dich]
                logging.info(f"Giao dịch {ma_giao_dich} đã hoàn tất và xóa khỏi giao_dich_active")
                return  # Exit the loop after success

            elif error_info["final_status"]:
                embed_that_bai = with_footer(discord.Embed(
                    title="❌ Giao Dịch Thất Bại",
                    description=(
                        f"🚨 **Giao dịch `{ma_giao_dich}` với {sotien:,} VNĐ đã thất bại.**\n\n"
                        f"**Lý do:** {error_info['description']} (Mã lỗi: `{result_code}`)\n"
                        f"**Loại lỗi:** {error_info['type']}\n"
                        f"**Hành động đề xuất:** {error_info['action'] or 'Tạo giao dịch mới bằng `/thanhtoan`.'}\n\n"
                        "**Tiếp Theo:**\n"
                        "- Kiểm tra lịch sử giao dịch trên MoMo.\n"
                        f"- Liên hệ **no-reply@nguyenquangdung.id.vn** với mã giao dịch `{noi_dung}` nếu cần hỗ trợ."
                    ),
                    color=discord.Color.red(),
                    timestamp=datetime.now(VN_TIMEZONE)
                ))
                embed_that_bai.add_field(name="💰 Số Tiền", value=f"**{sotien:,} VNĐ**", inline=True)
                embed_that_bai.add_field(name="📝 Mã Giao Dịch", value=f"**`{noi_dung}`**", inline=True)
                embed_that_bai.add_field(name="🔑 Mã Yêu Cầu", value=f"`{giao_dich_info.request_id[:8]}...{giao_dich_info.request_id[-8:]}`", inline=True)
                embed_that_bai.add_field(name="👤 Người Thanh Toán", value=f"{ten_nguoi_dung} (ID: `{giao_dich_info.user_id}`)", inline=True)
                embed_that_bai.add_field(name="🏬 Cửa Hàng", value=f"`NGUYEN QUANG DUNG` (Partner: `{PARTNER_CODE[:4]}...`)", inline=True)
                embed_that_bai.add_field(name="⏰ Thời Gian Kiểm Tra", value=f"<t:{int(datetime.now(VN_TIMEZONE).timestamp())}:F> (<t:{int(datetime.now(VN_TIMEZONE).timestamp())}:R>)", inline=True)
                await message.edit(embed=embed_that_bai)

                del giao_dich_active[ma_giao_dich]
                return

            elif result_code in [1000, 7000, 7002, 9000]:
                time_remaining = THOI_GIAN_CHO - int(time.time() - thoi_gian_bat_dau_time)
                minutes_remaining = max(0, time_remaining // 60)
                embed = with_footer(discord.Embed(
                    title="💳 Yêu Cầu Thanh Toán MoMo",
                    description=(
                        f"**Chào {ten_nguoi_dung},**\n\n"
                        "Cảm ơn bạn đã sử dụng dịch vụ nPos! Vui lòng làm theo hướng dẫn để hoàn tất thanh toán:\n"
                        "- **Quét QR hoặc nhấp link:** Mở ứng dụng MoMo chính thức.\n"
                        "- **Kiểm tra mã giao dịch:** Đảm bảo nội dung chuyển khoản chứa chính xác mã dưới đây.\n"
                        f"- **Thời hạn:** Giao dịch sẽ hết hạn sau **{minutes_remaining} phút** còn lại.\n\n"
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
                embed.add_field(name="🔑 Mã Yêu Cầu", value=f"`{giao_dich_info.request_id[:8]}...{giao_dich_info.request_id[-8:]}`", inline=True)
                embed.add_field(name="👤 Người Thanh Toán", value=f"{ten_nguoi_dung} (ID: `{giao_dich_info.user_id}`)", inline=True)
                embed.add_field(name="🏬 Cửa Hàng", value=f"`NGUYEN QUANG DUNG` (Partner: `{PARTNER_CODE[:4]}...`)", inline=True)
                embed.add_field(name="💳 Phương Thức", value="**MoMo Wallet** (QR Code & Link)", inline=True)
                embed.add_field(name="⏰ Thời Gian Tạo", value=f"<t:{int(thoi_gian_bat_dau_time)}:F> (<t:{int(thoi_gian_bat_dau_time)}:R>)", inline=True)
                embed.add_field(name="⏳ Hết Hạn", value=f"<t:{int((thoi_gian_bat_dau + timedelta(seconds=THOI_GIAN_CHO)).timestamp())}:F> (<t:{int((thoi_gian_bat_dau + timedelta(seconds=THOI_GIAN_CHO)).timestamp())}:R>)", inline=True)
                embed.add_field(name="📢 Tình Trạng", value=f"⏳ **Đang chờ thanh toán** (Còn {minutes_remaining} phút, kiểm tra mỗi {POLLING_INTERVAL}s)", inline=True)
                embed.add_field(name="🔗 Link Thanh Toán", value=f"[**Thanh Toán Ngay qua MoMo**]({pay_url})", inline=False)
                embed.add_field(
                    name="📋 Hướng Dẫn Thanh Toán",
                    value=(
                        "1. **Mở MoMo:** Sử dụng ứng dụng MoMo chính thức (iOS/Android).\n"
                        "2. **Quét QR hoặc nhấp link:** Quét mã QR đính kèm hoặc nhấp link phía trên.\n"
                        f"3. **Nội dung chuyển khoản:** Phải chứa **`{noi_dung}`** chính xác.\n"
                        f"4. **Số tiền:** Đúng **{sotien:,} VNĐ** (không thêm phí).\n"
                        f"5. **Thời hạn:** Hoàn tất trong **{minutes_remaining} phút**.\n\n"
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
                await message.edit(embed=embed)
            else:
                logging.warning(f"Trạng thái không xác định cho giao dịch {ma_giao_dich}: resultCode={result_code}")

            if time.time() - thoi_gian_bat_dau_time > THOI_GIAN_CHO:
                embed_het_thoi_gian = with_footer(discord.Embed(
                    title="⏰ Hết Thời Gian Xác Nhận",
                    description=(
                        f"⏳ **Giao dịch `{ma_giao_dich}` không được xác nhận trong {THOI_GIAN_CHO // 60} phút.**\n\n"
                        "**Lý do:** Chưa thanh toán hoặc lỗi kết nối.\n"
                        "**Hành động:**\n"
                        "- Kiểm tra lịch sử giao dịch trên MoMo.\n"
                        "- Tạo giao dịch mới bằng `/thanhtoan`.\n"
                        "- Liên hệ **no-reply@nguyenquangdung.id.vn** nếu cần hỗ trợ."
                    ),
                    color=discord.Color.red(),
                    timestamp=datetime.now(VN_TIMEZONE)
                ))
                await message.edit(embed=embed_het_thoi_gian)
                del giao_dich_active[ma_giao_dich]
                return

        except Exception as e:
            retry_count += 1
            logging.error(f"Lỗi kiểm tra trạng thái cho {ma_giao_dich} (lần {retry_count}/{MAX_RETRIES}): {e}")
            if retry_count >= MAX_RETRIES:
                embed_loi = with_footer(discord.Embed(
                    title="❌ Lỗi Kiểm Tra Giao Dịch",
                    description=(
                        f"🚨 **Không thể kiểm tra giao dịch `{ma_giao_dich}`.**\n\n"
                        f"**Lỗi:** {str(e)}\n"
                        f"**Số lần thử:** {MAX_RETRIES} (đã hết).\n\n"
                        "**Kiểm Tra:**\n"
                        f"- **Mã Giao Dịch:** `{noi_dung}` (xem trên MoMo).\n"
                        "- **Kết nối API:** Có thể MoMo API tạm gián đoạn.\n\n"
                        "**Giải Quyết:**\n"
                        "- Kiểm tra thủ công trên MoMo.\n"
                        "- Thử tạo giao dịch mới.\n"
                        "- Gửi ảnh chụp màn hình lỗi đến **no-reply@nguyenquangdung.id.vn**."
                    ),
                    color=discord.Color.red(),
                    timestamp=datetime.now(VN_TIMEZONE)
                ))
                await message.edit(embed=embed_loi)
                del giao_dich_active[ma_giao_dich]
                return
        await asyncio.sleep(POLLING_INTERVAL)

"""Tiện ích dựng Discord Embed dùng chung trong toàn bộ bot."""
import discord

FOOTER_TEXT = "Hệ Hống nPos - An Toàn - Bảo Mật | Phát Triển Bởi NGUYEN QUANG DUNG"
FOOTER_ICON = "https://developers.momo.vn/static/img/favicon.png"


def with_footer(embed: discord.Embed, text: str = FOOTER_TEXT, icon_url: str = FOOTER_ICON) -> discord.Embed:
    """Gắn footer chuẩn của hệ thống (nPos) vào một embed và trả về chính embed đó."""
    embed.set_footer(text=text, icon_url=icon_url)
    return embed

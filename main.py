"""Điểm khởi chạy chính của bot Discord thanh toán MoMo."""
import asyncio
import logging

import discord
from discord.ext import commands

from constants.config import TOKEN_BOT, PARTNER_CODE, validate_config
from utils.logger import setup_logging
from utils.security import hash_sensitive

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        logging.info(f'Đăng nhập với {bot.user} với MoMo (partnerCode: {hash_sensitive(PARTNER_CODE)})')
        logging.info("Bot đã sẵn sàng hoạt động")
    except Exception as e:
        logging.error(f"Lỗi khởi tạo bot: {e}")
        raise


async def main():
    setup_logging()
    validate_config()
    async with bot:
        await bot.load_extension("command.payment_commands")
        await bot.start(TOKEN_BOT)


if __name__ == "__main__":
    asyncio.run(main())

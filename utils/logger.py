"""Cấu hình ghi log dùng chung cho toàn bộ bot."""
import logging


def setup_logging() -> None:
    """Cấu hình ghi log với encoding UTF-8, ghi ra cả file bot.log và console."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

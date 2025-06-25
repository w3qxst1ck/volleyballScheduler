import os
import sys

from loguru import logger

log_folder = "logs"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

# иначе логи дублируются
logger.remove()

# вывод в консоль
logger.add(
    sys.stdout,
    level="DEBUG",
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{file}:{line}</cyan> | <level>{message}</level>"
)

# запись в .log файл
log_file_path = os.path.join(log_folder, "bot.log")

# запись всех логов
logger.add(
    log_file_path,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}",
    rotation="100 MB",
    retention="60 days",
)

# запись ошибок
error_log_file_path = os.path.join(log_folder, "bot_errors.log")
logger.add(
    error_log_file_path,
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}",
    rotation="100 MB",
    retention="60 days",
)

logger = logger

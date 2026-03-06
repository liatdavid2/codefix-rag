import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    filename="logs/app.log",
    filemode="a"
)

logger = logging.getLogger()
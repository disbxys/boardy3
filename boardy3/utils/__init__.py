import logging


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    stream_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)

    return logger
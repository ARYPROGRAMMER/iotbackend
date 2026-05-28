import logging
from logging.handlers import RotatingFileHandler


def configure_logging(app):
    level = getattr(logging, app.config["LOG_LEVEL"], logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    app.logger.setLevel(level)
    for handler in list(app.logger.handlers):
        app.logger.removeHandler(handler)
        handler.close()
    app.logger.propagate = False

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    app.logger.addHandler(stream_handler)

    file_handler = RotatingFileHandler(
        app.config["LOG_DIR"] / "stealthera-api.log",
        maxBytes=5_000_000,
        backupCount=5,
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

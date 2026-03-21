import logging
from logging.handlers import RotatingFileHandler

class RotatingFileHandlerWithCleanup(RotatingFileHandler):
    def __init__(self, filename, maxBytes=3*1024*1024, backupCount=3, *args, **kwargs):
        super().__init__(filename, maxBytes=maxBytes, backupCount=backupCount, *args, **kwargs)

    def emit(self, record):
        try:
            super().emit(record)
        except Exception as e:
            logging.error(f'Error writing to log: {e}'): Implement file logging with rotation (keep last 3 runs)
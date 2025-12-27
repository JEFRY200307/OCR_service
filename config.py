import os

# Configuración general del servicio OCR
class Settings:
    DATA_DIR = os.getenv("DATA_DIR", "data")
    LOG_FILE = os.getenv("LOG_FILE", "ocr_service.log")
    OCR_LANG = os.getenv("OCR_LANG", "es")
    OCR_USE_TEXTLINE_ORIENTATION = True

settings = Settings()

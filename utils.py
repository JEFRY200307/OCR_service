import logging
import os
from config import settings  # <-- Importa settings

def setup_logger(log_file=None):
    if log_file is None:
        log_file = settings.LOG_FILE  # Usa el valor de config.py
    log_path = os.path.abspath(log_file)
    log_dir = os.path.dirname(log_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    if not os.path.exists(log_path):
        with open(log_path, "a", encoding="utf-8"):
            pass
    logger = logging.getLogger("ocr_service")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(log_path)
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(fh)
    return logger

logger = setup_logger()

def log_extraction(filename, extracted_text, total, category, confidence, show_full_text=False):
    if show_full_text:
        logger.info(f"Archivo: {filename} | Categoria: {category} | Confianza: {confidence} | Total: {total} | Texto extraído: {extracted_text}")
    else:
        logger.info(f"Archivo: {filename} | Categoria: {category} | Confianza: {confidence} | Total: {total} | Texto extraído: {extracted_text[:100]}...")
import re
import numpy as np
import cv2
from paddleocr import PaddleOCR
from config import settings
from utils import log_extraction
import os
# Inicialización del motor OCR
ocr = PaddleOCR(lang=settings.OCR_LANG, use_textline_orientation=settings.OCR_USE_TEXTLINE_ORIENTATION)

def allowed_file(filename):
    allowed_ext = {"jpeg", "jpg", "png"}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_ext


def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    contrast = clahe.apply(gray)
    thresh = cv2.adaptiveThreshold(contrast, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 15)
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

# Lectura de imagen desde bytes
def read_image_from_bytes(content: bytes):
    nparr = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen. Formato no soportado o archivo corrupto.")
    return img

# Extracción de datos específicos del texto OCR
def extract_invoice_data(text):
    # Preprocesamiento
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    text_lower = text.lower()

    # RUC: busca variantes y tolera separadores
    ruc = None
    for pattern in [
        r'r[\s\.:_-]*u[\s\.:_-]*c[\s\.:_-]*[:\s\.:_-]*([0-9]{11})',
        r'\b([0-9]{11})\b'
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            ruc = m.group(1)
            break

    # Serie y número: busca variantes y separadores
    serie = None
    numero = None
    serie_num_patterns = [
        r'(?:serie|ser\.?|ser:|ser\s|f[a-z]?|b[a-z]?)[\s\.:_-]*([a-z0-9]{3,5})',
        r'([fb][0-9]{3,5})',
        r'([a-z]{1,3}[0-9]{3,5})',
    ]
    numero_patterns = [
        r'(?:n[\s\.:_-]*[ro°º]?|num[\s\.:_-]*|número[\s\.:_-]*|no[\s\.:_-]*|nº[\s\.:_-]*|n°[\s\.:_-]*|f[a-z]?|b[a-z]?)[\s\.:_-]*([0-9]{5,10})',
        r'([0-9]{6,10})'
    ]
    # Buscar serie y número en líneas
    for i, line in enumerate(lines):
        # Serie
        for pat in serie_num_patterns:
            m = re.search(pat, line, re.IGNORECASE)
            if m:
                serie = m.group(1)
                break
        # Número
        for pat in numero_patterns:
            m = re.search(pat, line, re.IGNORECASE)
            if m:
                numero = m.group(1)
                break
        if serie and numero:
            break
    # Si no se encontró, buscar juntos (ej: F001-123456)
    if not (serie and numero):
        m = re.search(r'([fb][0-9]{3,5})[-\s:]*([0-9]{5,10})', text, re.IGNORECASE)
        if m:
            serie = m.group(1)
            numero = m.group(2)

    # Fecha: busca variantes y formatos
    fecha = None
    fecha_patterns = [
        r'(\d{2}[/-]\d{2}[/-]\d{4})',
        r'(\d{4}[/-]\d{2}[/-]\d{2})',
        r'(\d{2}[. ]\d{2}[. ]\d{4})',
    ]
    for i, line in enumerate(lines):
        if any(w in line.lower() for w in ["fecha", "emision", "fec.", "f. emision"]):
            for pat in fecha_patterns:
                m = re.search(pat, line)
                if m:
                    fecha = m.group(1)
                    break
        if fecha:
            break
    if not fecha:
        for pat in fecha_patterns:
            m = re.search(pat, text)
            if m:
                fecha = m.group(1)
                break

    # Tipo de documento
    tipo_documento = "01" if "factura" in text_lower else None

    # Moneda
    moneda = None
    if re.search(r's/|s/\.|soles', text_lower):
        moneda = "PEN"
    elif re.search(r'usd|dólares|dolares', text_lower):
        moneda = "USD"

    # Importes: base, igv, total (busca variantes y líneas cercanas)
    def buscar_importe(palabras, lines):
        for i, line in enumerate(lines):
            if any(p in line.lower() for p in palabras):
                # Busca monto en la misma línea
                m = re.search(r'(\d{1,4}[.,]\d{2,})', line)
                if m:
                    return float(m.group(1).replace(',', '.'))
                # Busca en la siguiente línea
                if i+1 < len(lines):
                    m = re.search(r'(\d{1,4}[.,]\d{2,})', lines[i+1])
                    if m:
                        return float(m.group(1).replace(',', '.'))
        return None

    base = buscar_importe(["gravado", "valor venta", "subtotal", "op. gravada", "sub total"], lines)
    igv = buscar_importe(["igv", "i.g.v"], lines)
    total = buscar_importe(["total a pagar", "importe total", "total", "son:"], lines)

    # Items detalle: igual que antes, pero más tolerante
    items = []
    for line in lines:
        if re.search(r'[A-ZÁÉÍÓÚÑ]{3,}', line, re.IGNORECASE) and not re.search(r'(FACTURA|TOTAL|GRAVADO|IGV|IMPORTE|RUC|ELECTRONICA|BOLETA|SON|SUBTOTAL|VALOR|FECHA|N°|NRO|NUMERO|CANCELADO|CLIENTE|DIRECCION|MONEDA|EMISION|VENDEDOR|CREDITO|CONTADO|OP\.|IGV|BASE|SUB|IMPORTE|P.UNIT|CANT|DESCRIPCION|UNIDAD|MEDIDA|CODIGO|FIRMA|SELLO|SUPERVISOR|ALMACEN|VB)', line, re.IGNORECASE):
            items.append(line.strip())

    return {
        "ruc_emisor": ruc,
        "tipo_documento": tipo_documento,
        "serie": serie,
        "numero": numero,
        "fecha_emision": fecha,
        "moneda": moneda,
        "importes": {
            "base_imponible": base,
            "igv": igv,
            "total": total
        }
    }, items

# Simple detección del tipo de documento basado en palabras clave
def detect_doc_type(text_content):
    if "electrónica" in text_content.lower() or "electronica" in text_content.lower():
        return "comprobante_electronico"
    return "comprobante_fisico"

def clean_currency(text):
    match = re.search(r'(S/|S/\.|USD)?\s*(\d{1,4}[.,]\d{2})', text)
    if match:
        return match.group(2).replace(',', '.')
    return None

# Procesamiento de imagen desde bytes
def process_image_bytes(content: bytes, filename: str):
    img = read_image_from_bytes(content)
    img_prep = preprocess_image(img)
    # Guardar imagen preprocesada para depuración
    # try:
    #     import cv2
    #     cv2.imwrite(f"preprocessed_{filename}", img_prep)
    # except Exception as e:
    #     pass
    result = ocr.ocr(img_prep)
    # Loggear resultado crudo de PaddleOCR
    import logging
    logging.getLogger("ocr_service").info(f"Resultado crudo OCR para {filename}: {result}")
    if not result or not result[0]:
        return {"success": False, "message": "No text detected"}
    # Extraer texto de 'rec_texts' si está presente
    raw_lines = []
    if isinstance(result[0], dict) and 'rec_texts' in result[0]:
        raw_lines = result[0]['rec_texts']
    else:
        for line in result[0]:
            if (
                isinstance(line, (list, tuple)) and len(line) > 1
                and isinstance(line[1], (list, tuple)) and len(line[1]) > 1
                and isinstance(line[1][0], str)
            ):
                raw_lines.append(line[1][0])
    full_text = "\n".join(raw_lines)
    log_extraction(filename, full_text, None, None, 0, show_full_text=True)
    # Extraer info estructurada y categoría
    data_sunat, items_detalle = extract_invoice_data(full_text)
    category = detect_doc_type(full_text)
    return {
        "filename": filename,
        "raw_text": full_text,
        "meta": {
            "filename": filename,
            "category": category
        },
        "data_sunat": data_sunat,
        "items_detalle": items_detalle
    }

# Procesamiento por lotes para las pruebas locales
def batch_extract_from_data_folder(data_dir="data"):
    results = []
    for fname in os.listdir(data_dir):
        if fname.lower().endswith(('.jpeg', '.jpg', '.png')):
            fpath = os.path.join(data_dir, fname)
            with open(fpath, "rb") as f:
                try:
                    res = process_image_bytes(f.read(), fname)
                    results.append(res)
                except Exception as e:
                    results.append({"filename": fname, "error": str(e)})
    return results

# Procesamiento de imagen desde URL
def process_image_from_url(url: str):
    import requests
    filename = url.split("/")[-1]
    if not allowed_file(filename):
        return {"success": False, "error": "El archivo debe ser una imagen jpeg, jpg o png"}
    resp = requests.get(url)
    if resp.status_code != 200:
        return {"success": False, "error": f"No se pudo descargar la imagen: {resp.status_code}"}
    return process_image_bytes(resp.content, filename)

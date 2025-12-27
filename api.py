from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from ocr_service import allowed_file, process_image_bytes, process_image_from_url

router = APIRouter()

@router.get("/")
def health():
    return {"status": "running", "engine": "PaddleOCR-CPU"}

@router.post("/extract")
async def extract_invoice(file: UploadFile = File(...)):
    if not allowed_file(file.filename):
        raise HTTPException(400, "El archivo debe ser una imagen jpeg, jpg o png")
    content = await file.read()
    return process_image_bytes(content, file.filename)

@router.get("/extract/url")
def extract_invoice_url(url: str = Query(..., description="URL de la imagen a procesar")):
    return process_image_from_url(url)
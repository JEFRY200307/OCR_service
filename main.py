from fastapi import FastAPI
from api import router

app = FastAPI(title="Peri OCR Engine")
app.include_router(router)
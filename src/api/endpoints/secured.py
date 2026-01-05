"""
Secured Model Endpoint
Service pour le modèle sécurisé
"""

from fastapi import APIRouter, File, UploadFile

router = APIRouter(prefix="/secured", tags=["secured"])

@router.post("/detect")
async def detect_secured(file: UploadFile = File(...)):
    """Détection avec le modèle sécurisé"""
    return {"model": "secured", "result": "processing"}

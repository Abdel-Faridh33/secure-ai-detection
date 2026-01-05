"""
Baseline Model Endpoint
Service pour le modèle non sécurisé
"""

from fastapi import APIRouter, File, UploadFile

router = APIRouter(prefix="/baseline", tags=["baseline"])

@router.post("/detect")
async def detect_baseline(file: UploadFile = File(...)):
    """Détection avec le modèle baseline"""
    return {"model": "baseline", "result": "processing"}

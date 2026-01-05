"""
Comparison Endpoint
Service de comparaison des modèles
"""

from fastapi import APIRouter, File, UploadFile

router = APIRouter(prefix="/compare", tags=["comparison"])

@router.post("/analyze")
async def compare_models(file: UploadFile = File(...)):
    """Compare les résultats des deux modèles"""
    return {"baseline": {}, "secured": {}, "comparison": {}}

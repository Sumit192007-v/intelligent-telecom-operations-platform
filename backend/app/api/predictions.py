from fastapi import APIRouter
from pydantic import BaseModel

from ml.src.predict import predict_latency


router = APIRouter(prefix="/predict", tags=["ML Prediction"])


class PredictionRequest(BaseModel):
    operator: str
    hour: int
    day_of_week: int
    five_g_frequency_mhz: float | None = None
    five_g_pci: float | None = None
    lte_earfcn: float | None = None


@router.post("/")
def predict_network_latency(data: PredictionRequest):
    return predict_latency(
        operator=data.operator,
        hour=data.hour,
        day_of_week=data.day_of_week,
        five_g_frequency_mhz=data.five_g_frequency_mhz,
        five_g_pci=data.five_g_pci,
        lte_earfcn=data.lte_earfcn,
    )
from fastapi import APIRouter
from pydantic import BaseModel

from ml.src.predict import predict_latency


router = APIRouter(prefix="/predict", tags=["ML Prediction"])


class PredictionRequest(BaseModel):
    operator: str
    hour: int
    day_of_week: int
    frequency: float | None = None
    pci: float | None = None
    earfcn: float | None = None
    five_g_frequency_mhz: float | None = None
    five_g_pci: float | None = None
    lte_earfcn: float | None = None


@router.post("/")
def predict_network_latency(data: PredictionRequest):
    return predict_latency(
        operator=data.operator,
        hour=data.hour,
        day_of_week=data.day_of_week,
        five_g_frequency_mhz=(
            data.frequency
            if data.frequency is not None
            else data.five_g_frequency_mhz
        ),
        five_g_pci=data.pci if data.pci is not None else data.five_g_pci,
        lte_earfcn=data.earfcn if data.earfcn is not None else data.lte_earfcn,
    )
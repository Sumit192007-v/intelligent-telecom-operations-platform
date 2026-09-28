from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import NetworkMeasurement

router = APIRouter(
    prefix="/network",
    tags=["Network"]
)


@router.get("/measurements")
def get_network_measurements(
    operator: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(NetworkMeasurement)

    if operator:
        query = query.filter(
            NetworkMeasurement.operator == operator
        )

    measurements = (
        query
        .order_by(NetworkMeasurement.timestamp.desc())
        .limit(500)
        .all()
    )

    return [
        {
            "id": measurement.id,
            "operator": measurement.operator,
            "timestamp": measurement.timestamp,
            "latitude": measurement.latitude,
            "longitude": measurement.longitude,
            "download_mbps": measurement.download_mbps,
            "upload_mbps": measurement.upload_mbps,
            "rtt_ms": measurement.rtt_ms,
            "network_technology": measurement.network_technology,
            "5g_frequency_mhz": measurement.five_g_frequency_mhz,
            "5g_pci": measurement.five_g_pci,
            "lte_earfcn": measurement.lte_earfcn,
            "cell_event": measurement.cell_event,
        }
        for measurement in measurements
    ]
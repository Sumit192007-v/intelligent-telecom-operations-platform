from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import numpy as np
from sklearn.neighbors import BallTree

from app.auth import require_role
from app.database import get_db
from app.models.models import Complaint, NetworkMeasurement, User

router = APIRouter(
    prefix="/network",
    tags=["Network"]
)

MAP_RADIUS_KM = 1.0
EARTH_RADIUS_KM = 6371.0


@router.get("/measurements")
def get_network_measurements(
    operator: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("staff")),
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


@router.get("/map-data")
def get_network_map_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("staff")),
):
    measurements = (
        db.query(
            NetworkMeasurement.id.label("id"),
            NetworkMeasurement.operator.label("operator"),
            NetworkMeasurement.latitude.label("latitude"),
            NetworkMeasurement.longitude.label("longitude"),
            NetworkMeasurement.rtt_ms.label("rtt_ms"),
            NetworkMeasurement.five_g_frequency_mhz.label("frequency"),
            NetworkMeasurement.five_g_pci.label("pci"),
            NetworkMeasurement.lte_earfcn.label("earfcn"),
        )
        .filter(NetworkMeasurement.rtt_ms.isnot(None))
        .order_by(NetworkMeasurement.timestamp.desc())
        .limit(5000)
        .all()
    )
    pending_locations = (
        db.query(Complaint.latitude, Complaint.longitude)
        .filter(
            Complaint.status == "Pending",
            Complaint.latitude.isnot(None),
            Complaint.longitude.isnot(None),
        )
        .all()
    )

    measurement_coordinates = np.radians([
        [measurement.latitude, measurement.longitude]
        for measurement in measurements
    ])
    if pending_locations and measurements:
        complaint_tree = BallTree(
            np.radians(pending_locations),
            metric="haversine",
        )
        complaint_counts = complaint_tree.query_radius(
            measurement_coordinates,
            r=MAP_RADIUS_KM / EARTH_RADIUS_KM,
            count_only=True,
        )
    else:
        complaint_counts = np.zeros(len(measurements), dtype=int)

    results = []
    for measurement, nearby_complaints in zip(measurements, complaint_counts):
        nearby_complaints = int(nearby_complaints)
        latency = float(measurement.rtt_ms)
        if latency >= 75 or nearby_complaints >= 2:
            status = "red"
        elif 50 <= latency < 75 or nearby_complaints == 1:
            status = "orange"
        else:
            status = "green"

        results.append({
            "id": int(measurement.id),
            "lat": float(measurement.latitude),
            "lng": float(measurement.longitude),
            "operator": measurement.operator,
            "latency": latency,
            "frequency": measurement.frequency,
            "pci": measurement.pci,
            "earfcn": measurement.earfcn,
            "complaints": nearby_complaints,
            "status": status,
        })

    return results
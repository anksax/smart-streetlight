import json
import logging
import os
import uuid
from datetime import datetime, timezone

import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient, UpdateMode
from azure.identity import ManagedIdentityCredential
from lighting import decide
from validation import validate

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


def response(data, status=200):
    return func.HttpResponse(json.dumps(data), status_code=status,
                             mimetype="application/json")


@app.route(route="process-reading", methods=["POST"])
def process_reading(req):
    try:
        data = req.get_json()
        sensor_timestamp = validate(data)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return response({"error": str(exc)}, 400)
    now = datetime.now(timezone.utc)
    try:
        with TableServiceClient(os.environ["TABLE_STORAGE_ENDPOINT"],
                                credential=ManagedIdentityCredential()) as service:
            current = service.get_table_client("LampState")
            try:
                previous = current.get_entity(data["lamp_id"], "latest")
            except ResourceNotFoundError:
                previous = None
            decision = decide(float(data["ambient_lux"]), float(data["simulation_hour"]),
                              data["motion"], previous, now)
            fields = dict(sensor_timestamp=sensor_timestamp.isoformat(),
                          received_at=now.isoformat(),
                          ambient_lux=float(data["ambient_lux"]),
                          simulation_hour=float(data["simulation_hour"]),
                          motion=data["motion"],
                          activity_position=data.get("activity_position", 0),
                          demo_mode=data.get("demo_mode", False), **decision)
            service.get_table_client("Readings").create_entity(dict(
                PartitionKey=data["lamp_id"],
                RowKey=now.strftime("%Y%m%dT%H%M%S%f") + "_" + uuid.uuid4().hex,
                **fields))
            current.upsert_entity(dict(PartitionKey=data["lamp_id"], RowKey="latest",
                                       **fields), mode=UpdateMode.REPLACE)
        return response(dict(lamp_id=data["lamp_id"], stored=True, **decision))
    except Exception:
        logging.exception("Reading storage failed")
        return response({"error": "Storage operation failed"}, 503)

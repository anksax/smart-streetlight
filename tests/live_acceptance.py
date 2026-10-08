"""Opt-in live Function -> Storage -> dashboard API acceptance evidence.

Run on the Azure VM to include the VM/HTTP portion of the assignment.
Uses isolated QA lamp IDs, never the five production/demo lamps.
"""
import argparse
import csv
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib import request, error


def call(url, payload=None, key=None):
    headers = {}
    if key:
        headers["x-functions-key"] = key
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    try:
        with request.urlopen(request.Request(url, data=body, headers=headers), timeout=20) as reply:
            return reply.status, json.load(reply)
    except error.HTTPError as exc:
        try:
            result = json.loads(exc.read().decode())
        except (ValueError, UnicodeDecodeError):
            result = {"error": "Non-JSON HTTP error"}
        return exc.code, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="test-results")
    args = parser.parse_args()
    url, key = os.environ["STREETLIGHT_URL"], os.environ["STREETLIGHT_KEY"]
    dashboard = os.environ["DASHBOARD_URL"].rstrip("/")
    run_id = uuid.uuid4().hex[:8]
    # Each sequence starts with a unique lamp, so previous state is reproducible.
    cases = [
        ("normal_day", [(600,12,False,200,"OFF",0)]),
        ("normal_idle", [(40,22,False,200,"DIM",30)]),
        ("normal_motion", [(40,22,True,200,"ON",100)]),
        ("dark_day", [(40,12,False,200,"DIM",50)]),
        ("boundary_fresh", [(299,22,False,200,"DIM",30),(300,22,False,200,"OFF",0),(301,22,False,200,"OFF",0)]),
        ("hysteresis", [(600,22,False,200,"OFF",0),(280,22,False,200,"OFF",0),(279,22,False,200,"DIM",30),(299,22,False,200,"DIM",30),(300,22,False,200,"OFF",0)]),
        ("motion_hold", [(40,22,True,200,"ON",100),(40,22,False,200,"ON",100),(40,22,False,200,"DIM",30)]),
        ("invalid_lux", [(-10,22,False,400,None,None)]),
        ("invalid_hour", [(40,24,False,400,None,None)]),
        ("invalid_motion", [(40,22,"false",400,None,None)]),
    ]
    results = []
    for index, (name, steps) in enumerate(cases):
        lamp = f"QA_{run_id}_{index:02}"
        for step, (lux,hour,motion,code,state,brightness) in enumerate(steps):
            if name == "motion_hold" and step == 2:
                time.sleep(13)
            reading = dict(timestamp=datetime.now(timezone.utc).isoformat(),lamp_id=lamp,
                           ambient_lux=lux,simulation_hour=hour,motion=motion)
            status, actual, stored = None, {}, False
            detail = ""
            try:
                status, actual = call(url, reading, key)
                # Poll the actual dashboard storage reader; do not trust stored:true alone.
                for attempt in range(5):
                    history_status, history = call(dashboard+"/api/history?lamp="+lamp)
                    records = history.get("records", [])
                    stored = any(r.get("sensor_timestamp")==reading["timestamp"] for r in records)
                    if history_status != 200:
                        raise RuntimeError("Dashboard history HTTP "+str(history_status))
                    if stored or code != 200:
                        break
                    time.sleep(1)
                passed = status == code and (
                    actual.get("state")==state and actual.get("brightness")==brightness
                    and actual.get("stored") is True and stored if code == 200
                    else "error" in actual and not stored
                )
            except Exception as exc:
                passed = False
                detail = type(exc).__name__ + ": request or evidence check failed"
            row = dict(test=name,step=step+1,lamp_id=lamp,input=reading,
                       expected_http=code,expected_state=state,expected_brightness=brightness,
                       actual_http=status,actual=actual,storage_verified=stored,
                       result="PASS" if passed else "FAIL",detail=detail)
            results.append(row)
            print(name,step+1,row["result"],"HTTP",status,"state",actual.get("state"),flush=True)
    out = Path(args.output)/run_id
    out.mkdir(parents=True,exist_ok=True)
    (out/"results.json").write_text(json.dumps(dict(run_id=run_id,
        generated_at=datetime.now(timezone.utc).isoformat(),results=results),indent=2))
    with (out/"results.csv").open("w",newline="") as handle:
        writer = csv.DictWriter(handle,fieldnames=list(results[0]))
        writer.writeheader()
        for row in results:
            writer.writerow({k:json.dumps(v) if isinstance(v,dict) else v for k,v in row.items()})
    print("Evidence written to",out)
    raise SystemExit(0 if all(r["result"]=="PASS" for r in results) else 1)


if __name__ == "__main__":
    main()

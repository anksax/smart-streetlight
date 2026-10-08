import hmac
import logging
import math
import os
from datetime import datetime, timedelta, timezone
from heapq import nlargest
from flask import Flask, jsonify, render_template, request
from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient, UpdateMode
from azure.identity import ManagedIdentityCredential

app = Flask(__name__)
DEFAULTS = dict(hour=22.0, lux=40.0, activity_lamp=0, follow=True, auto_demo=False)
FIELDS = ['received_at','ambient_lux','simulation_hour','motion','state','brightness','reason','activity_position','demo_mode','motion_held','hold_remaining_seconds']

def storage():
    return TableServiceClient(endpoint=os.environ['TABLE_STORAGE_ENDPOINT'], credential=ManagedIdentityCredential())

def settings(service):
    try:
        row = service.get_table_client('Settings').get_entity('simulation','global')
        return {key: row.get(key,value) for key,value in DEFAULTS.items()}
    except ResourceNotFoundError:
        return DEFAULTS.copy()

@app.after_request
def headers(response):
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    return response

@app.get('/')
def index():
    return render_template('index.html')

@app.get('/api/settings')
def get_settings():
    try:
        with storage() as service:
            return jsonify(settings(service))
    except Exception:
        logging.exception('Settings read failed')
        return jsonify(error='Unable to read simulation settings'),503

@app.post('/api/settings')
def update_settings():
    expected = os.environ.get('DASHBOARD_CONTROL_TOKEN','')
    supplied = request.headers.get('X-Control-Token','')
    if not expected or not hmac.compare_digest(expected.encode(),supplied.encode()):
        return jsonify(error='Enter the correct control password to apply settings'),401
    try:
        data = request.get_json(silent=True)
        if not isinstance(data,dict):
            raise ValueError('Expected a JSON object')
        for key, maximum in [('hour',23.99),('lux',1000)]:
            value = data[key]
            if type(value) not in (int,float) or not math.isfinite(value) or not 0 <= value <= maximum:
                raise ValueError(f'Invalid {key}')
        if type(data['activity_lamp']) is not int or not 0 <= data['activity_lamp'] <= 5:
            raise ValueError('Activity position must be 0 to 5')
        if type(data['follow']) is not bool:
            raise ValueError('Follow must be true or false')
        if type(data.get('auto_demo', False)) is not bool:
            raise ValueError('Automatic demo must be true or false')
        updated = dict(auto_demo=data.get('auto_demo',False),hour=float(data['hour']),lux=float(data['lux']),activity_lamp=data['activity_lamp'],follow=data['follow'])
        with storage() as service:
            service.get_table_client('Settings').upsert_entity(dict(PartitionKey='simulation',RowKey='global',**updated),mode=UpdateMode.REPLACE)
        return jsonify(updated)
    except (ValueError,KeyError,TypeError) as exc:
        return jsonify(error=str(exc)),400
    except Exception:
        logging.exception('Settings write failed')
        return jsonify(error='Unable to save settings'),503

@app.get('/api/state')
def state():
    try:
        now = datetime.now(timezone.utc)
        lamps=[]
        with storage() as service:
            table=service.get_table_client('LampState')
            for number in range(1,6):
                lamp_id=f'L{number:02}'
                lamp=dict(lamp_id=lamp_id,state='WAITING',brightness=0,online=False,age_seconds=None,reason='No telemetry received')
                try:
                    row=table.get_entity(lamp_id,'latest')
                    lamp.update({key:row.get(key) for key in FIELDS})
                    age=max(0,(now-datetime.fromisoformat(row['received_at'])).total_seconds())
                    lamp.update(online=age<=45,age_seconds=round(age))
                except ResourceNotFoundError:
                    pass
                lamps.append(lamp)
            config=settings(service)
        return jsonify(lamps=lamps,settings=config,server_time=now.isoformat())
    except Exception:
        logging.exception('State read failed')
        return jsonify(error='Unable to load lamp telemetry'),503

@app.get('/api/history')
def history():
    lamp=request.args.get('lamp','L01')
    if lamp not in [f'L{i:02}' for i in range(1,6)]:
        return jsonify(error='Unknown lamp'),400
    try:
        cutoff=(datetime.now(timezone.utc)-timedelta(minutes=15)).strftime('%Y%m%dT%H%M%S%f')
        with storage() as service:
            rows=service.get_table_client('Readings').query_entities(
                query_filter='PartitionKey eq @lamp and RowKey ge @cutoff',
                parameters=dict(lamp=lamp,cutoff=cutoff),select=FIELDS)
            recent=nlargest(120,rows,key=lambda row:row['received_at'])
            records=[{key:row.get(key) for key in FIELDS} for row in reversed(recent)]
        return jsonify(lamp_id=lamp,records=records)
    except Exception:
        logging.exception('History read failed')
        return jsonify(error='Unable to load recent history'),503

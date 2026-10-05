import json
import os
import random
import time
from datetime import datetime, timezone
import requests
url=os.environ['STREETLIGHT_URL']
key=os.environ['STREETLIGHT_KEY']
settings_url=os.environ['DASHBOARD_URL'].rstrip('/')+'/api/settings'
try:
 with requests.Session() as session:
  while True:
   try:
    reply=session.get(settings_url,timeout=30)
    reply.raise_for_status()
    config=reply.json()
   except (requests.RequestException,ValueError):
    print('Settings unavailable; retrying in 5 seconds.',flush=True)
    time.sleep(5)
    continue
   position=int(config['activity_lamp'])
   for number in range(1,6):
    active=position!=0 and (number==position or (config['follow'] and position<number<=position+2))
    reading=dict(timestamp=datetime.now(timezone.utc).isoformat(),lamp_id=f'L{number:02}',simulation_hour=float(config['hour']),ambient_lux=round(max(0,float(config['lux'])+random.uniform(-2,2)),1),motion=active)
    print('SENSOR:',json.dumps(reading),flush=True)
    try:
     response=session.post(url,json=reading,headers={'x-functions-key':key},timeout=30)
     print('CLOUD:',response.status_code,response.text,flush=True)
    except requests.RequestException as exc:
     print('Send failed:',type(exc).__name__,flush=True)
   time.sleep(5)
except KeyboardInterrupt:
 print('Simulator stopped.')

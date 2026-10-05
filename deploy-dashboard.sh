#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root=Path('dashboard')
with ZipFile('dashboard.zip','w',ZIP_DEFLATED) as archive:
 for path in root.rglob('*'):
  if path.is_file() and path.relative_to(root).as_posix() in {
   'app.py', 'requirements.txt', 'templates/index.html',
   'static/app.js', 'static/style.css'
  }:
   archive.write(path,path.relative_to(root))
PY
az webapp config appsettings set -g smart-streetlight-rg -n streetlight-dashboard --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true TABLE_STORAGE_ENDPOINT=https://streetlightstorage.table.core.windows.net --output none
az webapp config set -g smart-streetlight-rg -n streetlight-dashboard --startup-file 'gunicorn --bind=0.0.0.0:8000 --timeout 120 app:app' --output none
az webapp deploy -g smart-streetlight-rg -n streetlight-dashboard --src-path dashboard.zip --type zip

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 - <<'PY'
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
with ZipFile('function.zip','w',ZIP_DEFLATED) as archive:
    for name in ['function_app.py','lighting.py','validation.py','requirements.txt','host.json']:
        archive.write(Path('functions')/name,name)
PY
az functionapp deployment source config-zip \
  --resource-group smart-streetlight-rg --name streetlight-func \
  --src function.zip --build-remote true

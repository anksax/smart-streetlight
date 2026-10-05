# Smart Street Lighting

Azure IoT simulation and an operations dashboard for five streetlights, produced by **anksax** (Ankur Ashish Saxena) for Fundamentals of IoT and Cloud Computing.

## Features

- Five selectable lamps, live connectivity, ON/DIM/OFF states and commanded brightness.
- Light and dark dashboard themes, with a browser-local theme preference.
- Daylight street background for simulated hours 06:00–17:59, independent of dashboard theme.
- Selected-lamp lux, motion, decision reason and last received telemetry.
- Cloud-stored brightness history: up to 120 readings per lamp from the last 15 minutes.
- Password-protected daylight, empty-night and movement presets.
- Missing telemetry and failed-request indicators, responsive layout and keyboard controls.
- Visible “Produced by anksax” attribution and managed identity access to storage.

## Azure architecture

```mermaid
flowchart LR
    VM[Python simulator on Azure VM / IaaS] -->|HTTP sensor readings| FN[Azure Function / FaaS]
    FN --> TABLE[Azure Table Storage]
    TABLE --> APP[Flask dashboard on Azure App Service / PaaS]
    APP -->|Write simulation settings| TABLE
    VM -->|Poll dashboard settings API| APP
```

The VM polls `/api/settings`, simulates five sensors and posts readings to the existing Function with the `x-functions-key` header. The Function processes telemetry and stores it; the dashboard reads storage using its App Service managed identity. Dashboard controls write to the Settings table after validating the control password.

**The deployed Azure Function’s source is not included in the ZIP or this repository.** A compatible deployed Function is required; this repository cannot reproduce or redeploy its processing logic.

Existing resource names used by the deployment script:

| Resource | Name |
| --- | --- |
| Resource group | `smart-streetlight-rg` |
| Storage account | `streetlightstorage` |
| Function App | `streetlight-func` |
| Dashboard Web App | `streetlight-dashboard` |

Tables: `Readings`, `LampState`, `Settings`, `Alerts`. Alerts is reserved for future fault detection. The dashboard identity needs Storage Table Data Reader at storage-account scope and Storage Table Data Contributor at Settings-table scope. The Function identity needs Storage Table Data Contributor. These resources and permissions must already exist; the script does not provision them.

### Expected data contract

`Settings` uses PartitionKey `simulation` and RowKey `global`, with `hour`, `lux`, `activity_lamp` (0–5) and `follow` (boolean). `LampState` uses lamp IDs `L01`–`L05` as PartitionKey and `latest` as RowKey. `Readings` uses the lamp ID as PartitionKey and a sortable UTC timestamp RowKey in `YYYYMMDDTHHMMSSffffff` format. Telemetry fields are `received_at` (timezone-aware ISO timestamp), `ambient_lux`, `simulation_hour`, `motion`, `state`, `brightness` (0–100) and `reason`.

## Setup

Requires Python 3.10+ and access to the existing Azure deployment.

```bash
git clone https://github.com/anksax/smart-streetlight.git
cd smart-streetlight
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r dashboard/requirements.txt -r simulator/requirements.txt
```

Copy `.env.example` to an ignored local `.env` and replace its placeholders. These programs read process environment variables; they do **not** automatically load `.env`. Export the required values in your terminal or configure them through your hosting environment without committing them.

| Variable | Used by | Purpose |
| --- | --- | --- |
| `TABLE_STORAGE_ENDPOINT` | Dashboard | Table Storage HTTPS endpoint |
| `DASHBOARD_CONTROL_TOKEN` | Dashboard | Private password required for settings changes |
| `STREETLIGHT_URL` | Simulator | Existing Function HTTP endpoint, without a key in the URL |
| `STREETLIGHT_KEY` | Simulator | Function key sent as a request header |
| `DASHBOARD_URL` | Simulator | Dashboard base URL |

### Dashboard

```bash
python -m flask --app dashboard/app run
```

Open `http://127.0.0.1:5000`. The page can render locally, but storage API requests require an Azure managed identity. The included dashboard deliberately uses `ManagedIdentityCredential`; to develop against Azure from a workstation, adapt the credential to a suitable local Azure credential and authenticate with the required table permissions. Never insert credentials into source files. The control password remains in page memory and is not saved in browser storage.

### Simulator

Set `STREETLIGHT_URL`, `STREETLIGHT_KEY` and `DASHBOARD_URL` in the simulator environment, then run:

```bash
python simulator/simulator.py
```

It sends five readings per cycle and waits five seconds between cycles. Stop with Ctrl+C. Follow mode activates the chosen lamp and up to two subsequent lamps; automatic movement and delayed dimming are not implemented. Avoid running duplicate simulators against the same lamp IDs.

## Dashboard deployment

GitHub publication does not update Azure. To deliberately deploy a release later, use Azure Cloud Shell (Bash) or a Bash environment with Python 3 and Azure CLI, sign in to the intended subscription, and run from this repository:

```bash
az login
az account show
bash deploy-dashboard.sh
```

The script packages only the five dashboard runtime files into ignored `dashboard.zip`, enables remote dependency installation, sets `TABLE_STORAGE_ENDPOINT`, configures Gunicorn and ZIP-deploys the existing Web App. It changes that Web App's settings and deployment only. Existing managed identities, roles, `DASHBOARD_CONTROL_TOKEN` and deployment basic authentication settings are left in place. Set the control token privately in App Service configuration if it is missing. No Azure deployment is performed by publishing this repository.

After an intentional deployment, verify the page, `/api/state`, lamp history, theme toggle and password-protected presets. Confirm the VM produces fresh readings and that incorrect passwords cannot change settings.

## Data interpretation

ONLINE means telemetry arrived within 45 seconds. Offline brightness is the last-known command. Mean brightness includes stale reported commands and is not an energy measurement. Environment settings can update before the VM's next sensor cycle. The daylight background follows simulated time, while actual brightness comes from the deployed Function.

## Security and checks

Keep passwords, Function keys, private keys, `.env` files, caches and generated ZIPs out of Git. `.env.example` contains placeholders only. `.gitignore` excludes common sensitive and generated files; the deployment archive uses an explicit runtime-file allowlist. Review staged files before publishing.

Syntax checks:

```bash
python -m compileall -q dashboard simulator
node --check dashboard/static/app.js
bash -n deploy-dashboard.sh
```

Cloud connectivity and the external Function must be verified in Azure separately. No Function source or standalone UI smoke-test workflow was supplied in the ZIP.

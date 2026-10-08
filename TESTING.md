# Assignment testing and evidence

## Reproducible local checks

Run from the repository root:

```bash
python3 -m unittest discover -s functions -p 'test_*.py'
node --check dashboard/static/app.js
bash -n deploy-function.sh
bash -n deploy-dashboard.sh
```

The Python tests require only the standard library. They cover numeric limits,
invalid types, missing fields, motion hold expiry/refresh, daylight cancellation,
first-reading decisions and both directions of hysteresis.

## Live acceptance tests

Deploy the updated Function and dashboard first. Run the following on the VM
with the same three environment variables used by the simulator:
STREETLIGHT_URL, STREETLIGHT_KEY and DASHBOARD_URL.

```bash
python3 tests/live_acceptance.py
```

The runner makes real requests; it does not invent actual results. It publishes
isolated QA lamp IDs and verifies each accepted record through the dashboard's
Table Storage history reader using its sensor timestamp. It exercises all
three states, dark daytime, 299/300/301 lux, 279/280 hysteresis boundaries,
motion hold and invalid lux/hour/motion. At least ten accepted cloud records
are generated. Invalid requests must return 400 and have no matching record.
CSV and JSON evidence is written under test-results/<run-id>.

QA records do not appear among the five street lamps. This prevents tests from
overwriting the running demonstration. Use their lamp IDs to find them in
Storage browser. Record retention/cleanup is manual after assessment.

API evidence verifies Function -> Storage -> dashboard data access. It does
not replace a screenshot demonstrating the five-lamp UI. No live test has
passed merely because a local unit test passed.

## Visual and integration evidence

| Required test | Setup | Expected observation |
|---|---|---|
| Normal | Manual mode; 600 lux, hour 12, no activity | OFF / 0%; HTTP 200; stored record |
| Low light | Manual mode; 40 lux, hour 22, no activity; wait for hold to expire | DIM / 30% |
| Activity abnormal/alert | 40 lux, hour 22, activity L03 | ON / 100% at L03 and follow lamps |
| Boundary | Live runner; preserve previous state | Exact 279/280 and 299/300/301 decisions |
| Invalid sensor | Live runner: negative lux, invalid hour, string motion | HTTP 400; no matching stored reading |
| Hold | Remove activity at night | ON for up to 12s, then DIM |
| Automatic | Enable automatic demo and apply | Day/night in 120s; activity advances every 6s |
| Offline | Stop service and wait over 45s | Lamps marked stale/offline; restart afterward |
| Wrong password | Apply controls with incorrect password | Rejected; saved settings unchanged |

With hysteresis, 299 lux following an OFF state remains OFF. A first reading at
299 lux is DIM. Always document the preceding state in boundary evidence.
Lux >=300 cancels hold immediately. Simulator noise is inappropriate for
exact boundary evidence; use the live runner.

## Requirements traceability

| Assignment requirement | Implementation / evidence |
|---|---|
| 2–4 sensor parameters | Lux (lx), simulated hour (0–24), motion (boolean) |
| VM sensor simulator | simulator/simulator.py; SSH and running-service screenshots |
| HTTP-triggered Function | functions/function_app.py; HTTP request/response evidence |
| 3 processing conditions | OFF, DIM, ON; functions/lighting.py |
| 5–10 stored records | Readings table; live runner generates more than ten |
| Dashboard | Flask App Service; five lamps and selected-lamp history |
| 3 E2E cases including abnormal | Normal, boundary, activity/invalid cases plus visual evidence |
| IaaS/FaaS/PaaS diagram | README architecture; label Azure VM, Function, App Service |
| Public cloud discussion | PDF/PPT: two benefits and two limitations |
| Group submission | PDF and PPT with group number, names and roll numbers |

## Screenshot checklist

- Subscription and resource group.
- VM overview; successful SSH; OS and Python version.
- Simulator readings and successful cloud responses.
- Function overview, code, and tests.
- Readings table with raw data, timestamps and processed state.
- Deployed dashboard; normal, boundary and abnormal demonstration.
- Exported actual test results.
- Cleanup after assessment.

Do not include Function keys, passwords or SSH keys in screenshots.
PDF/PPT, team details, conceptual analysis and cleanup remain submission tasks.

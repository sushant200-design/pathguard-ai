# PathGuard AI

A student mini-project starter for road-hazard reporting, map visualization, risk prioritization, and administration.

## Features
- Citizen registration/login with password hashing
- Report creation with image upload and map-selected coordinates
- SQLite persistence
- Public report listing, search/filter, report details
- Leaflet / OpenStreetMap hazard map
- Nearby reports within a selectable radius (default 10 km after selecting your location)
- Unique support/vote per user per report
- Admin dashboard, status updates, notes, admin account creation
- Optional YOLO inference when compatible trained weights are configured
- Rule-based demo risk score (not a validated safety model)

## Requirements
- Python 3.10+ recommended
- Internet access for CDN assets and OpenStreetMap tiles during the demo

## Setup (Windows PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:PATHGUARD_SECRET="replace-this-with-a-long-random-secret"
$env:PATHGUARD_ADMIN_EMAIL="admin@example.com"
$env:PATHGUARD_ADMIN_PASSWORD="Choose-A-Strong-Password"
python app.py
```

If PowerShell blocks activation, run `.venv\Scripts\python.exe -m pip install -r requirements.txt`, then `.venv\Scripts\python.exe app.py`.

## Setup (macOS/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
export PATHGUARD_SECRET='replace-this-with-a-long-random-secret'
export PATHGUARD_ADMIN_EMAIL='admin@example.com'
export PATHGUARD_ADMIN_PASSWORD='Choose-A-Strong-Password'
python app.py
```

Open http://127.0.0.1:5000.

## Admin login
On first run, an admin account is created from `PATHGUARD_ADMIN_EMAIL` and `PATHGUARD_ADMIN_PASSWORD`. If you do not set these variables, the local demo defaults are:
- Email: `admin@pathguard.local`
- Password: `AdminDemo123!`

Change these before any shared demo. If the database already exists, changing the environment password does not reset the existing account password. For a local project demo, create a new admin from the admin panel or reset the password intentionally using a script.

## Optional YOLO setup
The project does **not** include trained weights. To configure your own compatible Ultralytics YOLO model:

Windows PowerShell:
```powershell
$env:PATHGUARD_YOLO_MODEL="C:\path\to\your\trained-model.pt"
python app.py
```

macOS/Linux:
```bash
export PATHGUARD_YOLO_MODEL='/path/to/your/trained-model.pt'
python app.py
```

Install may take time because Ultralytics brings ML dependencies. If you only want to run the reporting/map prototype first, you can temporarily remove `ultralytics>=8.2` from `requirements.txt` and install only Flask; AI page will report unavailable unless weights are configured and the package is installed. A model file existing does not prove it detects potholes: verify `model.names`, run labeled test images, and document the measured metrics.

## Database and uploads
- SQLite database: `pathguard.db` (created on first run)
- Uploaded images: `static/uploads/`
- Back up both before moving the project.
- Do not commit the database, uploaded photos, secrets, or real user data to Git.

## Project structure
```text
pathguard_ai/
├── app.py
├── database.py
├── requirements.txt
├── README.md
├── pathguard.db              # generated at first run
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── login.html
│   ├── report.html
│   ├── reports.html
│   ├── report_detail.html
│   ├── dashboard.html
│   ├── map.html
│   ├── admin.html
│   ├── admin_users.html
│   ├── ai_detection.html
│   └── error.html
└── static/
    ├── css/style.css
    ├── js/main.js
    ├── js/report-map.js
    ├── js/reports.js
    ├── js/hazard-map.js
    ├── js/detail-map.js
    ├── js/admin.js
    └── uploads/
```

## Important limitations before public deployment
This is a local educational prototype, not production-hardened software. Before internet deployment, add CSRF protection, rate limiting, email verification/password reset, secure cookie and HTTPS configuration, moderation/report verification, stronger file validation and image re-encoding, backups, logging, and tests. The starter uses one global admin role; per-admin geographic jurisdictions are not implemented yet. The map is location-aware only when a user explicitly shares their browser location; otherwise reports are shown globally. Nearby distance filtering is calculated from the selected browser location in the map UI.

The risk score is a transparent illustrative heuristic based on category and a few description keywords; it is not an AI prediction or validated measure of real-world danger.


## Authority portal (added)

This update adds an additive SQLite migration and role-based authority portal without deleting existing citizen reports. Existing `admin` accounts that do not have an `authority_profiles` row are treated as Super Admins. The seeded local demo Super Admin is `admin@pathguard.local` / `AdminDemo123!` unless `PATHGUARD_ADMIN_EMAIL` and `PATHGUARD_ADMIN_PASSWORD` are set before the first run. Change the demo password before sharing the app.

### Setup and run on Windows
1. Back up `pathguard.db` and `static/uploads/` if they already contain data.
2. Activate your environment: `venv\Scripts\activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Start: `python app.py`
5. Sign in as Super Admin at `http://127.0.0.1:5000/login`.
6. Open `http://127.0.0.1:5000/admin/authorities` and create each road authority with a center latitude/longitude and radius.
7. Authority users sign in through the same login page and are sent to `/authority`.

### Geographic authorization
The authority dashboard, report detail and status-update endpoints verify report coordinates against the assigned center/radius on the server. Unauthorized report IDs return 403, and missing report IDs return 404. The radius uses straight-line Haversine distance, not road travel distance. Public citizen-facing `/reports`, `/report/<id>`, and `/api/reports` routes remain public in the original project; this portal's authority views are restricted. If those public routes should also be private, change them separately.

### Important security notes
This is an educational prototype. Before public deployment, configure a strong random `PATHGUARD_SECRET`, HTTPS and secure cookies, CSRF protection, rate limiting, secure upload validation/re-encoding, backups, and tests. The local seeded credentials are public demo credentials. Existing role values are preserved (`citizen`/`admin`); an `authority_profiles` row distinguishes road authorities from Super Admins, avoiding a destructive rebuild of the existing `users` table.
gunicorn

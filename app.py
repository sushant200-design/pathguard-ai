import os
from functools import wraps
from math import radians, sin, cos, asin, sqrt
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import init_db, get_db, seed_admin

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("PATHGUARD_SECRET", "change-this-development-secret")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
STATUSES = ["Submitted", "Under Review", "In Progress", "Resolved", "Rejected"]
CATEGORIES = ["Pothole", "Damaged Road", "Waterlogging", "Broken Manhole", "Road Debris", "Other"]

init_db()
seed_admin()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def current_user():
    if "user_id" not in session:
        return None
    db = get_db()
    user = db.execute("SELECT id, name, email, role FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    db.close()
    return user

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        if user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped

def authority_profile(user_id):
    db = get_db()
    profile = db.execute("SELECT * FROM authority_profiles WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    return profile

def super_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        if user["role"] != "admin" or authority_profile(user["id"]):
            abort(403)
        return view(*args, **kwargs)
    return wrapped

def authority_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        profile = authority_profile(user["id"]) if user["role"] == "admin" else None
        if not profile or not profile["is_active"]:
            abort(403)
        return view(*args, **kwargs)
    return wrapped

def reports_in_authority_area(db, profile):
    rows = db.execute("""SELECT r.*, u.name AS reporter,
        (SELECT COUNT(*) FROM report_support s WHERE s.report_id=r.id) AS support_count
        FROM reports r LEFT JOIN users u ON u.id=r.user_id
        ORDER BY r.risk_score DESC, r.created_at DESC""").fetchall()
    return [r for r in rows if haversine_km(profile["center_lat"], profile["center_lon"],
                                             r["latitude"], r["longitude"]) <= profile["radius_km"]]

def authority_can_access_report(db, profile, report_id):
    row = db.execute("SELECT latitude, longitude FROM reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        return None
    distance = haversine_km(profile["center_lat"], profile["center_lon"], row["latitude"], row["longitude"])
    return row if distance <= profile["radius_km"] else False

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*r*asin(sqrt(min(1, a)))

def risk_score(category, description):
    # Transparent demonstration heuristic, not a validated safety model.
    base = {
        "Pothole": 65, "Damaged Road": 70, "Waterlogging": 55,
        "Broken Manhole": 75, "Road Debris": 45, "Other": 35
    }.get(category, 35)
    text = (description or "").lower()
    if any(word in text for word in ["large", "deep", "major", "accident", "dangerous", "busy", "highway"]):
        base += 15
    return min(100, base)

@app.context_processor
def inject_globals():
    user = current_user()
    is_authority = bool(user and user["role"] == "admin" and authority_profile(user["id"]))
    return {"nav_user": user, "categories": CATEGORIES, "statuses": STATUSES,
            "nav_is_authority": is_authority, "nav_is_super_admin": bool(user and user["role"] == "admin" and not is_authority)}

@app.route("/")
def index():
    db = get_db()
    stats = {
        "total": db.execute("SELECT COUNT(*) FROM reports").fetchone()[0],
        "open": db.execute("SELECT COUNT(*) FROM reports WHERE status NOT IN ('Resolved','Rejected')").fetchone()[0],
        "resolved": db.execute("SELECT COUNT(*) FROM reports WHERE status='Resolved'").fetchone()[0],
    }
    recent = db.execute("""SELECT r.*, u.name AS reporter FROM reports r
        LEFT JOIN users u ON u.id=r.user_id ORDER BY r.created_at DESC LIMIT 6""").fetchall()
    db.close()
    return render_template("index.html", stats=stats, recent=recent)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name and email. Password must be at least 8 characters.", "danger")
            return render_template("register.html")
        db = get_db()
        try:
            db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'citizen')",
                       (name, email, generate_password_hash(password)))
            db.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except Exception:
            flash("That email may already be registered.", "danger")
        finally:
            db.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        profile = None
        if user and user["role"] == "admin":
            profile = db.execute("SELECT is_active FROM authority_profiles WHERE user_id=?", (user["id"],)).fetchone()
        db.close()
        if user and check_password_hash(user["password_hash"], password):
            if profile and not profile["is_active"]:
                flash("This authority account is inactive. Contact the Super Admin.", "danger")
                return render_template("login.html")
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['name']}!", "success")
            if user["role"] == "admin":
                return redirect(url_for("authority_dashboard") if profile else url_for("admin_dashboard"))
            dest = request.args.get("next", "")
            return redirect(dest if dest.startswith("/") and not dest.startswith("//") else url_for("dashboard"))
        db.close()
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    db = get_db()
    reports = db.execute("SELECT * FROM reports WHERE user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall()
    db.close()
    return render_template("dashboard.html", reports=reports)

@app.route("/report", methods=["GET", "POST"])
@login_required
def report_hazard():
    if request.method == "POST":
        category = request.form.get("category", "")
        description = request.form.get("description", "").strip()
        location_name = request.form.get("location_name", "").strip()
        try:
            lat, lon = float(request.form.get("latitude", "")), float(request.form.get("longitude", ""))
        except ValueError:
            flash("Choose a valid map location before submitting.", "danger")
            return render_template("report.html")
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            flash("The selected coordinates are invalid.", "danger")
            return render_template("report.html")
        if category not in CATEGORIES or not description:
            flash("Choose a category and add a description.", "danger")
            return render_template("report.html")
        image_name = None
        image = request.files.get("image")
        if image and image.filename:
            if not allowed_file(image.filename):
                flash("Upload a JPG, PNG, or WEBP image.", "danger")
                return render_template("report.html")
            safe = secure_filename(image.filename)
            image_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{safe}"
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], image_name))
        score = risk_score(category, description)
        db = get_db()
        cur = db.execute("""INSERT INTO reports
            (user_id, category, description, location_name, latitude, longitude, image_filename, risk_score, status)
            VALUES (?,?,?,?,?,?,?,?, 'Submitted')""",
            (current_user()["id"], category, description, location_name, lat, lon, image_name, score))
        db.commit()
        report_id = cur.lastrowid
        db.close()
        flash(f"Report PG-{report_id:04d} submitted successfully.", "success")
        return redirect(url_for("report_detail", report_id=report_id))
    return render_template("report.html")

@app.route("/reports")
def reports():
    db = get_db()
    rows = db.execute("""SELECT r.*, u.name AS reporter FROM reports r
        LEFT JOIN users u ON u.id=r.user_id ORDER BY r.created_at DESC""").fetchall()
    db.close()
    return render_template("reports.html", reports=rows)

@app.route("/report/<int:report_id>")
def report_detail(report_id):
    db = get_db()
    row = db.execute("""SELECT r.*, u.name AS reporter FROM reports r
        LEFT JOIN users u ON u.id=r.user_id WHERE r.id=?""", (report_id,)).fetchone()
    db.close()
    if not row:
        abort(404)
    return render_template("report_detail.html", report=row)

@app.route("/map")
def hazard_map():
    return render_template("map.html")

@app.route("/api/reports")
def api_reports():
    db = get_db()
    rows = db.execute("""SELECT id, category, description, location_name, latitude, longitude,
        risk_score, status, created_at FROM reports ORDER BY created_at DESC""").fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/nearby")
def api_nearby():
    try:
        lat, lon = float(request.args["lat"]), float(request.args["lon"])
        radius = min(50.0, max(0.1, float(request.args.get("radius", "10"))))
    except (KeyError, ValueError):
        return jsonify({"error": "Valid lat and lon are required."}), 400
    db = get_db()
    rows = db.execute("""SELECT id, category, description, location_name, latitude, longitude,
        risk_score, status, created_at FROM reports""").fetchall()
    db.close()
    output = []
    for row in rows:
        distance = haversine_km(lat, lon, row["latitude"], row["longitude"])
        if distance <= radius:
            item = dict(row)
            item["distance_km"] = round(distance, 2)
            output.append(item)
    output.sort(key=lambda x: (x["risk_score"] * -1, x["distance_km"]))
    return jsonify(output)

@app.route("/support/<int:report_id>", methods=["POST"])
@login_required
def support_report(report_id):
    db = get_db()
    exists = db.execute("SELECT id FROM reports WHERE id=?", (report_id,)).fetchone()
    if not exists:
        db.close()
        abort(404)
    try:
        db.execute("INSERT INTO report_support(report_id,user_id) VALUES(?,?)", (report_id, current_user()["id"]))
        db.commit()
        flash("You supported this report. Thank you!", "success")
    except Exception:
        flash("You have already supported this report.", "info")
    finally:
        db.close()
    return redirect(request.referrer if request.referrer and request.referrer.startswith("/") else url_for("reports"))

@app.route("/admin")
@super_admin_required
def admin_dashboard():
    db = get_db()
    rows = db.execute("""SELECT r.*, u.name AS reporter,
        (SELECT COUNT(*) FROM report_support s WHERE s.report_id=r.id) AS support_count
        FROM reports r LEFT JOIN users u ON u.id=r.user_id
        ORDER BY r.risk_score DESC, r.created_at DESC""").fetchall()
    counts = {s: db.execute("SELECT COUNT(*) FROM reports WHERE status=?", (s,)).fetchone()[0] for s in STATUSES}
    db.close()
    return render_template("admin.html", reports=rows, counts=counts)

@app.route("/admin/report/<int:report_id>", methods=["POST"])
@super_admin_required
def admin_update_report(report_id):
    status = request.form.get("status", "")
    note = request.form.get("resolution_note", "").strip()
    if status not in STATUSES:
        abort(400)
    db = get_db()
    row = db.execute("SELECT id FROM reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        db.close()
        abort(404)
    db.execute("UPDATE reports SET status=?, resolution_note=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
               (status, note, report_id))
    db.execute("INSERT INTO report_activity(report_id, actor_user_id, status, note) VALUES(?,?,?,?)",
               (report_id, current_user()["id"], status, note))
    db.commit()
    db.close()
    flash("Report status updated.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/users", methods=["GET", "POST"])
@super_admin_required
def admin_users():
    # Backward-compatible URL; account creation is now handled in the authority manager.
    return redirect(url_for("admin_authorities"))

@app.route("/admin/authorities", methods=["GET", "POST"])
@super_admin_required
def admin_authorities():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action", "create")
        if action == "toggle":
            try:
                target_id = int(request.form.get("user_id", ""))
            except ValueError:
                abort(400)
            target = db.execute("SELECT u.id, u.name, ap.is_active FROM users u JOIN authority_profiles ap ON ap.user_id=u.id WHERE u.id=?", (target_id,)).fetchone()
            if not target:
                db.close(); abort(404)
            new_active = 0 if target["is_active"] else 1
            db.execute("UPDATE authority_profiles SET is_active=? WHERE user_id=?", (new_active, target_id))
            db.execute("INSERT INTO authority_audit(actor_user_id,target_user_id,action,details) VALUES(?,?,?,?)",
                       (current_user()["id"], target_id, "deactivate" if not new_active else "reactivate", "Authority account status changed"))
            db.commit()
            flash("Authority account updated.", "success")
        else:
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            try:
                lat = float(request.form.get("center_lat", "")); lon = float(request.form.get("center_lon", ""))
                radius = float(request.form.get("radius_km", "10"))
            except ValueError:
                lat, lon, radius = 999, 999, 0
            if not name or not email or len(password) < 12 or not (-90 <= lat <= 90) or not (-180 <= lon <= 180) or not (0 < radius <= 500):
                flash("Enter valid details, coordinates, a radius up to 500 km, and a password of at least 12 characters.", "danger")
            else:
                try:
                    cur = db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'admin')",
                                     (name, email, generate_password_hash(password)))
                    target_id = cur.lastrowid
                    db.execute("INSERT INTO authority_profiles(user_id,center_lat,center_lon,radius_km) VALUES(?,?,?,?)",
                               (target_id, lat, lon, radius))
                    db.execute("INSERT INTO authority_audit(actor_user_id,target_user_id,action,details) VALUES(?,?,?,?)",
                               (current_user()["id"], target_id, "create", f"Center=({lat},{lon}); radius={radius} km"))
                    db.commit()
                    flash("Road authority account created.", "success")
                except Exception:
                    db.rollback()
                    flash("That email may already be registered. No account was created.", "danger")
    authorities = db.execute("""SELECT u.id,u.name,u.email,u.created_at,ap.center_lat,ap.center_lon,ap.radius_km,ap.is_active
        FROM users u JOIN authority_profiles ap ON ap.user_id=u.id ORDER BY u.created_at DESC""").fetchall()
    audit = db.execute("""SELECT a.created_at,a.action,a.details,u.name AS actor,t.name AS target
        FROM authority_audit a JOIN users u ON u.id=a.actor_user_id LEFT JOIN users t ON t.id=a.target_user_id
        ORDER BY a.id DESC LIMIT 20""").fetchall()
    db.close()
    return render_template("admin_authorities.html", authorities=authorities, audit=audit)

@app.route("/authority")
@authority_required
def authority_dashboard():
    user = current_user()
    profile = authority_profile(user["id"])
    db = get_db()
    reports = reports_in_authority_area(db, profile)
    counts = {status: sum(1 for r in reports if r["status"] == status) for status in STATUSES}
    db.close()
    return render_template("authority.html", reports=reports, counts=counts, profile=profile)

@app.route("/authority/report/<int:report_id>", methods=["POST"])
@authority_required
def authority_update_report(report_id):
    user = current_user(); profile = authority_profile(user["id"])
    status = request.form.get("status", "")
    note = request.form.get("resolution_note", "").strip()
    if status not in STATUSES or len(note) > 1000:
        abort(400)
    db = get_db()
    access = authority_can_access_report(db, profile, report_id)
    if access is None:
        db.close(); abort(404)
    if access is False:
        db.close(); abort(403)
    db.execute("UPDATE reports SET status=?, resolution_note=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
               (status, note, report_id))
    db.execute("INSERT INTO report_activity(report_id,actor_user_id,status,note) VALUES(?,?,?,?)",
               (report_id, user["id"], status, note))
    db.commit(); db.close()
    flash(f"Report PG-{report_id:04d} updated.", "success")
    return redirect(url_for("authority_dashboard"))

@app.route("/authority/report/<int:report_id>")
@authority_required
def authority_report_detail(report_id):
    user = current_user(); profile = authority_profile(user["id"])
    db = get_db()
    access = authority_can_access_report(db, profile, report_id)
    if access is None:
        db.close(); abort(404)
    if access is False:
        db.close(); abort(403)
    row = db.execute("""SELECT r.*,u.name AS reporter FROM reports r LEFT JOIN users u ON u.id=r.user_id WHERE r.id=?""", (report_id,)).fetchone()
    db.close()
    distance = round(haversine_km(profile["center_lat"], profile["center_lon"], row["latitude"], row["longitude"]), 2)
    return render_template("authority_report.html", report=row, distance=distance)

@app.route("/ai-detection", methods=["GET", "POST"])
@login_required
def ai_detection():
    model_path = os.environ.get("PATHGUARD_YOLO_MODEL", "").strip()
    model_ready = bool(model_path and os.path.isfile(model_path))
    results = None
    error = None
    if request.method == "POST":
        image = request.files.get("image")
        if not image or not image.filename:
            error = "Choose an image first."
        elif not allowed_file(image.filename):
            error = "Upload a JPG, PNG, or WEBP image."
        elif not model_ready:
            error = "AI detection is not configured: compatible trained YOLO weights were not found. Manual hazard reporting is still available."
        else:
            try:
                from ultralytics import YOLO
                import tempfile
                model = YOLO(model_path)
                suffix = "." + image.filename.rsplit(".", 1)[1].lower()
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    image.save(tmp.name)
                    temp_path = tmp.name
                try:
                    predictions = model.predict(source=temp_path, verbose=False)
                    p = predictions[0]
                    results = []
                    for box in p.boxes:
                        cls_id = int(box.cls[0])
                        results.append({
                            "class_name": p.names.get(cls_id, str(cls_id)),
                            "confidence": round(float(box.conf[0]), 4),
                            "xyxy": [round(float(v), 1) for v in box.xyxy[0].tolist()]
                        })
                finally:
                    os.unlink(temp_path)
            except Exception as exc:
                error = f"Model inference failed. Check that the weights match your installed Ultralytics version. Details: {exc}"
    return render_template("ai_detection.html", model_ready=model_ready, results=results, error=error)

@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="You do not have permission to access this page."), 403

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="The page or report could not be found."), 404

if __name__ == "__main__":
    app.run(debug=True)

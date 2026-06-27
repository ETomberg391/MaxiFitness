"""MaxiFitness Workout Tracker — Flask application."""

import sqlite3
import os
import io
from PIL import Image
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.exceptions import RequestEntityTooLarge

from dotenv import load_dotenv
load_dotenv()

from db import get_db, init_db, seed_settings_if_empty, bmi as calc_bmi
from db import get_streak, get_weekly_stats, get_monthly_stats, get_heatmap_data
from db import compute_ema, compute_ema_list, check_milestones
from db import evaluate_badges, get_badge_progress
from db import recommend_workout, get_variety_report
from db import calculate_bmr

app = Flask(__name__)
# ChowAPI key for barcode nutrition lookups (set in .env)
CHOW_API_KEY = os.environ.get("CHOW_API_KEY", "")
# Flask secret key for session cookies (set in .env)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-env-file")

# Prevent browser caching so template/JS updates are picked up immediately
@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Photo upload config
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB
app.config["PHOTO_UPLOAD_DIR"] = os.path.join(app.root_path, "static", "photos")
app.config["PHOTO_THUMB_MAX_EDGE"] = 600
app.config["PHOTO_ORIGINAL_MAX_EDGE"] = 1920
app.config["PHOTO_QUALITY"] = 85
app.config["PHOTO_PER_USER_LIMIT"] = 100
app.config["PHOTO_PER_USER_BYTES"] = 500 * 1024 * 1024  # 500 MB


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    flash("Photo too large. Maximum size is 10 MB.", "error")
    return redirect(request.referrer or url_for("progress"))

# Initialize DB on import
init_db()
seed_settings_if_empty()


# ─── Helpers ────────────────────────────────────────────────────────────────


def get_settings():
    conn = get_db()
    row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else {}


def get_week_range():
    """Return (monday, sunday) for the current week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_current_week_number():
    """ISO week number for today."""
    return date.today().isocalendar()[1]


def get_current_phase():
    week = get_current_week_number()
    if week <= 2:
        return "Foundation (Weeks 1-2)"
    elif week <= 4:
        return "Build (Weeks 3-4)"
    else:
        return "Maintenance (Week 5+)"


def get_weighin_day_name(day_int):
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day_int]


def next_weighin_date(user_weighin_day):
    today = date.today()
    days_ahead = user_weighin_day - today.weekday()
    if days_ahead < 0:
        days_ahead += 7
    if days_ahead == 0:
        return today
    return today + timedelta(days=days_ahead)


def is_weighin_day(user_weighin_day):
    return date.today().weekday() == user_weighin_day


def weighin_feedback(last_weight, current_weight, total_loss):
    if last_weight is None:
        return "First weigh-in logged! Keep it up."
    change = round(current_weight - last_weight, 1)
    if change < -0.5:
        return f"Great week! Down {abs(change)} lbs."
    elif change <= 0.5:
        return "Steady week. The trend is what matters."
    elif change <= 2.0:
        return f"Up {change} lbs this week — totally normal. Water, salt, timing all play a role. Your {total_loss} lb total loss speaks for itself."
    else:
        return f"Up {change} lbs — fluctuations happen. Look at your overall trend, not one week. You're {total_loss} lbs down overall."

app.jinja_env.globals['get_current_phase'] = get_current_phase
app.jinja_env.globals['heatmap_level'] = lambda mins: '1' if mins < 15 else '2' if mins < 30 else '3'


def generate_workout_summary(duration_min, calories, workout_type, total_workouts, exertion):
    """Return (summary_text, emoji) for a gamified post-workout message."""
    import random
    msgs = []
    # Milestone check
    if total_workouts % 5 == 0:
        msgs.append((f"That's workout #{total_workouts} — you're on a roll! 🔥", '🔥'))
    if total_workouts % 10 == 0:
        msgs.append((f"#{total_workouts} workouts! You're a machine! 💪", '💪'))
    # Duration-based
    if duration_min >= 30:
        msgs.append((f"{duration_min} minutes — that's serious commitment! ⏱️", '⏱️'))
    if duration_min >= 45:
        msgs.append((f"{duration_min} minutes — you could walk across Manhattan in that time! 🏃", '🏃'))
    # Calorie-based
    if calories and calories >= 200:
        hours = round(calories / 60, 1)
        msgs.append((f"You burned {calories} cal — enough to power a 60W bulb for {hours} hours! 💡", '💡'))
    if calories and calories >= 400:
        msgs.append((f"{calories} cal burned! That's like running {round(calories/100, 1)} miles! 🏃‍♀️", '🏃‍♀️'))
    # Exertion-based
    if exertion == 5:
        msgs.append(("Felt amazing! That's the kind of energy that builds habits. ⚡", '⚡'))
    if exertion == 1:
        msgs.append(("Brutal session — but that's where the growth happens. 💪", '💪'))
    # Fallback
    if not msgs:
        msgs.append(("Great session! Consistency is what moves the needle. 🎯", '🎯'))
    return random.choice(msgs)

# ─── Calorie estimation helpers ───────────────────────────────────────────────

# Metabolic Equivalent of Task (MET) values for MaxiFitness-style vertical
# climbing workouts, keyed by the intensity tags used in the videos table
# and the workouts table.
_MAXIFITNESS_METS = {
    "beginner": 5.0,
    "moderate": 7.0,
    "high":     9.0,
}

# Fallback weight (kg) used when no weight has ever been recorded for the user.
_DEFAULT_WEIGHT_KG = 70.0  # ~154 lb


def latest_weight_kg(user_id):
    """Return the user's most recent recorded weight in kilograms.

    Priority:
      1. Most recent row in daily_metrics (today's weigh-in if present)
      2. users.weight_lbs (profile baseline)
      3. _DEFAULT_WEIGHT_KG
    Returns a tuple (kg, source) where source is one of 'daily_metrics',
    'profile', or 'default' — so callers can label the estimate.

    Note: the daily_metrics.weight column stores pounds (the existing
    project convention; users.weight_lbs is explicitly pounds too). If a
    unit column is added to daily_metrics in the future, update here.
    """
    conn = get_db()
    # 1) Most recent daily_metrics weight (lbs, per project convention)
    row = conn.execute(
        "SELECT weight FROM daily_metrics "
        "WHERE user_id = ? AND weight IS NOT NULL "
        "ORDER BY date DESC, id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if row and row["weight"]:
        kg = float(row["weight"]) * 0.453592
        conn.close()
        return round(kg, 1), "daily_metrics"

    # 2) Profile weight_lbs on the users row
    row = conn.execute(
        "SELECT weight_lbs FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row and row["weight_lbs"]:
        kg = float(row["weight_lbs"]) * 0.453592
        conn.close()
        return round(kg, 1), "profile"

    conn.close()
    return _DEFAULT_WEIGHT_KG, "default"


def estimate_calories(weight_kg, intensity, duration_min):
    """Estimate calorie burn using the standard MET formula.

    Returns an integer. Result is clipped to a sensible floor of 1 kcal so
    the column never shows 0 for a real workout.
    """
    met = _MAXIFITNESS_METS.get((intensity or "moderate").lower(), 7.0)
    hours = max(duration_min, 0) / 60.0
    return max(1, round(met * weight_kg * hours))


def bmi_category(bmi_val):
    if bmi_val is None:
        return "N/A"
    elif bmi_val < 18.5:
        return "Underweight"
    elif bmi_val < 25:
        return "Normal"
    elif bmi_val < 30:
        return "Overweight"
    else:
        return "Obese"
# ─── Template context ──────────────────────────────────────────────────────


@app.context_processor
def inject_users():
    """Make all_nav_users, current_user_name, and current_user available in every template."""
    result = {"all_nav_users": [], "current_user_name": None, "current_user": None, "session": session}
    if session.get("user_id"):
        conn = get_db()
        result["all_nav_users"] = conn.execute("SELECT id, name FROM users ORDER BY name").fetchall()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        result["current_user_name"] = row["name"] if row else None
        result["current_user"] = dict(row) if row else None
        conn.close()
    return result



# ─── Auth guard ─────────────────────────────────────────────────────────────

USER_WHITELIST = {"users", "add_user", "select_user", "edit_user", "static", "api_weekly_weighin", "api_weekly_chart", "api_weighin_status", "api_weighin_day"}


@app.before_request
def require_user():
    if request.endpoint in USER_WHITELIST:
        return
    if request.endpoint and request.endpoint.startswith("api_"):
        return
    # Allow app clients that pass user_id as query param
    if request.args.get("user_id"):
        return
    if not session.get("user_id"):
        return redirect(url_for("users"))


# ─── User management ────────────────────────────────────────────────────────


@app.route("/users", methods=["GET", "POST"])
def users():
    conn = get_db()

    if request.method == "POST":
        # Add new user
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name is required.", "error")
            conn.close()
            return redirect(url_for("users"))

        weight_lbs = float(request.form["weight_lbs"]) if request.form.get("weight_lbs") else None
        height_ft = int(request.form["height_ft"]) if request.form.get("height_ft") else None
        height_in = int(request.form["height_in"]) if request.form.get("height_in") else None
        start_date = request.form.get("start_date", date.today().isoformat())
        notes = request.form.get("notes", "")
        weighin_day = int(request.form.get("weighin_day", 0))
        age = int(request.form["age"]) if request.form.get("age") else None
        gender = request.form.get("gender", "female")
        diet_focus = request.form.get("diet_focus", "calorie")
        prolapse_safe = 1 if request.form.get("prolapse_safe") == "on" else 0

        b = calc_bmi(weight_lbs, height_ft or 0, height_in or 0)
        cur = conn.execute(
            "INSERT INTO users (name, weight_lbs, height_ft, height_in, bmi, start_date, notes, weighin_day, age, gender, prolapse_safe, diet_focus) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, weight_lbs, height_ft, height_in, b, start_date, notes, weighin_day, age, gender, prolapse_safe, diet_focus),
        )
        conn.commit()
        new_id = cur.lastrowid
        session["user_id"] = new_id
        conn.close()
        flash(f"Welcome, {name}!", "success")
        return redirect(url_for("dashboard"))

    # GET — show user list and possibly current user profile
    all_users = conn.execute("SELECT * FROM users ORDER BY name").fetchall()

    if session.get("user_id"):
        user = dict(conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone())
        routines = conn.execute("SELECT * FROM routines ORDER BY name").fetchall()
        videos = conn.execute("SELECT * FROM videos ORDER BY name").fetchall()
        conn.close()
        return render_template(
            "users.html",
            all_users=all_users,
            current_user=user,
            routines=routines,
            videos=videos,
            today=date.today().isoformat(),
        )
    else:
        conn.close()
        return render_template("users.html", all_users=all_users, current_user=None, routines=[], videos=[], today=date.today().isoformat())


@app.route("/users/<int:id>/select", methods=["POST"])
def select_user(id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("users"))
    session["user_id"] = id
    flash(f"Switched to {user['name']}.", "success")
    return redirect(url_for("dashboard"))


@app.route("/users/<int:id>/edit", methods=["POST"])
def edit_user(id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    if not user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("users"))

    name = request.form.get("name", "").strip()
    if not name:
        flash("Name is required.", "error")
        conn.close()
        return redirect(url_for("users"))

    weight_lbs = float(request.form["weight_lbs"]) if request.form.get("weight_lbs") else None
    height_ft = int(request.form["height_ft"]) if request.form.get("height_ft") else None
    height_in = int(request.form["height_in"]) if request.form.get("height_in") else None
    favorite_routine_id = int(request.form["favorite_routine_id"]) if request.form.get("favorite_routine_id") else None
    favorite_video_id = int(request.form["favorite_video_id"]) if request.form.get("favorite_video_id") else None
    notes = request.form.get("notes", "")
    weighin_day = int(request.form.get("weighin_day", 0))
    age = int(request.form["age"]) if request.form.get("age") else None
    gender = request.form.get("gender", "female")
    diet_focus = request.form.get("diet_focus", "calorie")
    prolapse_safe = 1 if request.form.get("prolapse_safe") == "on" else 0
    if_start_hour = int(request.form["if_start_hour"]) if request.form.get("if_start_hour") else None
    if_end_hour = int(request.form["if_end_hour"]) if request.form.get("if_end_hour") else None

    b = calc_bmi(weight_lbs, height_ft or 0, height_in or 0)

    conn.execute(
        "UPDATE users SET name=?, weight_lbs=?, height_ft=?, height_in=?, bmi=?, "
        "favorite_routine_id=?, favorite_video_id=?, notes=?, weighin_day=?, age=?, gender=?, prolapse_safe=?, "
        "if_start_hour=?, if_end_hour=?, diet_focus=? "
        "WHERE id=?",
        (name, weight_lbs, height_ft, height_in, b, favorite_routine_id, favorite_video_id, notes,
         weighin_day, age, gender, prolapse_safe, if_start_hour, if_end_hour, diet_focus, id),
    )
    conn.commit()
    conn.close()
    flash("Profile updated.", "success")
    return redirect(url_for("users"))


@app.route("/api/users")
def api_users():
    conn = get_db()
    rows = conn.execute("SELECT id, name, weight_lbs, height_ft, height_in, bmi, start_date, notes FROM users ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/bmi/<int:id>")
def api_bmi(id):
    conn = get_db()
    user = conn.execute("SELECT weight_lbs, height_ft, height_in, bmi FROM users WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not user:
        return jsonify({"error": "User not found"}), 404
    b = user["bmi"] if user["bmi"] else calc_bmi(user["weight_lbs"], user["height_ft"] or 0, user["height_in"] or 0)
    return jsonify({"bmi": b, "category": bmi_category(b)})


# ─── Pages ──────────────────────────────────────────────────────────────────


@app.route("/")
def dashboard():
    settings = get_settings()
    conn = get_db()
    uid = session.get("user_id")

    # This week's workouts
    monday, sunday = get_week_range()
    week_workouts = conn.execute(
        "SELECT * FROM workouts WHERE user_id = ? AND date >= ? AND date <= ? ORDER BY date DESC",
        (uid, monday.isoformat(), sunday.isoformat()),
    ).fetchall()

    week_duration = sum(w["duration_min"] for w in week_workouts)
    week_calories = sum(w["calories"] or 0 for w in week_workouts)

    # This month's workouts
    first = date.today().replace(day=1)
    month_workouts = conn.execute(
        "SELECT * FROM workouts WHERE user_id = ? AND date >= ? ORDER BY date DESC",
        (uid, first.isoformat()),
    ).fetchall()
    month_duration = sum(w["duration_min"] for w in month_workouts)
    month_calories = sum(w["calories"] or 0 for w in month_workouts)

    # Total all-time
    total = conn.execute(
        "SELECT COUNT(*) as cnt, COALESCE(SUM(duration_min),0) as dur, COALESCE(SUM(calories),0) as cal FROM workouts WHERE user_id = ?",
        (uid,),
    ).fetchone()

    # Last 7 days of daily metrics (weight)
    metrics = conn.execute(
        "SELECT * FROM daily_metrics WHERE user_id = ? ORDER BY date DESC LIMIT 7",
        (uid,),
    ).fetchall()

    # Recent workouts (last 14)
    recent = conn.execute(
        "SELECT * FROM workouts WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 14",
        (uid,),
    ).fetchall()

    # Streak & consistency
    streak = get_streak(conn, uid)
    weekly = get_weekly_stats(conn, uid)
    monthly = get_monthly_stats(conn, uid)
    heatmap = get_heatmap_data(conn, uid)

    # Evaluate badges on dashboard load
    new_badges = evaluate_badges(uid)

    # Get a recommendation for the dashboard widget
    user_row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    dashboard_rec = recommend_workout(conn, uid, dict(user_row)) if user_row else None

    conn.close()

    return render_template(
        "dashboard.html",
        settings=settings,
        week_workouts=week_workouts,
        week_duration=week_duration,
        week_calories=week_calories,
        month_duration=month_duration,
        month_calories=month_calories,
        total=total,
        metrics=metrics,
        recent=recent,
        streak=streak,
        weekly=weekly,
        monthly=monthly,
        heatmap=heatmap,
        new_badges=new_badges,
        dashboard_rec=dashboard_rec,
    )


@app.route("/badges")
def badges():
    conn = get_db()
    uid = session.get("user_id")

    # Evaluate any unearned badges first
    evaluate_badges(uid)

    # Get all badges with earned status and progress
    all_badges = conn.execute("SELECT * FROM badges ORDER BY category, sort_order").fetchall()
    earned_ids = {
        row["badge_id"]
        for row in conn.execute(
            "SELECT badge_id, earned_at FROM user_badges WHERE user_id = ?", (uid,)
        ).fetchall()
    }
    earned_map = {
        row["badge_id"]: row["earned_at"]
        for row in conn.execute(
            "SELECT badge_id, earned_at FROM user_badges WHERE user_id = ?", (uid,)
        ).fetchall()
    }

    badge_list = []
    for b in all_badges:
        b = dict(b)
        b["earned"] = b["id"] in earned_ids
        b["earned_at"] = earned_map.get(b["id"], None)
        if not b["earned"]:
            current, target = get_badge_progress(conn, uid, b)
            b["progress"] = current
            b["target"] = target
            b["pct"] = min(100, int((current / target) * 100)) if target > 0 else 0
        else:
            b["progress"] = 0
            b["target"] = 0
            b["pct"] = 100
        badge_list.append(b)

    total_earned = len(earned_ids)
    total_badges = len(all_badges)
    conn.close()

    return render_template(
        "badges.html",
        badges=badge_list,
        total_earned=total_earned,
        total_badges=total_badges,
    )


@app.route("/recommend")
def recommend():
    conn = get_db()
    uid = session.get("user_id")
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if not user:
        conn.close()
        return redirect(url_for("users"))
    user = dict(user)

    rec = recommend_workout(conn, uid, user)
    variety = get_variety_report(conn, uid)

    # Get 2 alternatives
    alternatives = []
    if rec:
        if user.get("prolapse_safe"):
            alt_categories = ["prolapse", "yoga"]
        else:
            alt_categories = ["10min", "20min", "dumbbell", "back_biceps", "chest_tricep", "shoulder_legs", "yoga"]
        placeholders = ",".join("?" * len(alt_categories))
        all_available = conn.execute(
            f"SELECT * FROM videos WHERE category IN ({placeholders}) AND id != ?",
            alt_categories + [rec["video"]["id"]],
        ).fetchall()
        import random
        alternatives = [dict(v) for v in random.sample(all_available, min(2, len(all_available)))]

    conn.close()
    return render_template("recommend.html", rec=rec, alternatives=alternatives, variety=variety)


@app.route("/api/recommend-random")
def api_recommend_random():
    import random
    conn = get_db()
    uid = session.get("user_id")
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if not user:
        conn.close()
        return jsonify({"ok": False, "error": "Not signed in"}), 401
    user = dict(user)

    if user.get("prolapse_safe"):
        categories = ["prolapse", "yoga"]
    else:
        categories = ["10min", "20min", "dumbbell", "back_biceps", "chest_tricep", "shoulder_legs", "yoga"]
    placeholders = ",".join("?" * len(categories))
    videos = conn.execute(
        f"SELECT * FROM videos WHERE category IN ({placeholders})",
        categories,
    ).fetchall()
    conn.close()

    if videos:
        v = random.choice(videos)
        return jsonify({"url": v["url"], "name": v["name"]})
    return jsonify({"url": None})


@app.route("/workouts", methods=["GET", "POST"])
def workouts():
    conn = get_db()
    uid = session.get("user_id")

    if request.method == "POST":
        w = request.form
        exertion_val = None
        ex_str = w.get("exertion", "").strip()
        if ex_str:
            try:
                exertion_val = int(ex_str)
                if not 1 <= exertion_val <= 5:
                    exertion_val = None
            except (ValueError, TypeError):
                pass
        conn.execute(
            "INSERT INTO workouts (user_id, date, duration_min, calories, heart_rate_avg, heart_rate_max, workout_type, intensity, notes, exertion) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                uid,
                w["date"],
                int(w["duration_min"]),
                int(w.get("calories")) if w.get("calories") else None,
                int(w.get("heart_rate_avg")) if w.get("heart_rate_avg") else None,
                int(w.get("heart_rate_max")) if w.get("heart_rate_max") else None,
                w["workout_type"],
                w["intensity"],
                w.get("notes", ""),
                exertion_val,
            ),
        )
        conn.commit()
        total_workouts = conn.execute("SELECT COUNT(*) FROM workouts WHERE user_id = ?", (uid,)).fetchone()[0]
        dur = int(w["duration_min"])
        cals = int(w.get("calories")) if w.get("calories") else None
        summary, emoji = generate_workout_summary(dur, cals, w["workout_type"], total_workouts, exertion_val)
        session["last_workout_summary"] = summary
        session["last_workout_emoji"] = emoji
        new_badges = evaluate_badges(uid)
        if new_badges:
            badge_names = ", ".join(b["name"] for b in new_badges)
            flash(f"Workout logged! Badges earned: {badge_names}", "success")
        else:
            flash("Workout logged!", "success")
        return redirect(url_for("workouts"))

    # Paginated list
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    total = conn.execute("SELECT COUNT(*) FROM workouts WHERE user_id = ?", (uid,)).fetchone()[0]
    rows = conn.execute(
        "SELECT * FROM workouts WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ? OFFSET ?",
        (uid, per_page, offset),
    ).fetchall()
    total_pages = max(1, (total + per_page - 1) // per_page)

    conn.close()

    return render_template(
        "workouts.html",
        workouts=rows,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@app.route("/workouts/<int:id>/delete", methods=["POST"])
def delete_workout(id):
    conn = get_db()
    uid = session.get("user_id")
    conn.execute("DELETE FROM workouts WHERE id = ? AND user_id = ?", (id, uid))
    conn.commit()
    conn.close()
    flash("Workout deleted.", "info")
    return redirect(url_for("workouts"))


@app.route("/api/record-video-workout", methods=["POST"])
def api_record_video_workout():
    """Record a workout entry triggered by completing an official video.

    Body JSON: { duration_min: int, video_name?: str,
                 intensity?: str, workout_type?: str }
    """
    uid = session.get("user_id")
    if not uid:
        return jsonify({"ok": False, "error": "Not signed in"}), 401

    data = request.get_json(silent=True) or {}
    try:
        duration = int(data.get("duration_min", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Bad duration_min"}), 400
    if duration < 1:
        return jsonify({"ok": False, "error": "Bad duration_min"}), 400

    video_name = (data.get("video_name") or "").strip()[:120]
    intensity = (data.get("intensity") or "moderate").lower()
    if intensity not in ("beginner", "moderate", "high"):
        intensity = "moderate"

    workout_type = (data.get("workout_type") or "hiit").lower()
    valid_types = ("steady", "hiit", "tabata", "cross-training", "custom")
    if workout_type not in valid_types:
        workout_type = "hiit"

    today = date.today().isoformat()
    notes = "Logged automatically from video"
    if video_name:
        notes += f": {video_name}"

    # Calorie estimate from the user's most recent weight
    weight_kg, weight_source = latest_weight_kg(uid)
    calories = estimate_calories(weight_kg, intensity, duration)
    notes += f" (~{calories} kcal est., {weight_kg:g} kg)"

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO workouts (user_id, date, duration_min, calories, "
        "workout_type, intensity, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uid, today, duration, calories, workout_type, intensity, notes),
    )
    conn.commit()
    new_id = cur.lastrowid
    new_badges = evaluate_badges(uid)
    conn.close()
    result = {"ok": True, "id": new_id, "date": today,
                "duration_min": duration, "calories": calories,
                "weight_kg": weight_kg, "weight_source": weight_source,
                "workout_type": workout_type, "intensity": intensity}
    if new_badges:
        result["new_badges"] = [{"name": b["name"], "icon": b["icon"]} for b in new_badges]
    return jsonify(result)


@app.route("/progress", methods=["GET", "POST"])
def progress():
    conn = get_db()
    uid = session.get("user_id")
    settings = get_settings()
    if request.method == "POST":
        m = request.form
        conn.execute(
            "INSERT OR REPLACE INTO daily_metrics "
            "(user_id, date, weight, waist, hips, chest, left_arm, right_arm, left_thigh, right_thigh, resting_hr, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                uid,
                m["date"],
                float(m.get("weight")) if m.get("weight") else None,
                float(m.get("waist")) if m.get("waist") else None,
                float(m.get("hips")) if m.get("hips") else None,
                float(m.get("chest")) if m.get("chest") else None,
                float(m.get("left_arm")) if m.get("left_arm") else None,
                float(m.get("right_arm")) if m.get("right_arm") else None,
                float(m.get("left_thigh")) if m.get("left_thigh") else None,
                float(m.get("right_thigh")) if m.get("right_thigh") else None,
                int(m.get("resting_hr")) if m.get("resting_hr") else None,
                m.get("notes", ""),
            ),
        )
        conn.commit()
        new_badges = evaluate_badges(uid)
        if new_badges:
            badge_names = ", ".join(b["name"] for b in new_badges)
            flash(f"Metrics saved! Badges earned: {badge_names}", "success")
        else:
            flash("Metrics saved!", "success")
        return redirect(url_for("progress"))

    # All metrics, newest first
    metrics = conn.execute(
        "SELECT * FROM daily_metrics WHERE user_id = ? ORDER BY date DESC",
        (uid,),
    ).fetchall()

    # Weight trend: last 90 days
    weight_trend = conn.execute(
        "SELECT date, weight FROM daily_metrics WHERE user_id = ? AND weight IS NOT NULL ORDER BY date ASC LIMIT 90",
        (uid,),
    ).fetchall()

    # Weigh-in context
    user_row = conn.execute("SELECT weighin_day FROM users WHERE id = ?", (uid,)).fetchone()
    weighin_day = user_row["weighin_day"] if user_row else 0
    weighin_is_today = is_weighin_day(weighin_day)
    weighin_day_name = get_weighin_day_name(weighin_day)

    # Progress photos, newest first
    photos = conn.execute(
        "SELECT * FROM progress_photos WHERE user_id = ? ORDER BY date DESC, angle ASC",
        (uid,),
    ).fetchall()

    # Wellness log, newest first
    wellness = conn.execute(
        "SELECT * FROM wellness_log WHERE user_id = ? ORDER BY date DESC",
        (uid,),
    ).fetchall()

    conn.close()

    return render_template(
        "progress.html",
        settings=settings,
        metrics=metrics,
        weight_trend=weight_trend,
        weighin_is_today=weighin_is_today, weighin_day_name=weighin_day_name,
        photos=photos,
        wellness=wellness,
    )


@app.route("/videos", methods=["GET", "POST"])
def videos():
    conn = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        coach = request.form.get("coach", "").strip()
        duration_min = request.form.get("duration_min", "0").strip()
        url = request.form.get("url", "").strip()
        category = request.form.get("category", "").strip()
        intensity = request.form.get("intensity", "moderate").strip()
        description = request.form.get("description", "").strip()
        if not name or not url:
            flash("Video name and URL are required.", "error")
            conn.close()
            rows = conn.execute("SELECT * FROM videos ORDER BY category, duration_min, name").fetchall()
            conn.close()
            return render_template("videos.html", videos=rows)
        try:
            duration_min = int(duration_min)
        except ValueError:
            flash("Duration must be a number.", "error")
            conn.close()
            rows = conn.execute("SELECT * FROM videos ORDER BY category, duration_min, name").fetchall()
            conn.close()
            return render_template("videos.html", videos=rows)
        conn.execute(
            "INSERT INTO videos (name, coach, duration_min, url, category, intensity, description) VALUES (?,?,?,?,?,?,?)",
            (name, coach, duration_min, url, category, intensity, description),
        )
        conn.commit()
        flash(f'"{name}" added to the video library.', "success")
        conn.close()
        return redirect(url_for("videos"))
    rows = conn.execute("SELECT * FROM videos ORDER BY category, duration_min, name").fetchall()
    conn.close()
    return render_template("videos.html", videos=rows)


@app.route("/routines")
def routines():
    conn = get_db()
    rows = conn.execute("SELECT * FROM routines ORDER BY category, difficulty, total_min").fetchall()
    conn.close()
    return render_template("routines.html", routines=rows)


@app.route("/schedule")
def schedule():
    conn = get_db()
    plans = conn.execute("SELECT * FROM schedule_plans ORDER BY week_start").fetchall()
    for plan in plans:
        plan = dict(plan)
        plan["days"] = conn.execute(
            "SELECT * FROM schedule_days WHERE plan_id = ? ORDER BY "
            "CASE day_name WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 "
            "WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 "
            "WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7 END",
            (plan["id"],),
        ).fetchall()
    conn.close()

    current_phase = get_current_phase()
    return render_template("schedule.html", plans=plans, current_phase=current_phase)


@app.route("/reference")
def reference():
    return render_template("reference.html")


# ─── API endpoints for charts ───────────────────────────────────────────────


@app.route("/api/weight-chart")
def api_weight_chart():
    conn = get_db()
    uid = session.get("user_id")
    rows = conn.execute(
        "SELECT date, weight FROM daily_metrics WHERE user_id = ? AND weight IS NOT NULL ORDER BY date ASC LIMIT 180",
        (uid,),
    ).fetchall()
    conn.close()
    return jsonify([{"date": r["date"], "weight": r["weight"]} for r in rows])


@app.route("/api/workout-chart")
def api_workout_chart():
    """Last 90 days of workout data for charting."""
    conn = get_db()
    uid = session.get("user_id")
    cutoff = (date.today() - timedelta(days=90)).isoformat()
    rows = conn.execute(
        "SELECT date, duration_min, calories FROM workouts WHERE user_id = ? AND date >= ? ORDER BY date ASC",
        (uid, cutoff),
    ).fetchall()
    conn.close()
    return jsonify([{"date": r["date"], "duration_min": r["duration_min"], "calories": r["calories"] or 0} for r in rows])


@app.route("/api/weekly-summary")
def api_weekly_summary():
    """Last 12 weeks of aggregated data."""
    conn = get_db()
    uid = session.get("user_id")
    # Get each Monday for the last 12 weeks
    today = date.today()
    weeks = []
    for i in range(11, -1, -1):
        ref = today - timedelta(weeks=i)
        monday = ref - timedelta(days=ref.weekday())
        sunday = monday + timedelta(days=6)
        row = conn.execute(
            "SELECT COALESCE(SUM(duration_min),0) as dur, COALESCE(SUM(calories),0) as cal, COUNT(*) as cnt "
            "FROM workouts WHERE user_id = ? AND date >= ? AND date <= ?",
            (uid, monday.isoformat(), sunday.isoformat()),
        ).fetchone()
        weeks.append({
            "week": monday.isoformat(),
            "duration": row["dur"],
            "calories": row["cal"],
            "sessions": row["cnt"],
        })
    conn.close()
    return jsonify(weeks)


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    conn = get_db()
    if request.method == "POST":
        data = request.get_json()
        conn.execute(
            "INSERT OR REPLACE INTO settings (id, start_weight, goal_weight, unit, start_date) "
            "VALUES (1, ?, ?, ?, ?)",
            (
                data.get("start_weight"),
                data.get("goal_weight"),
                data.get("unit", "lbs"),
                data.get("start_date", date.today().isoformat()),
            ),
        )
        conn.commit()
        conn.close()
        return jsonify({"ok": True})

    row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    conn.close()
    return jsonify(dict(row) if row else {})



@app.route("/api/weekly-weighin", methods=["POST"])
def api_weekly_weighin():
    conn = get_db()
    uid = session.get("user_id")
    data = request.get_json()
    weight = float(data.get("weight")) if data.get("weight") else None
    if weight is None or weight <= 0:
        conn.close()
        return jsonify({"error": "Valid weight required"}), 400
    notes = data.get("notes", "")
    today = date.today()
    week_num = today.isocalendar()[1]
    conn.execute(
        "INSERT OR REPLACE INTO weekly_weighins "
        "(user_id, date, weight, notes, week_number) "
        "VALUES (?, ?, ?, ?, ?)",
        (uid, today.isoformat(), float(weight), notes, week_num),
    )
    conn.commit()
    settings = get_settings()
    start_weight = settings.get("start_weight")
    unit = settings.get("unit", "lbs")
    if start_weight is None:
        conn.execute("UPDATE settings SET start_weight = ? WHERE id = 1", (weight,))
        conn.commit()
        start_weight = weight
        feedback = "Welcome! This is your starting weight."
    else:
        total_loss = round(start_weight - weight, 1)
        last_row = conn.execute("SELECT weight FROM weekly_weighins WHERE user_id = ? AND date < ? ORDER BY date DESC LIMIT 1", (uid, today.isoformat())).fetchone()
        feedback = weighin_feedback(
            last_row["weight"] if last_row else None, weight, total_loss
        )
    milestones = check_milestones(conn, uid, weight, start_weight)
    ema = compute_ema(conn, uid, span=4)
    conn.close()
    return jsonify({
        "ok": True, "weight": weight, "start_weight": start_weight,
        "total_loss": round(start_weight - weight, 1),
        "milestones": milestones, "ema_4week": ema, "week_number": week_num,
        "feedback": feedback,
    })


@app.route("/api/weekly-chart")
def api_weekly_chart():
    conn = get_db()
    uid = session.get("user_id")
    rows = conn.execute(
        "SELECT date, weight FROM weekly_weighins "
        "WHERE user_id = ? ORDER BY date ASC LIMIT 26",
        (uid,),
    ).fetchall()
    conn.close()
    weights = [r["weight"] for r in rows]
    ema_values = compute_ema_list(weights, span=4)
    return jsonify([
        {"date": r["date"], "weight": r["weight"],
         "ema": ema_values[i] if i < len(ema_values) else None}
        for i, r in enumerate(rows)
    ])


@app.route("/api/weighin-status")
def api_weighin_status():
    conn = get_db()
    uid = session.get("user_id")
    user_row = conn.execute("SELECT weighin_day FROM users WHERE id = ?", (uid,)).fetchone()
    weighin_day = user_row["weighin_day"] if user_row else 0
    settings = get_settings()
    start_weight = settings.get("start_weight")
    last = conn.execute(
        "SELECT date, weight FROM weekly_weighins "
        "WHERE user_id = ? ORDER BY date DESC LIMIT 1",
        (uid,),
    ).fetchone()
    today_weighin = conn.execute(
        "SELECT weight FROM weekly_weighins "
        "WHERE user_id = ? AND date = ?",
        (uid, date.today().isoformat()),
    ).fetchone()
    conn.close()
    nxt = next_weighin_date(weighin_day)
    days_until = (nxt - date.today()).days
    return jsonify({
        "weighin_day": weighin_day,
        "weighin_day_name": get_weighin_day_name(weighin_day),
        "is_today": is_weighin_day(weighin_day),
        "next_date": nxt.isoformat(),
        "days_until": days_until,
        "last_weight": last["weight"] if last else None,
        "last_date": last["date"] if last else None,
        "start_weight": start_weight,
        "total_loss": round(start_weight - last["weight"], 1) if start_weight and last else None,
        "has_weighin_today": bool(today_weighin),
    })


@app.route("/api/weighin-day", methods=["POST"])
def api_weighin_day():
    conn = get_db()
    uid = session.get("user_id")
    data = request.get_json()
    day = int(data.get("weighin_day"))
    if day is None or not (0 <= day <= 6):
        conn.close()
        return jsonify({"error": "weighin_day must be 0-6"}), 400
    conn.execute("UPDATE users SET weighin_day = ? WHERE id = ?", (day, uid))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "weighin_day": day})

def get_fasting_status(user):
    """Return fasting timer state for a user."""
    start_h = user.get('if_start_hour') if hasattr(user, 'get') else getattr(user, 'if_start_hour', None)
    end_h = user.get('if_end_hour') if hasattr(user, 'get') else getattr(user, 'if_end_hour', None)
    if start_h is None or end_h is None:
        return None
    now = datetime.now()
    start_minutes = start_h * 60
    end_minutes = end_h * 60
    now_minutes = now.hour * 60 + now.minute
    # Determine if currently in eating or fasting window
    if start_minutes < end_minutes:
        # Normal window (e.g., 12pm-8pm)
        eating = start_minutes <= now_minutes < end_minutes
    else:
        # Overnight window (e.g., 8pm-12pm)
        eating = now_minutes >= start_minutes or now_minutes < end_minutes
    if eating:
        # Minutes until eating window ends
        if start_minutes < end_minutes:
            remaining = end_minutes - now_minutes
        else:
            remaining = (24 * 60 - now_minutes) + start_minutes if now_minutes >= start_minutes else (start_minutes - now_minutes)
        return {'fasting': False, 'minutes_remaining': max(0, remaining), 'eating_window': f'{start_h}:00-{end_h}:00'}
    else:
        # Minutes until eating window starts
        if start_minutes < end_minutes:
            remaining = start_minutes - now_minutes if now_minutes < start_minutes else (24 * 60 - now_minutes) + start_minutes
        else:
            remaining = start_minutes - now_minutes
        return {'fasting': True, 'minutes_remaining': max(0, remaining), 'eating_window': f'{start_h}:00-{end_h}:00'}


@app.route("/api/fasting-status")
def api_fasting_status():
    uid = session.get("user_id")
    if not uid:
        return jsonify(None)
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()
    if not user:
        return jsonify(None)
    status = get_fasting_status(user)
    return jsonify(status)


@app.route("/nutrition")
def nutrition():
    uid = session.get("user_id")
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if not user:
        conn.close()
        return redirect(url_for("users"))
    user = dict(user)
    today = date.today().isoformat()

    # Auto-create calorie goal if missing
    goal = conn.execute("SELECT * FROM calorie_goals WHERE user_id = ?", (uid,)).fetchone()
    if not goal:
        bmr = calculate_bmr(user)
        daily_goal = int(bmr * 1.2 - 500)
        conn.execute(
            "INSERT INTO calorie_goals (user_id, daily_goal, water_glasses_goal) VALUES (?, ?, ?)",
            (uid, daily_goal, 8),
        )
        conn.commit()
        goal = conn.execute("SELECT * FROM calorie_goals WHERE user_id = ?", (uid,)).fetchone()
    goal = dict(goal)

    # Today's food entries
    foods = conn.execute(
        "SELECT * FROM nutrition_log WHERE user_id = ? AND date = ? ORDER BY meal_type, created_at",
        (uid, today),
    ).fetchall()

    # Water intake
    water = conn.execute(
        "SELECT * FROM daily_water WHERE user_id = ? AND date = ?",
        (uid, today),
    ).fetchone()
    if not water:
        conn.execute(
            "INSERT INTO daily_water (user_id, date, glasses) VALUES (?, ?, 0)",
            (uid, today),
        )
        conn.commit()
        water = conn.execute("SELECT * FROM daily_water WHERE user_id = ? AND date = ?", (uid, today)).fetchone()
    water = dict(water)

    # Workout calories burned today
    workout_cals = conn.execute(
        "SELECT COALESCE(SUM(calories), 0) as total FROM workouts WHERE user_id = ? AND date = ?",
        (uid, today),
    ).fetchone()["total"]

    # Totals
    total_cals = sum(f["calories"] or 0 for f in foods)
    total_protein = sum(f["protein_g"] or 0 for f in foods)
    total_carbs = sum(f["carbs_g"] or 0 for f in foods)
    total_fat = sum(f["fat_g"] or 0 for f in foods)
    net_cals = total_cals - workout_cals

    # Food database for quick-add
    food_db = conn.execute("SELECT * FROM food_database ORDER BY name").fetchall()
    conn.close()

    return render_template(
        "nutrition.html",
        user=user, today=today, foods=foods, water=water, goal=goal,
        total_cals=total_cals, total_protein=total_protein,
        total_carbs=total_carbs, total_fat=total_fat,
        net_cals=net_cals, workout_cals=workout_cals,
        food_db=food_db,
    )

def get_user_id():
    """Get user_id from query param (for app clients) or session (for browser)."""
    uid = request.args.get("user_id")
    if uid is not None:
        return int(uid)
    return session.get("user_id")

@app.route("/api/nutrition/today")

def api_nutrition_today():
    """JSON endpoint for today's nutrition data — used by the Android app."""
    uid = get_user_id()
    if not uid:
        return jsonify(None), 401
    conn = get_db()
    today = date.today().isoformat()

    goal = conn.execute("SELECT * FROM calorie_goals WHERE user_id = ?", (uid,)).fetchone()
    if not goal:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        bmr = calculate_bmr(dict(user))
        daily_goal = int(bmr * 1.2 - 500)
        conn.execute(
            "INSERT INTO calorie_goals (user_id, daily_goal, water_glasses_goal) VALUES (?, ?, ?)",
            (uid, daily_goal, 8),
        )
        conn.commit()
        goal = conn.execute("SELECT * FROM calorie_goals WHERE user_id = ?", (uid,)).fetchone()
    goal = dict(goal)

    # Get user's diet_focus
    user = conn.execute("SELECT diet_focus FROM users WHERE id = ?", (uid,)).fetchone()
    diet_focus = (user and user["diet_focus"]) or "calorie"

    foods = conn.execute(
        "SELECT * FROM nutrition_log WHERE user_id = ? AND date = ? ORDER BY meal_type, created_at",
        (uid, today),
    ).fetchall()

    water = conn.execute(
        "SELECT * FROM daily_water WHERE user_id = ? AND date = ?",
        (uid, today),
    ).fetchone()
    if not water:
        conn.execute(
            "INSERT INTO daily_water (user_id, date, glasses) VALUES (?, ?, 0)",
            (uid, today),
        )
        conn.commit()
        water = conn.execute("SELECT * FROM daily_water WHERE user_id = ? AND date = ?", (uid, today)).fetchone()
    water = dict(water)

    workout_cals = conn.execute(
        "SELECT COALESCE(SUM(calories), 0) as total FROM workouts WHERE user_id = ? AND date = ?",
        (uid, today),
    ).fetchone()["total"]

    total_cals = sum(f["calories"] or 0 for f in foods)
    total_protein = sum(f["protein_g"] or 0 for f in foods)
    total_carbs = sum(f["carbs_g"] or 0 for f in foods)
    total_fat = sum(f["fat_g"] or 0 for f in foods)
    total_fiber = sum(f["fiber_g"] or 0 for f in foods)
    net_cals = total_cals - workout_cals

    user = conn.execute("SELECT name FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()

    return jsonify({
        "user_name": user["name"] if user else "Unknown",
        "today": today,
        "diet_focus": diet_focus,
        "goal": {
            "daily_goal": goal["daily_goal"],
            "water_glasses_goal": goal["water_glasses_goal"],
            "protein_goal": goal.get("protein_goal") or 0,
            "carbs_goal": goal.get("carbs_goal") or 0,
            "fat_goal": goal.get("fat_goal") or 0,
            "diet_focus": diet_focus,
        },
        "totals": {
            "calories": total_cals,
            "protein_g": round(total_protein, 1),
            "carbs_g": round(total_carbs, 1),
            "fat_g": round(total_fat, 1),
            "fiber_g": round(total_fiber, 1),
            "net_calories": net_cals,
            "workout_calories": workout_cals,
        },
        "water": {"glasses": water["glasses"]},
        "foods": [dict(f) for f in foods],
    })
@app.route("/api/recent-scans")
def api_recent_scans():
    """Return the 20 most recent barcode-scanned nutrition_log entries."""
    uid = get_user_id()
    if not uid:
        return jsonify(None), 401
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT barcode, food_name, calories, protein_g, carbs_g, fat_g, meal_type, date "
        "FROM nutrition_log WHERE user_id = ? AND barcode != '' AND barcode IS NOT NULL "
        "ORDER BY created_at DESC LIMIT 20",
        (uid,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
@app.route("/api/search-foods")
def api_search_foods():
    """Search local barcode_cache by name, then ChowAPI if needed."""
    uid = get_user_id()
    if not uid:
        return jsonify(None), 401
    query = request.args.get("q", "").strip()
    use_api = request.args.get("api", "false").lower() == "true"
    import json as _json

    if use_api:
        # Search ChowAPI
        import urllib.request, urllib.error
        url = f'https://api.chowapi.dev/v1/search?q={urllib.parse.quote(query)}&limit=20'
        try:
            req = urllib.request.Request(url, headers={
                'Authorization': f'Bearer {CHOW_API_KEY}',
                'User-Agent': 'MaxiFitness/1.0'
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = _json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return jsonify({"results": [], "error": f"ChowAPI error: {e.code}"}), 200
        except Exception as e:
            return jsonify({"results": [], "error": str(e)}), 200

        results = []
        for item in data.get("results", []):
            n = item.get("nutrients_per_serving", {}) or item.get("nutrients", {})
            results.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "brand": item.get("brand"),
                "barcode": item.get("barcode"),
                "barcodes": item.get("barcodes", []),
                "calories": n.get("calories"),
                "protein": n.get("protein"),
                "carbs": n.get("carbs"),
                "fat": n.get("fat"),
                "fiber": n.get("fiber"),
                "sugar": n.get("sugar"),
                "sodium": n.get("sodium"),
                "saturated_fat": n.get("saturated_fat"),
                "serving_description": item.get("serving", {}).get("description"),
                "serving_gram_weight": item.get("serving", {}).get("gram_weight"),
                "data_quality": item.get("data_quality"),
                "source": item.get("source"),
                "image_url": item.get("image_url"),
            })
        # Cache results
        conn = get_db()
        for r in results:
            if r.get("barcode"):
                existing = conn.execute("SELECT id FROM barcode_cache WHERE barcode = ?", (r["barcode"],)).fetchone()
                if not existing:
                    try:
                        conn.execute(
                            "INSERT INTO barcode_cache (barcode, name, brand, category, calories, protein, carbs, fat, "
                            "fiber, sugar, sodium, cholesterol, saturated_fat, serving_gram_weight, serving_description, "
                            "data_quality, source, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (r["barcode"], r["name"], r["brand"], None,
                             r["calories"], r["protein"], r["carbs"], r["fat"],
                             r["fiber"], r["sugar"], r["sodium"], None, r["saturated_fat"],
                             r["serving_gram_weight"], r["serving_description"],
                             r["data_quality"], r["source"], r["image_url"]),
                        )
                    except sqlite3.IntegrityError:
                        pass
        conn.commit()
        conn.close()
        return jsonify({"results": results})

    # Search local barcode_cache, nutrition_log, and food_database by name
    conn = get_db()
    seen = set()
    results = []

    # 1. nutrition_log (most recent entry per food_name) — shown first
    for r in conn.execute(
        "SELECT food_name, calories, protein_g, carbs_g, fat_g, fiber_g, meal_type, date FROM nutrition_log "
        "WHERE user_id = ? AND food_name LIKE ? ORDER BY date DESC, id DESC",
        (uid, f"%{query}%",)
    ).fetchall():
        key = r["food_name"].lower()
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "name": r["food_name"], "brand": None, "barcode": None,
            "calories": r["calories"], "protein": r["protein_g"], "carbs": r["carbs_g"], "fat": r["fat_g"],
            "fiber": r["fiber_g"], "sugar": None, "sodium": None, "saturated_fat": None,
            "serving_description": None, "serving_gram_weight": None,
            "data_quality": None, "source": "nutrition_log", "image_url": None,
            "from": "nutrition_log"
        })

    # 2. barcode_cache
    for r in conn.execute("SELECT * FROM barcode_cache WHERE name LIKE ? ORDER BY name LIMIT 20", (f"%{query}%",)).fetchall():
        key = r["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "name": r["name"], "brand": r["brand"], "barcode": r["barcode"],
            "calories": r["calories"], "protein": r["protein"], "carbs": r["carbs"], "fat": r["fat"],
            "fiber": r["fiber"], "sugar": r["sugar"], "sodium": r["sodium"], "saturated_fat": r["saturated_fat"],
            "serving_description": r["serving_description"], "serving_gram_weight": r["serving_gram_weight"],
            "data_quality": r["data_quality"], "source": r["source"], "image_url": r["image_url"],
            "from": "barcode_cache"
        })

    # 3. food_database
    for r in conn.execute("SELECT * FROM food_database WHERE name LIKE ? ORDER BY name LIMIT 20", (f"%{query}%",)).fetchall():
        key = r["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "name": r["name"], "brand": None, "barcode": None,
            "calories": r["calories"], "protein": r["protein_g"], "carbs": r["carbs_g"], "fat": r["fat_g"],
            "fiber": r["fiber_g"], "sugar": None, "sodium": None, "saturated_fat": None,
            "serving_description": r["serving_desc"], "serving_gram_weight": None,
            "data_quality": None, "source": "food_database", "image_url": None,
            "from": "food_database"
        })

    conn.close()
    # Cap at 20 results total
    return jsonify({"results": results[:20]})


@app.route("/api/weekly-nutrition")
def api_weekly_nutrition():
    conn = get_db()
    uid = session.get("user_id")
    if not uid:
        conn.close()
        return jsonify(None)
    goal = conn.execute("SELECT * FROM calorie_goals WHERE user_id = ?", (uid,)).fetchone()
    if not goal:
        conn.close()
        return jsonify(None)
    goal = dict(goal)
    daily_goal = goal.get("daily_goal", 1800)
    water_goal = goal.get("water_glasses_goal", 8)
    days = []
    protein_hit = 0
    water_hit = 0
    total_protein = 0
    total_water = 0
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        food_rows = conn.execute(
            "SELECT * FROM nutrition_log WHERE user_id = ? AND date = ?", (uid, d)
        ).fetchall()
        water_row = conn.execute(
            "SELECT * FROM daily_water WHERE user_id = ? AND date = ?", (uid, d)
        ).fetchone()
        cals = sum(f["calories"] or 0 for f in food_rows)
        protein = sum(f["protein_g"] or 0 for f in food_rows)
        water = dict(water_row)["glasses"] if water_row else 0
        total_protein += protein
        total_water += water
        days.append({
            "date": d,
            "label": (date.today() - timedelta(days=i)).strftime("%a"),
            "calories": cals,
            "protein": round(protein, 1),
            "water": water,
        })
    conn.close()
    # Determine tips
    tips = []
    avg_water = total_water / 7
    avg_protein = total_protein / 7
    if avg_water < water_goal:
        tips.append("💧 Try keeping a bottle at your desk to hit your water goal")
    if avg_protein < 0.6 * (daily_goal / 4):
        tips.append("🥩 Add a protein source to each meal to boost intake")
    cal_days_hit = sum(1 for d in days if d["calories"] <= daily_goal and d["calories"] > 0)
    water_days_hit = sum(1 for d in days if d["water"] >= water_goal)
    return jsonify({
        "days": days,
        "daily_goal": daily_goal,
        "water_goal": water_goal,
        "cal_days_hit": cal_days_hit,
        "water_days_hit": water_days_hit,
        "avg_water": round(avg_water, 1),
        "avg_protein": round(avg_protein, 1),
        "tips": tips if tips else ["🎉 Great week overall — keep it up!"],
    })


@app.route("/nutrition/log", methods=["POST"])
def nutrition_log():
    conn = get_db()
    uid = session.get("user_id")
    today = date.today().isoformat()
    food_id = request.form.get("food_id")
    meal_type = request.form.get("meal_type", "lunch")
    if not food_id:
        flash("Select a food first.", "warning")
        return redirect(url_for("nutrition"))
    food = conn.execute("SELECT * FROM food_database WHERE id = ?", (food_id,)).fetchone()
    if not food:
        flash("Food not found.", "warning")
        conn.close()
        return redirect(url_for("nutrition"))
    conn.execute(
        "INSERT INTO nutrition_log (user_id, date, meal_type, food_name, calories, protein_g, carbs_g, fat_g) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (uid, today, meal_type, food["name"], food["calories"], food["protein_g"], food["carbs_g"], food["fat_g"]),
    )
    conn.commit()
    conn.close()
    flash(f"Added {food['name']} to {meal_type}.", "success")
    return redirect(url_for("nutrition"))


@app.route("/nutrition/log-barcode", methods=["POST"])
def nutrition_log_barcode():
    """Log a scanned barcode product to nutrition_log."""
    conn = get_db()
    uid = get_user_id()
    if not uid:
        conn.close()
        return redirect(url_for("users"))
    today = date.today().isoformat()
    food_name = request.form.get("food_name", "Unknown")[:120]
    meal_type = request.form.get("meal_type", "snack").lower()
    try:
        calories = int(request.form.get("calories", 0))
    except (ValueError, TypeError):
        calories = 0
    try:
        protein_g = float(request.form.get("protein_g", 0))
    except (ValueError, TypeError):
        protein_g = 0.0
    try:
        carbs_g = float(request.form.get("carbs_g", 0))
    except (ValueError, TypeError):
        carbs_g = 0.0
    try:
        fat_g = float(request.form.get("fat_g", 0))
    except (ValueError, TypeError):
        fat_g = 0.0
    barcode = request.form.get("barcode", "")
    try:
        fiber_g = float(request.form.get("fiber_g", 0))
    except (TypeError, ValueError):
        fiber_g = 0.0
    try:
        servings = float(request.form.get("servings", 1))
    except (TypeError, ValueError):
        servings = 1.0
    conn.execute(
        "INSERT INTO nutrition_log (user_id, date, meal_type, food_name, calories, protein_g, carbs_g, fat_g, barcode, fiber_g, servings) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (uid, today, meal_type, food_name, calories, protein_g, carbs_g, fat_g, barcode, fiber_g, servings),
    )

    # Cache in barcode_cache if a barcode was provided and not already there
    if barcode:
        existing = conn.execute("SELECT id FROM barcode_cache WHERE barcode = ?", (barcode,)).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO barcode_cache (barcode, name, brand, category, calories, protein, carbs, fat, "
                "fiber, sugar, sodium, cholesterol, saturated_fat, serving_gram_weight, serving_description, "
                "data_quality, source, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (barcode, food_name, None, None, float(calories), protein_g, carbs_g, fat_g,
                 fiber_g, None, None, None, None, None, None, None, "user_entered", None),
            )

    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/lookup-barcode/<barcode>")
def api_lookup_barcode(barcode):
    """2-pass barcode lookup: local SQLite cache first, then ChowAPI as fallback."""
    import json as _json

    conn = get_db()

    # ── Pass 1: Check local cache ──
    cached = conn.execute(
        "SELECT * FROM barcode_cache WHERE barcode = ?", (barcode,)
    ).fetchone()

    if cached:
        conn.close()
        return _json.dumps({
            'success': True,
            'cached': True,
            'name': cached['name'],
            'brand': cached['brand'],
            'category': cached['category'],
            'calories': cached['calories'],
            'protein': cached['protein'],
            'carbs': cached['carbs'],
            'fat': cached['fat'],
            'fiber': cached['fiber'],
            'sugar': cached['sugar'],
            'sodium': cached['sodium'],
            'cholesterol': cached['cholesterol'],
            'saturated_fat': cached['saturated_fat'],
            'serving_gram_weight': cached['serving_gram_weight'],
            'serving_description': cached['serving_description'],
            'data_quality': cached['data_quality'],
            'source': cached['source'],
            'image_url': cached['image_url'],
        }), 200, {'Content-Type': 'application/json'}

    # ── Pass 2: Query ChowAPI ──
    import urllib.request, urllib.error
    url = f'https://api.chowapi.dev/v1/barcode/{barcode}'
    try:
        req = urllib.request.Request(url, headers={
            'Authorization': f'Bearer {CHOW_API_KEY}',
            'User-Agent': 'MaxiFitness/1.0'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        conn.close()
        if e.code == 404:
            return _json.dumps({'success': False, 'error': 'Product not found in database'}), 200, {'Content-Type': 'application/json'}
        return _json.dumps({'success': False, 'error': f'ChowAPI error: {e.code}'}), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        conn.close()
        return _json.dumps({'success': False, 'error': str(e)}), 200, {'Content-Type': 'application/json'}

    # Extract nutrients — prefer per_serving if available, else per_100g
    nutrients = data.get('nutrients', {})
    nutrients_per_serving = data.get('nutrients_per_serving', {})
    serving = data.get('serving', {})

    # Use per-serving if it has data, otherwise per-100g
    if nutrients_per_serving:
        n = nutrients_per_serving
    else:
        n = nutrients

    result = {
        'name': data.get('name', 'Unknown'),
        'brand': data.get('brand'),
        'category': data.get('category'),
        'calories': n.get('calories'),
        'protein': n.get('protein'),
        'carbs': n.get('carbs'),
        'fat': n.get('fat'),
        'fiber': n.get('fiber'),
        'sugar': n.get('sugar'),
        'sodium': n.get('sodium'),
        'cholesterol': n.get('cholesterol'),
        'saturated_fat': n.get('saturated_fat'),
        'serving_gram_weight': serving.get('gram_weight'),
        'serving_description': serving.get('description'),
        'data_quality': data.get('data_quality'),
        'image_url': data.get('image_url'),
        'source': data.get('source'),
    }

    # ── Cache in SQLite ──
    try:
        conn.execute(
            "INSERT INTO barcode_cache (barcode, name, brand, category, calories, protein, carbs, fat, "
            "fiber, sugar, sodium, cholesterol, saturated_fat, serving_gram_weight, serving_description, "
            "data_quality, source, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (barcode, result['name'], result['brand'], result['category'],
             result['calories'], result['protein'], result['carbs'], result['fat'],
             result['fiber'], result['sugar'], result['sodium'], result['cholesterol'],
             result['saturated_fat'], result['serving_gram_weight'], result['serving_description'],
             result['data_quality'], result['source'], result['image_url']),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Another request cached it first

    conn.close()

    return _json.dumps({'success': True, 'cached': False, **result}), 200, {'Content-Type': 'application/json'}

@app.route("/nutrition/delete/<int:id>", methods=["POST"])
def nutrition_delete(id):
    conn = get_db()
    uid = get_user_id()
    conn.execute("DELETE FROM nutrition_log WHERE id = ? AND user_id = ?", (id, uid))
    conn.commit()
    conn.close()
    if request.args.get("user_id"):
        return jsonify({"ok": True})
    return redirect(url_for("nutrition"))


@app.route("/nutrition/water", methods=["POST"])
def nutrition_water():
    conn = get_db()
    uid = get_user_id()
    today = date.today().isoformat()
    try:
        glasses = int(request.form.get("glasses", 0))
    except (TypeError, ValueError):
        glasses = 0
    conn.execute(
        "INSERT INTO daily_water (user_id, date, glasses) VALUES (?, ?, ?) ON CONFLICT(user_id, date) DO UPDATE SET glasses = ?",
        (uid, today, glasses, glasses),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "glasses": glasses})


@app.route("/nutrition/goal", methods=["POST"])
def nutrition_goal():
    conn = get_db()
    uid = get_user_id()
    if not uid:
        conn.close()
        return jsonify({"ok": False, "error": "No user"}), 401
    try:
        daily_goal = int(request.form.get("daily_goal", 1800))
    except (TypeError, ValueError):
        daily_goal = 1800
    try:
        water_glasses_goal = int(request.form.get("water_glasses_goal", 8))
    except (TypeError, ValueError):
        water_glasses_goal = 8
    try:
        protein_goal = float(request.form.get("protein_goal", 0))
    except (TypeError, ValueError):
        protein_goal = 0.0
    try:
        carbs_goal = float(request.form.get("carbs_goal", 0))
    except (TypeError, ValueError):
        carbs_goal = 0.0
    try:
        fat_goal = float(request.form.get("fat_goal", 0))
    except (TypeError, ValueError):
        fat_goal = 0.0
    diet_focus = request.form.get("diet_focus", "calorie")

    # Auto-fill defaults if any macro goal is 0
    daily = daily_goal or 2000
    defaults = {
        "calorie":  (daily * 0.3 / 4, daily * 0.45 / 4, daily * 0.25 / 9),  # 30%P 45%C 25%F
        "keto":     (daily * 0.3 / 4, daily * 0.05 / 4, daily * 0.65 / 9),   # 30%P 5%C 65%F
        "protein":  (daily * 0.4 / 4, daily * 0.35 / 4, daily * 0.25 / 9),   # 40%P 35%C 25%F
        "balanced": (daily * 0.3 / 4, daily * 0.45 / 4, daily * 0.25 / 9),   # 30%P 45%C 25%F
    }
    p, c, f = defaults.get(diet_focus, defaults["calorie"])
    if protein_goal == 0: protein_goal = round(p, 1)
    if carbs_goal == 0: carbs_goal = round(c, 1)
    if fat_goal == 0: fat_goal = round(f, 1)

    # Update calorie goals
    conn.execute(
        "INSERT INTO calorie_goals (user_id, daily_goal, water_glasses_goal, protein_goal, carbs_goal, fat_goal) "
        "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET "
        "daily_goal = ?, water_glasses_goal = ?, protein_goal = ?, carbs_goal = ?, fat_goal = ?",
        (uid, daily_goal, water_glasses_goal, protein_goal, carbs_goal, fat_goal,
         daily_goal, water_glasses_goal, protein_goal, carbs_goal, fat_goal),
    )

    # Update user diet_focus
    conn.execute("UPDATE users SET diet_focus = ? WHERE id = ?", (diet_focus, uid))
    conn.commit()
    conn.close()

    if request.args.get("user_id"):
        return jsonify({"ok": True})
    flash("Goals updated!", "success")
    return redirect(url_for("nutrition"))


@app.route("/plans")
def plans():
    conn = get_db()
    uid = session.get("user_id")

    plans_list = conn.execute("""
        SELECT wp.*,
               COALESCE(pa.is_active, 0) as is_assigned,
               pa.current_week,
               pa.start_date
        FROM workout_plans wp
        LEFT JOIN plan_assignments pa ON wp.id = pa.plan_id AND pa.user_id = ? AND pa.is_active = 1
        ORDER BY wp.is_template DESC, wp.frequency, wp.name
    """, (uid,)).fetchall()

    conn.close()
    return render_template("plans.html", plans=plans_list)


@app.route("/plans/<int:id>")
def plans_view(id):
    conn = get_db()
    uid = session.get("user_id")

    plan = conn.execute("SELECT * FROM workout_plans WHERE id=?", (id,)).fetchone()
    if not plan:
        conn.close()
        return redirect(url_for("plans"))
    plan = dict(plan)

    # Days grouped by week
    days_by_week = {}
    for row in conn.execute(
        "SELECT * FROM plan_days WHERE plan_id=? ORDER BY week_number, day_index", (id,)
    ):
        row = dict(row)
        wk = row["week_number"]
        if wk not in days_by_week:
            days_by_week[wk] = []
        if row["video_id"]:
            v = conn.execute("SELECT * FROM videos WHERE id=?", (row["video_id"],)).fetchone()
            row["video"] = dict(v) if v else None
        days_by_week[wk].append(row)
    plan["weeks"] = days_by_week

    # Assignment status
    assignment = conn.execute(
        "SELECT * FROM plan_assignments WHERE user_id=? AND plan_id=? AND is_active=1", (uid, id)
    ).fetchone()
    plan["assignment"] = dict(assignment) if assignment else None

    conn.close()
    return render_template("plans_view.html", plan=plan)


@app.route("/plans/<int:id>/assign", methods=["POST"])
def plans_assign(id):
    uid = session.get("user_id")
    conn = get_db()
    conn.execute("UPDATE plan_assignments SET is_active=0 WHERE user_id=? AND is_active=1", (uid,))
    existing = conn.execute(
        "SELECT * FROM plan_assignments WHERE user_id=? AND plan_id=?", (uid, id)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE plan_assignments SET is_active=1, current_week=1, start_date=? WHERE id=?",
            (date.today().isoformat(), existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO plan_assignments (user_id, plan_id, start_date, current_week, is_active) VALUES (?,?,?,?,1)",
            (uid, id, date.today().isoformat(), 1),
        )
    conn.commit()
    conn.close()
    flash("Plan assigned! Check your dashboard for today's workout.", "success")
    return redirect(url_for("dashboard"))


@app.route("/plans/<int:id>/advance", methods=["POST"])
def plans_advance(id):
    uid = session.get("user_id")
    conn = get_db()
    assignment = conn.execute(
        "SELECT * FROM plan_assignments WHERE user_id=? AND plan_id=? AND is_active=1", (uid, id)
    ).fetchone()
    if not assignment:
        flash("You're not currently assigned to this plan.", "error")
        conn.close()
        return redirect(url_for("plans_view", id=id))
    plan = conn.execute("SELECT weeks_count FROM workout_plans WHERE id=?", (id,)).fetchone()
    if assignment["current_week"] >= plan["weeks_count"]:
        flash("You've completed all weeks! Start over or pick a new plan.", "info")
        conn.close()
        return redirect(url_for("plans_view", id=id))
    conn.execute("UPDATE plan_assignments SET current_week = current_week + 1 WHERE id=?", (assignment["id"],))
    conn.commit()
    conn.close()
    flash(f"Advanced to Week {assignment['current_week'] + 1}!", "success")
    return redirect(url_for("plans_view", id=id))


@app.route("/plans/<int:id>/unassign", methods=["POST"])
def plans_unassign(id):
    uid = session.get("user_id")
    conn = get_db()
    conn.execute("UPDATE plan_assignments SET is_active=0 WHERE user_id=? AND plan_id=? AND is_active=1", (uid, id))
    conn.commit()
    conn.close()
    flash("Plan unassigned.", "info")
    return redirect(url_for("plans"))


@app.route("/plans/new", methods=["GET", "POST"])
def plans_new():
    uid = session.get("user_id")
    conn = get_db()
    user = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    prolapse_flagged = bool(user and user.get("prolapse_safe")) if user else False

    if request.method == "POST":
        import json
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        try:
            frequency = int(request.form.get("frequency", 3))
        except (TypeError, ValueError):
            frequency = 3
        try:
            weeks_count = int(request.form.get("weeks_count", 4))
        except (TypeError, ValueError):
            weeks_count = 4
        weeks_count = max(1, min(weeks_count, 8))
        schedule = json.loads(request.form.get("schedule", "[]"))

        if not name:
            flash("Plan name is required.", "warning")
            conn.close()
            videos = conn.execute("SELECT * FROM videos ORDER BY category, name").fetchall()
            return render_template("plans_new.html", videos=videos, prolapse_flagged=prolapse_flagged)

        pid = conn.execute(
            "INSERT INTO workout_plans (name, description, frequency, weeks_count, is_template, created_by) VALUES (?,?,?,?,0,?)",
            (name, description, frequency, weeks_count, uid),
        ).lastrowid

        for week_data in schedule:
            wk = week_data.get("week", 1)
            wo = 0
            for day_data in week_data.get("days", []):
                di = day_data["day"]
                is_rest = day_data.get("rest", False)
                vid = day_data.get("video_id")
                if is_rest:
                    conn.execute(
                        "INSERT INTO plan_days (plan_id, week_number, day_index, is_rest, order_within_week) VALUES (?,?,?,?,0)",
                        (pid, wk, di, 1),
                    )
                else:
                    wo += 1
                    v = conn.execute("SELECT name, duration_min FROM videos WHERE id=?", (vid,)).fetchone() if vid else None
                    conn.execute(
                        "INSERT INTO plan_days (plan_id, week_number, day_index, is_rest, video_id, workout_name, duration_min, order_within_week) VALUES (?,?,?,?,?,?,?,?)",
                        (pid, wk, di, 0, vid, v["name"] if v else None, v["duration_min"] if v else None, wo),
                    )
        conn.commit()
        conn.close()
        flash("Plan created!", "success")
        return redirect(url_for("plans_view", id=pid))

    videos = conn.execute("SELECT * FROM videos ORDER BY category, name").fetchall()
    if prolapse_flagged:
        videos = [v for v in videos if v["category"] in ("prolapse", "yoga")]
    conn.close()
    return render_template("plans_new.html", videos=videos, prolapse_flagged=prolapse_flagged)


@app.route("/api/today-workout")
def api_today_workout():
    uid = session.get("user_id")
    conn = get_db()
    assignment = conn.execute(
        "SELECT * FROM plan_assignments WHERE user_id=? AND is_active=1 ORDER BY created_at DESC LIMIT 1", (uid,)
    ).fetchone()
    if not assignment:
        conn.close()
        return jsonify(None)

    today = date.today()
    day_index = today.weekday()  # 0=Monday..6=Sunday
    plan_name = conn.execute("SELECT name FROM workout_plans WHERE id=?", (assignment["plan_id"],)).fetchone()["name"]

    day = conn.execute(
        "SELECT pd.*, v.name as video_name, v.duration_min as video_duration, v.intensity as video_intensity, v.url as video_url, v.category as video_category",
        " FROM plan_days pd LEFT JOIN videos v ON pd.video_id = v.id WHERE pd.plan_id=? AND pd.week_number=? AND pd.day_index=?",
        (assignment["plan_id"], assignment["current_week"], day_index),
    ).fetchone()
    conn.close()

    if not day or day["is_rest"]:
        return jsonify(None)

    return jsonify({
        "plan_name": plan_name,
        "week_number": assignment["current_week"],
        "day_name": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day_index],
        "is_rest": False,
        "workout_name": day["workout_name"] or day["video_name"],
        "duration_min": day["duration_min"] or day["video_duration"],
        "intensity": day["video_intensity"],
        "video_url": day["video_url"],
        "description": day.get("description"),
    })


REACTION_EMOJI = {"fire": "\U0001f525", "muscle": "\U0001f4aa", "heart": "\u2764\ufe0f", "star": "\u2b50", "wave": "\U0001f44b"}
REACTION_LABEL = {"fire": "That was intense!", "muscle": "Strong work!", "heart": "Proud of you", "star": "You crushed it", "wave": "Hey, saw this!"}
app.jinja_env.globals['reaction_emoji'] = REACTION_EMOJI.get
app.jinja_env.globals['reaction_label'] = REACTION_LABEL.get


def compute_goal_progress(conn, goal, uid_a, uid_b):
    gtype = goal["goal_type"]
    s, e = goal["start_date"], goal["end_date"]
    if gtype == "combined_workouts":
        return conn.execute("SELECT COUNT(*) FROM workouts WHERE user_id IN (?,?) AND date >= ? AND date <= ?", (uid_a, uid_b, s, e)).fetchone()[0]
    elif gtype == "combined_minutes":
        return conn.execute("SELECT COALESCE(SUM(duration_min),0) FROM workouts WHERE user_id IN (?,?) AND date >= ? AND date <= ?", (uid_a, uid_b, s, e)).fetchone()[0]
    elif gtype == "combined_days":
        return conn.execute("SELECT COUNT(DISTINCT date) FROM workouts WHERE user_id IN (?,?) AND date >= ? AND date <= ?", (uid_a, uid_b, s, e)).fetchone()[0]
    elif gtype == "combined_calories":
        return conn.execute("SELECT COALESCE(SUM(calories),0) FROM workouts WHERE user_id IN (?,?) AND date >= ? AND date <= ?", (uid_a, uid_b, s, e)).fetchone()[0]
    return 0


def _find_partner(conn, uid):
    return conn.execute(
        "SELECT pl.*, u2.id as partner_id, u2.name as partner_name "
        "FROM partner_links pl JOIN users u2 ON (pl.user_a_id = u2.id OR pl.user_b_id = u2.id) "
        "WHERE (pl.user_a_id = ? OR pl.user_b_id = ?) AND pl.status = 'active' AND u2.id != ? LIMIT 1",
        (uid, uid, uid)).fetchone()


def _get_weekly_stats(conn, uid_a, uid_b):
    mon, sun = get_week_range()
    my_week = conn.execute(
        "SELECT COUNT(*) as cnt, COALESCE(SUM(duration_min),0) as dur, COALESCE(SUM(calories),0) as cal "
        "FROM workouts WHERE user_id = ? AND date >= ? AND date <= ?",
        (uid_a, mon.isoformat(), sun.isoformat())).fetchone()
    partner_week = conn.execute(
        "SELECT COUNT(*) as cnt, COALESCE(SUM(duration_min),0) as dur, COALESCE(SUM(calories),0) as cal "
        "FROM workouts WHERE user_id = ? AND date >= ? AND date <= ?",
        (uid_b, mon.isoformat(), sun.isoformat())).fetchone()
    return my_week, partner_week


def _get_recent_workouts(conn, uid):
    rows = conn.execute(
        "SELECT w.*, u.name as user_name FROM workouts w JOIN users u ON w.user_id = u.id "
        "WHERE w.user_id = ? ORDER BY w.date DESC, w.id DESC LIMIT 10",
        (uid,)).fetchall()
    for w in rows:
        w["reactions"] = conn.execute(
            "SELECT r.reaction_type, u.name as reactor_name FROM reactions r "
            "JOIN users u ON r.user_id = u.id WHERE r.workout_id = ?",
            (w["id"],)).fetchall()
    return rows


def _get_active_goals(conn, link_id, uid_a, uid_b):
    goals = conn.execute(
        "SELECT * FROM joint_goals WHERE partner_link_id = ? AND status = 'active' "
        "ORDER BY end_date ASC", (link_id,)).fetchall()
    for g in goals:
        cv = compute_goal_progress(conn, g, uid_a, uid_b)
        g["current_value"] = cv
        g["percent"] = min(100, round((cv / g["target_value"]) * 100))
    return goals


def _days_since_last_workout(conn, uid):
    row = conn.execute(
        "SELECT date FROM workouts WHERE user_id = ? ORDER BY date DESC LIMIT 1",
        (uid,)).fetchone()
    if row is None:
        return None
    return (date.today() - date.fromisoformat(row["date"])).days


@app.route("/partner")
def partner_dashboard():
    uid = session.get("user_id")
    conn = get_db()
    partner = _find_partner(conn, uid)
    if not partner:
        conn.close()
        return render_template("partner.html", partner=None, REACTION_EMOJI=REACTION_EMOJI)
    partner = dict(partner)
    pid = partner["partner_id"]
    my_week, partner_week = _get_weekly_stats(conn, uid, pid)
    my_recent = _get_recent_workouts(conn, uid)
    partner_recent = _get_recent_workouts(conn, pid)
    active_goals = _get_active_goals(conn, partner["id"], uid, pid)
    partner_days_inactive = _days_since_last_workout(conn, pid)
    conn.close()
    return render_template("partner.html",
        partner=partner, my_week=my_week, partner_week=partner_week,
        my_recent=my_recent, partner_recent=partner_recent,
        active_goals=active_goals, partner_days_inactive=partner_days_inactive,
        today=date.today().isoformat(), REACTION_EMOJI=REACTION_EMOJI)


@app.route("/partner/link", methods=["POST"])
def partner_link():
    uid = session.get("user_id")
    pid = int(request.form["partner_id"])
    conn = get_db()
    if uid == pid:
        conn.close(); flash("You can't partner with yourself.", "error"); return redirect(url_for("partner_dashboard"))
    if not conn.execute("SELECT id FROM users WHERE id = ?", (pid,)).fetchone():
        conn.close(); flash("User doesn't exist.", "error"); return redirect(url_for("partner_dashboard"))
    if conn.execute("SELECT id FROM partner_links WHERE status = 'active' AND (user_a_id = ? OR user_b_id = ?)", (uid, pid)).fetchone():
        conn.close(); flash("Already in an active partnership.", "error"); return redirect(url_for("partner_dashboard"))
    a, b = sorted([uid, pid])
    conn.execute("INSERT INTO partner_links (user_a_id, user_b_id) VALUES (?, ?)", (a, b))
    conn.commit(); conn.close()
    flash("Partnership created!", "success")
    return redirect(url_for("partner_dashboard"))


@app.route("/partner/unlink", methods=["POST"])
def partner_unlink():
    uid = session.get("user_id")
    conn = get_db()
    link = conn.execute("SELECT id FROM partner_links WHERE status = 'active' AND (user_a_id = ? OR user_b_id = ?)", (uid, uid)).fetchone()
    if link:
        action = request.form.get("action", "end")
        conn.execute("UPDATE partner_links SET status = ? WHERE id = ?", ("paused" if action == "pause" else "ended", link["id"]))
        conn.commit()
        flash("Partnership " + ("paused" if action == "pause" else "ended") + ".", "info")
    conn.close()
    return redirect(url_for("partner_dashboard"))


@app.route("/api/partner/reaction", methods=["POST"])
def api_partner_reaction():
    uid = session.get("user_id")
    data = request.get_json()
    wid, rt = data.get("workout_id"), data.get("reaction_type")
    if not wid or not rt:
        return jsonify({"error": "workout_id and reaction_type required"}), 400
    conn = get_db()
    w = conn.execute("SELECT user_id FROM workouts WHERE id = ?", (wid,)).fetchone()
    if not w:
        conn.close(); return jsonify({"error": "Workout not found"}), 404
    pl = conn.execute("SELECT pl.id FROM partner_links pl WHERE pl.status = 'active' AND (pl.user_a_id = ? OR pl.user_b_id = ?) AND (pl.user_a_id = ? OR pl.user_b_id = ?)", (uid, uid, w["user_id"], w["user_id"])).fetchone()
    if not pl:
        conn.close(); return jsonify({"error": "Can only react to partner workouts"}), 403
    ex = conn.execute("SELECT id FROM reactions WHERE workout_id = ? AND user_id = ? AND reaction_type = ?", (wid, uid, rt)).fetchone()
    if ex:
        conn.execute("DELETE FROM reactions WHERE id = ?", (ex["id"],)); action = "removed"
    else:
        conn.execute("INSERT INTO reactions (workout_id, user_id, reaction_type) VALUES (?, ?, ?)", (wid, uid, rt)); action = "added"
    conn.commit()
    reactions = conn.execute("SELECT r.reaction_type, u.name as reactor_name FROM reactions r JOIN users u ON r.user_id = u.id WHERE r.workout_id = ?", (wid,)).fetchall()
    conn.close()
    return jsonify({"action": action, "reactions": [dict(r) for r in reactions]})


@app.route("/partner/goals")
def partner_goals():
    uid = session.get("user_id")
    conn = get_db()
    partner = conn.execute(
        "SELECT pl.*, u2.id as partner_id FROM partner_links pl JOIN users u2 ON (pl.user_a_id = u2.id OR pl.user_b_id = u2.id) "
        "WHERE (pl.user_a_id = ? OR pl.user_b_id = ?) AND pl.status = 'active' AND u2.id != ? LIMIT 1",
        (uid, uid, uid)).fetchone()
    if not partner:
        conn.close()
        return render_template("partner_goals.html", partner=None, goals=[])
    partner = dict(partner)
    pid = partner["partner_id"]
    goals = conn.execute("SELECT * FROM joint_goals WHERE partner_link_id = ? ORDER BY end_date DESC", (partner["id"],)).fetchall()
    for g in goals:
        g = dict(g)
        g["current_value"] = compute_goal_progress(conn, g, uid, pid)
        g["percent"] = min(100, round((g["current_value"] / g["target_value"]) * 100))
        if g["status"] == "active" and date.today() > date.fromisoformat(g["end_date"]):
            conn.execute("UPDATE joint_goals SET status = 'expired' WHERE id = ?", (g["id"],)); conn.commit(); g["status"] = "expired"
        elif g["status"] == "active" and g["current_value"] >= g["target_value"]:
            conn.execute("UPDATE joint_goals SET status = 'completed' WHERE id = ?", (g["id"],)); conn.commit(); g["status"] = "completed"
    conn.close()
    return render_template("partner_goals.html", partner=partner, goals=goals, today=date.today().isoformat())


@app.route("/api/partner/goals", methods=["POST"])
def api_partner_goal_create():
    uid = session.get("user_id")
    data = request.get_json()
    conn = get_db()
    pl = conn.execute("SELECT pl.id FROM partner_links pl WHERE pl.status = 'active' AND (pl.user_a_id = ? OR pl.user_b_id = ?)", (uid, uid)).fetchone()
    if not pl:
        conn.close(); return jsonify({"error": "No active partnership"}), 400
    conn.execute("INSERT INTO joint_goals (partner_link_id, name, description, goal_type, target_value, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (pl["id"], data["name"], data.get("description", ""), data["goal_type"], data["target_value"], data["start_date"], data["end_date"]))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


@app.route("/api/partner/goals/<int:id>/delete", methods=["POST"])
def api_partner_goal_delete(id):
    uid = session.get("user_id")
    conn = get_db()
    g = conn.execute("SELECT jg.* FROM joint_goals jg JOIN partner_links pl ON jg.partner_link_id = pl.id WHERE jg.id = ? AND (pl.user_a_id = ? OR pl.user_b_id = ?)", (id, uid, uid)).fetchone()
    if not g:
        conn.close(); return jsonify({"error": "Goal not found"}), 404
    conn.execute("DELETE FROM joint_goals WHERE id = ?", (id,)); conn.commit(); conn.close()
    return jsonify({"ok": True})



# ─── Plan 5: Progress Photos & Wellness ──────────────────────────────────────


def compress_photo(input_stream, max_edge, quality):
    """Read image from BytesIO, resize if needed, return JPEG bytes."""
    img = Image.open(input_stream)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if max(img.size) > max_edge:
        ratio = max_edge / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    out.seek(0)
    return out.getvalue()


def _delete_photo_files(file_path, thumb_path):
    """Delete photo files from disk."""
    for path in [file_path, thumb_path]:
        full = os.path.join(app.root_path, path)
        if os.path.exists(full):
            os.remove(full)


def _dir_size(path):
    """Return total size of all files in a directory in bytes."""
    total = 0
    if os.path.exists(path):
        for f in os.scandir(path):
            if f.is_file():
                total += f.stat().st_size
    return total


@app.route("/progress/photos/upload", methods=["POST"])
def upload_photo():
    conn = get_db()
    uid = session.get("user_id")

    photo = request.files.get("photo")
    date_str = request.form.get("date", date.today().isoformat())
    angle = request.form.get("angle", "front")
    notes = request.form.get("notes", "")

    if not photo or photo.filename == "":
        flash("No photo selected.", "error")
        conn.close()
        return redirect(url_for("progress"))

    if angle not in ("front", "side", "back"):
        flash("Invalid photo angle.", "error")
        conn.close()
        return redirect(url_for("progress"))

    allowed = {"image/jpeg", "image/png", "image/webp"}
    if photo.content_type not in allowed:
        flash("Unsupported file type. Use JPEG, PNG, or WebP.", "error")
        conn.close()
        return redirect(url_for("progress"))

    user_dir = os.path.join(app.config["PHOTO_UPLOAD_DIR"], f"user_{uid}")
    os.makedirs(user_dir, exist_ok=True)

    count = conn.execute(
        "SELECT COUNT(*) FROM progress_photos WHERE user_id = ?", (uid,)
    ).fetchone()[0]
    if count >= app.config["PHOTO_PER_USER_LIMIT"]:
        oldest = conn.execute(
            "SELECT * FROM progress_photos WHERE user_id = ? ORDER BY created_at ASC LIMIT 1",
            (uid,),
        ).fetchone()
        if oldest:
            _delete_photo_files(oldest["file_path"], oldest["thumbnail_path"])
            conn.execute("DELETE FROM progress_photos WHERE id = ?", (oldest["id"],))

    dir_bytes = _dir_size(user_dir)
    if dir_bytes > app.config["PHOTO_PER_USER_BYTES"]:
        flash("Storage limit reached. Delete some photos first.", "error")
        conn.close()
        return redirect(url_for("progress"))

    thumb_bytes = compress_photo(photo, app.config["PHOTO_THUMB_MAX_EDGE"], app.config["PHOTO_QUALITY"])
    photo.seek(0)
    orig_bytes = compress_photo(photo, app.config["PHOTO_ORIGINAL_MAX_EDGE"], app.config["PHOTO_QUALITY"])

    filename = f"{date_str}_{angle}.jpg"
    thumb_filename = f"{date_str}_{angle}_thumb.jpg"
    file_path = os.path.join("static", "photos", f"user_{uid}", filename)
    thumb_path = os.path.join("static", "photos", f"user_{uid}", thumb_filename)

    with open(os.path.join(app.root_path, file_path), "wb") as f:
        f.write(orig_bytes)
    with open(os.path.join(app.root_path, thumb_path), "wb") as f:
        f.write(thumb_bytes)

    conn.execute(
        "INSERT INTO progress_photos (user_id, date, angle, file_path, thumbnail_path, notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (uid, date_str, angle, file_path, thumb_path, notes),
    )
    conn.commit()
    conn.close()

    flash("Photo saved!", "success")
    return redirect(url_for("progress"))


@app.route("/progress/photos/<int:id>/delete", methods=["POST"])
def delete_photo(id):
    conn = get_db()
    uid = session.get("user_id")

    photo = conn.execute(
        "SELECT * FROM progress_photos WHERE id = ? AND user_id = ?", (id, uid)
    ).fetchone()

    if not photo:
        flash("Photo not found.", "error")
        conn.close()
        return redirect(url_for("progress"))

    _delete_photo_files(photo["file_path"], photo["thumbnail_path"])
    conn.execute("DELETE FROM progress_photos WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("Photo deleted.", "success")
    return redirect(url_for("progress"))


@app.route("/progress/wellness", methods=["POST"])
def log_wellness():
    conn = get_db()
    uid = session.get("user_id")

    m = request.form
    date_str = m.get("date", date.today().isoformat())

    def clamp_int(val, lo, hi):
        if not val:
            return None
        v = int(val)
        return max(lo, min(hi, v))

    conn.execute(
        "INSERT OR REPLACE INTO wellness_log "
        "(user_id, date, energy, mood, sleep, clothing_fit, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            uid,
            date_str,
            clamp_int(m.get("energy"), 1, 5),
            clamp_int(m.get("mood"), 1, 5),
            clamp_int(m.get("sleep"), 1, 5),
            m.get("clothing_fit") if m.get("clothing_fit") in ("tight", "fitting", "loose", "very_loose") else None,
            m.get("notes", ""),
        ),
    )
    conn.commit()
    conn.close()

    flash("Wellness log saved!", "success")
    return redirect(url_for("progress"))


@app.route("/api/photos/<int:user_id>")
def api_photos(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, date, angle, file_path, thumbnail_path, notes "
        "FROM progress_photos WHERE user_id = ? ORDER BY date ASC, angle ASC",
        (user_id,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/wellness/<int:user_id>")
def api_wellness(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM wellness_log WHERE user_id = ? ORDER BY date ASC",
        (user_id,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/dismiss-feature/<slug>", methods=["POST"])
def dismiss_feature(slug):
    if 'seen_features' not in session:
        session['seen_features'] = []
    if slug not in session['seen_features']:
        session['seen_features'].append(slug)
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)




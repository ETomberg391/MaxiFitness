"""SQLite database initialization and helpers."""

import sqlite3
import os
from datetime import date, datetime

DB_PATH = os.environ.get("MAXIFITNESS_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "maxifitness.db"))


def get_db():
    """Return a DB connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def bmi(weight_lbs, height_ft, height_in):
    """Calculate BMI from weight in lbs and height in ft/in."""
    if not weight_lbs or not height_ft and not height_in:
        return None
    inches = height_ft * 12 + height_in
    if inches <= 0:
        return None
    return round((weight_lbs / (inches ** 2)) * 703, 1)


def init_db():
    """Create tables if they don't exist and seed reference data."""
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        weight_lbs REAL,
        height_ft INTEGER,
        height_in INTEGER,
        bmi REAL,
        start_date TEXT,
        favorite_routine_id INTEGER REFERENCES routines(id),
        favorite_video_id INTEGER REFERENCES videos(id),
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        start_weight REAL,
        goal_weight REAL,
        unit TEXT DEFAULT 'lbs' CHECK (unit IN ('lbs', 'kg')),
        start_date TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        duration_min INTEGER NOT NULL,
        calories INTEGER,
        heart_rate_avg INTEGER,
        heart_rate_max INTEGER,
        workout_type TEXT DEFAULT 'steady',
        intensity TEXT DEFAULT 'moderate',
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS daily_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        weight REAL,
        waist REAL,
        hips REAL,
        chest REAL,
        left_arm REAL,
        right_arm REAL,
        left_thigh REAL,
        right_thigh REAL,
        resting_hr INTEGER,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, date)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        coach TEXT,
        duration_min INTEGER NOT NULL,
        url TEXT NOT NULL,
        category TEXT DEFAULT '10min',
        intensity TEXT DEFAULT 'moderate',
        description TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS routines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'hiit',
        description TEXT,
        structure TEXT NOT NULL,
        total_min INTEGER,
        difficulty TEXT DEFAULT 'beginner'
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS schedule_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase_name TEXT NOT NULL,
        week_start INTEGER NOT NULL,
        week_end INTEGER NOT NULL,
        description TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS schedule_days (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL REFERENCES schedule_plans(id) ON DELETE CASCADE,
        day_name TEXT NOT NULL,
        workout_name TEXT,
        duration_min INTEGER,
        video_url TEXT,
        description TEXT,
        is_rest INTEGER DEFAULT 0
    )
    """)

    # Seed videos
    videos = [
        ("New Heights", "Coach Jamie", 10, "https://www.youtube.com/watch?v=A2tFT4la0DU", "10min", "moderate",
         "Warm-up, sprints, active recovery, reaches, and intervals."),
        ("Rise & Climb", "Coach Jamie", 10, "https://www.youtube.com/watch?v=W9G0SlxNl2M", "10min", "beginner",
         "Beginner intervals: warm-up, sprints, active recovery, squats, cool-down."),
        ("Tabata + Lower Body Sculpt", "Coach Jessi", 10, "https://www.youtube.com/watch?v=hExoNY0m7pk", "10min", "moderate",
         "Warm-up, alternating long and short strides, cool-down."),
        ("Tabata + Full-Body", "Coach Adriana", 10, "https://www.youtube.com/watch?v=0DtMo88dOCk", "10min", "moderate",
         "1-min warm-up, sprints, strides, climbing squats, cool-down."),
        ("Full-Body Blaster", "Coach Adriana", 20, "https://www.youtube.com/watch?v=TvkOIcNtWso", "20min", "high",
         "Warm-up, climbing squats, reverse grips, sprints, active recovery, crunches."),
        ("Full-Body HIIT (Jessi)", "Coach Jessi", 20, "https://www.youtube.com/watch?v=bzoIJ48WLxY", "20min", "high",
         "Warm-up, long strides, short strides, oblique crunches."),
        ("Full-Body HIIT (GC)", "Coach GC", 20, "https://www.youtube.com/watch?v=CudrTd6IiJc", "20min", "high",
         "Warm-up, sprints, active recovery, alternating long and short strides."),
        ("Tabata + Lower Body", "Coach GC", 11, "https://www.youtube.com/watch?v=6_fPdnsOM9s", "10min", "moderate",
         "Tabata intervals focused on lower body — glutes, quads, hamstrings."),
        ("Upper Body HIIT", "Coach Jamie", 21, "https://www.youtube.com/watch?v=iv-J8ONUoIU", "20min", "high",
         "Upper body HIIT — reverse grips, arm targets, climbing intervals."),
        ("Tabata + Lower Body Burner", "Coach Jamie", 11, "https://www.youtube.com/watch?v=BVxsLjxh54M", "10min", "moderate",
         "Tabata format with lower body focus — alternating stride lengths, glute activation."),
        ("Upper Body HIIT (v2)", "Coach Jamie", 21, "https://www.youtube.com/watch?v=wfR9xkM6IRM", "20min", "high",
         "Second take of upper body HIIT — similar structure with slight variation."),
        ("10 Min Upper Body Workout", "Coach GC", 11, "https://www.youtube.com/watch?v=_3rkxuKLq58", "10min", "moderate",
         "Targeted upper body — shoulders, arms, chest engagement on the climber."),
        ("10 Min Lower Body Workout", "Coach Jessi", 11, "https://www.youtube.com/watch?v=V3urc32J3PU", "10min", "moderate",
         "Lower body sculpting — quads, glutes, hamstrings with Jessi's coaching style."),
        ("Arms", "Coach Jamie", 11, "https://www.youtube.com/watch?v=Btctq0BfwTk", "10min", "moderate",
         "Arm-focused workout — triceps, biceps, core engagement."),
        ("Lower Body", "Coach Jamie", 11, "https://www.youtube.com/watch?v=PkSqolEGRUc", "10min", "beginner",
         "Full lower body — quads, hamstrings, glutes; highest viewed MaxiClimber video."),
        ("10 Min Dumbbell Chest Workout", "Tom Peto Training", 10, "https://www.youtube.com/watch?v=dqeftPf4f04", "dumbbell", "moderate",
         "Incline/flat press, push-ups, flyes — chest-focused with dumbbells."),
        ("10 Mins INTENSE Chest Workout", "Chloe Ting", 10, "https://www.youtube.com/watch?v=a9vL6BsgkPg", "dumbbell", "moderate",
         "Standing press, upward fly, reverse grip press, chest fly, pullover, push-ups, planks."),
        ("10 Min Dumbbell Upper Body", "Caroline Girvan", 14, "https://www.youtube.com/watch?v=Mx9RrNZv2TI", "dumbbell", "moderate",
         "Rows, chest press, flyes, pullovers, overhead press, curls — full upper body."),
        ("10 Min Upper Body Dumbbell Follow Along", "Tom Peto Training", 11, "https://www.youtube.com/watch?v=nBwV7S45OvE", "dumbbell", "moderate",
         "Bent over row, bench/floor press, crush grip curls, overhead press, pullover."),
        ("20 Min Chest and Back with Dumbbells", "Tom Peto Training", 19, "https://www.youtube.com/watch?v=OsO8WVO0mBQ", "dumbbell", "high",
         "Incline press + prone row supersets, 1.5 press + pullover, incline fly + wide row."),
        ("20 Min Upper Body Dumbbell Workout", "ACHV PEAK", 25, "https://www.youtube.com/watch?v=v2vLQiU8lJQ", "dumbbell", "moderate",
         "Curls, shoulder press, tricep extension, rows, flyes, shoulder matrix, pullovers."),
        ("20 Min Home Upper Body Workout", "FitnessBlender", 20, "https://www.youtube.com/watch?v=ptQXsJfgPAY", "dumbbell", "beginner",
         "Push-ups, reverse fly, overhead press, pullover, tricep extension, bicep curls."),
        ("10 Min Dumbbell Strength Workout", "Sunny Health & Fitness", 11, "https://www.youtube.com/watch?v=kk1rnldcPPE", "dumbbell", "beginner",
         "Squats, overhead press, bent-over row, lunges, curls, chest fly, skull crushers."),
        ("10-Minute Yoga For Beginners", "Yoga With Adriene", 12, "https://www.youtube.com/watch?v=j7rKKpwdXNE", "yoga", "beginner",
         "Basic poses, breath awareness, seated stretches, cat-cow, low lunge, child's pose."),
        ("10-Minute Morning Yoga", "Yoga With Adriene", 11, "https://www.youtube.com/watch?v=klmBssEYkdU", "yoga", "beginner",
         "Cat-cow, downward dog, three-legged dog with hip opener, seated meditation."),
        ("10 min Morning Yoga Full Body Stretch", "Yoga with Kassandra", 11, "https://www.youtube.com/watch?v=4pKly2JojMw", "yoga", "beginner",
         "Neck release, cat-cow, thread the needle, lizard pose, downward dog, ragdoll, malasana, sphinx, child's pose."),
        ("10 min Morning Yoga Stretch – Day #1", "Yoga with Kassandra", 14, "https://www.youtube.com/watch?v=JyaM87ecKd0", "yoga", "beginner",
         "Day 1 of 30-day challenge — child's pose, cat-cow, core work, modified side plank, downward dog, high lunge, standing pigeon, chair pose, seated twists."),
        ("10 min Yoga for Beginners – Gentle", "Yoga with Kassandra", 12, "https://www.youtube.com/watch?v=5s978KzFvOg", "yoga", "beginner",
         "All poses seated or reclined — twists, side bends, cat-cow, downward dog, sphinx, child's pose."),
        ("Yoga For Complete Beginners", "Yoga With Adriene", 24, "https://www.youtube.com/watch?v=v7AYKMP6rOE", "yoga", "beginner",
         "Seated stretches, twists, side body, cat-cow, heart-to-earth, downward dog, forward fold, mountain pose, warrior I/II."),
        ("20-Minute Yoga For Beginners", "Yoga With Adriene", 22, "https://www.youtube.com/watch?v=vNyJuQuuMC8", "yoga", "beginner",
         "Breath-focused — spine, hips, shoulders, core, hamstrings, wrists, ankles, knees."),
        ("Morning Yoga for Beginners", "Yoga With Adriene", 22, "https://www.youtube.com/watch?v=GnHTeHAZQhM", "yoga", "beginner",
         "Neck rolls, foot/wrist awareness, knee-to-chest hugs, butterfly, cat-cow circles, downward dog, forward fold, seated stretches."),
        ("10 Min Morning Yoga Flow", "Boho Beautiful Yoga", 14, "https://www.youtube.com/watch?v=uQ2yJhF4zZY", "yoga", "beginner",
         "Seated side stretches, supine spinal twists, happy baby, child's pose, downward dog, ragdoll, forward fold, sun salutations."),
        ("20 min Morning Yoga for Flexibility", "Yoga with Kassandra", 21, "https://www.youtube.com/watch?v=59Yd_i-D-w0", "yoga", "moderate",
         "Deep stretch — laying chest openers, sphinx, cobra, tiger pose, low lunge twists, warrior II, triangle, lizard pose, reclined pigeon, figure-four."),
        ("10 Min Back & Bicep", "HASfit", 11, "https://www.youtube.com/watch?v=NxFMvQCnfEw", "back_biceps", "moderate",
         "High plank row, curl & run, high pull, hammer curl, row/fly — 5 exercises × 4 rounds."),
        ("20 Min Back & Biceps", "Midas Movement", 21, "https://www.youtube.com/watch?v=__ACpp9tQnI", "back_biceps", "moderate",
         "20 unique exercises, 30s on/30s off — side rows, curl negatives, rear fly, paddle rows, RDL+pronated row, twisting curls."),
        ("20 Min Back & Biceps", "Caroline Girvan", 23, "https://www.youtube.com/watch?v=tf685ggJv9k", "back_biceps", "high",
         "Single arm row, renegade row, pullovers, supine row, preacher curls — 5 exercises × 3 rounds."),
        ("10 Min Standing Arms + Back", "Eleni Fit", 10, "https://www.youtube.com/watch?v=ZdkaEQBSl-8", "back_biceps", "moderate",
         "Standing format, 30s on, no rest — back and bicep targets with no setup needed."),
        ("20 Min Superset Back", "Caroline Girvan", 26, "https://www.youtube.com/watch?v=kO_b0D8P1Jg", "back_biceps", "high",
         "45s supersets — bent over row/renegade row, rotating renegade/landmine row, single arm renegade/single arm row, pullover finisher."),
        ("30 Min Back & Bicep", "Tom Peto Training", 30, "https://www.youtube.com/watch?v=IqFh7LY8uMU", "back_biceps", "high",
         "Heavy section (single arm row, crusher curl, shrugs) + light section (high pull upright row, supinated curl, reverse grip row, 1.5 hammer curl)."),
        ("15 Min Chest & Triceps", "TIFF x DAN", 19, "https://www.youtube.com/watch?v=yki76xhcuKU", "chest_tricep", "moderate",
         "6 circuits of 3 exercises — DB chest press, push-ups, chest flyes, wide/diamond push-ups, tricep extensions."),
        ("15 Min Chest & Tricep", "HOME WORKOUT STUDIO", 18, "https://www.youtube.com/watch?v=YaNuacSY3Bs", "chest_tricep", "moderate",
         "5 exercises × 3 rounds — DB press w/ rotation, push-ups, DB flys, wide grip push-ups, diamond push-ups."),
        ("30 Min Chest & Tricep", "TIFF x DAN", 35, "https://www.youtube.com/watch?v=hkeLoBUbY00", "chest_tricep", "high",
         "6 exercises × 3 sets (40s/30s/20s work) — high volume chest and tricep pairing."),
        ("22 Min Legs & Shoulders", "ACHV PEAK", 22, "https://www.youtube.com/watch?v=erSkH_1BY68", "shoulder_legs", "high",
         "12 exercises in supersets (2 sets each, 30s on / 15s off) — static lunges, hex squats, RDLs, sumo squats, front squats, deadlifts, shoulder press, reverse flyes, Arnold presses, lateral raises, shoulder matrix."),
        ("20 Min Full Body Strength", "nourishmovelove", 24, "https://www.youtube.com/watch?v=q1wFPBY6IYI", "shoulder_legs", "moderate",
         "Circuit 1: legs & shoulders (squats, split lunges, single-arm shoulder press). Circuits 2-3 add back, chest, biceps, triceps. 40s work / 20s rest, no repeats."),
        ("20 Min Full Body Dumbbell", "Zeus Fitness", 25, "https://www.youtube.com/watch?v=VQZJlSAuOTc", "shoulder_legs", "moderate",
         "6 exercises × 3 laps (10 → 15 → 20 reps) — goblet squats, kib presses (shoulder press + upright row), alternating lunges, double arm extensions, step-leg deadlifts, isometric hold + bicep curl."),
        ("35 Min Leg and Shoulder EMOM", "nourishmovelove", 40, "https://www.youtube.com/watch?v=I7LTmg1naO0", "shoulder_legs", "high",
         "4 circuits of 3 exercises in EMOM format — alternating squat thrusters, push press, squat transition press, overhead lunges, 45° presses, staggered deadlift to snatch, lateral lunges, front/lateral raises, halo lateral lunges."),
        ("25 Min Strength Supersets", "Heather Robertson", 30, "https://www.youtube.com/watch?v=9ug_SiqKaiY", "shoulder_legs", "moderate",
         "4 supersets × 3 rounds, 40s work / 20s rest — sumo squat + front squat, chest press + skull crusher, additional upper/lower body combos."),
        ("30 Min Chest & Tricep", "Tom Peto Training", 31, "https://www.youtube.com/watch?v=Y96AYpbJl74", "chest_tricep", "high",
         "Incline press, pullover, flat press, crusher press, fly, skull crusher, push-ups, overhead extension — 40s on / 20s off, 3 rounds."),
        ("15 Min Back & Biceps", "Kaleigh Cohen Strength", 17, "https://www.youtube.com/watch?v=oC6sKQHMSyA", "back_biceps", "moderate",
         "No-repeat format, 45s work/15s rest — alternating curls, wide curls, concentration curls, hammer curls, hammer pulses, alternating rows, wide rows, single arm rows, reverse grip rows."),
        ("11 Min Back and Biceps", "Jessica Valant", 11, "https://www.youtube.com/watch?v=8kVCOb41Lgk", "back_biceps", "beginner",
         "Beginner-friendly, standing format — bicep curls, single-arm rows, twisting bicep curls, double-arm rear fly rows, hammer curls with twist."),
        ("20 Min Back and Bicep", "TIFF x DAN", 21, "https://www.youtube.com/watch?v=DT4QjwTaf5Q", "back_biceps", "high",
         "40s work/20s rest — bent over single arm rows, crusher curls, shrugs/RDLs, upright rows, bicep curls, reverse grip rows, 1.5 hammer curls."),
        ("15 Min Chest and Triceps", "HASfit", 24, "https://www.youtube.com/watch?v=T6MCCmD5l-g", "chest_tricep", "moderate",
         "Superset-based — underhand chest press, overhead tricep extension, 1-and-a-quarter push-ups, manual tricep extension, dumbbell chest fly, elbow-out extension, burnout round."),
        ("20 Min Chest and Triceps", "HASfit", 28, "https://www.youtube.com/watch?v=Hku6TXi0j1s", "chest_tricep", "moderate",
         "Extended superset version with burnout round — underhand chest press, overhead tricep extension, 1-and-a-quarter push-ups, manual tricep extension, chest fly, elbow-out extension."),
        ("15 Min Chest & Tricep", "Kaleigh Cohen Strength", 17, "https://www.youtube.com/watch?v=K_zjIyt0ZNk", "chest_tricep", "moderate",
         "No-repeat format, 45s work/15s rest — single-arm overhead tricep extension, tricep kickbacks, push-ups, chest press, alternating chest press, pullover, chest fly, tricep push-ups, close-grip press."),
        ("15 Min Chest & Triceps", "Buff Dudes Workouts", 15, "https://www.youtube.com/watch?v=mwk16rZj1Zc", "chest_tricep", "high",
         "Twisting bench press, incline close press, single-arm floor press, underhand dumbbell flyes, twisting skull crushers, tricep kickbacks, ab rollouts."),
        ("30 Min Chest & Triceps", "Midas Movement", 31, "https://www.youtube.com/watch?v=EXfKqlgYnF4", "chest_tricep", "high",
         "No bench needed — DB floor press, floor fly, floor hex press, single Tate press, twist floor press, lying skullcrusher."),
        ("22 Min Shoulder and Legs", "Coco Fitness", 22, "https://www.youtube.com/watch?v=JJj4ImppQ9A", "shoulder_legs", "moderate",
         "Arnold Press, DB Upright Row, Lateral Raise (shoulders) + Static Lunges, Squat Narrow to Normal, Hip Thrusters, Single Leg Hip Thrusters (legs)."),
        ("10 Min Shoulder Workout", "HASfit", 11, "https://www.youtube.com/watch?v=0ObXy_hq3Xs", "shoulder_legs", "moderate",
         "Superset format — Arnold Press + Iso 90 Shoulder Press Hold, Side Raise with Pulse + Kneeling Reverse Shoulder Extension. Two rounds."),
        ("20 Min 3D Shoulders", "Midas Movement", 24, "https://www.youtube.com/watch?v=8e9qInG3h3s", "shoulder_legs", "moderate",
         "Double Front Raises, Leaning Rear Delt Flys, Push Press, Lateral Raises, Leaning Rear Flys, Side Raises, Double Twisting Front Raises, Leaning High Rows, Arnold Press, Alt Front Raises + Hold. Two rounds."),
        ("20 Min Dumbbell Legs", "Midas Movement", 24, "https://www.youtube.com/watch?v=x5PAjQrG_UM", "shoulder_legs", "moderate",
         "3 rounds of 6 exercises — Goblet Squats, Romanian Deadlifts, Bulgarian Split Squats, Side to Side Lunges, Calf Raises, Briefcase Squats."),
        ("20 Min Dumbbell Leg Workout", "nourishmovelove", 23, "https://www.youtube.com/watch?v=2crbEzncCCo", "shoulder_legs", "moderate",
         "5 superset circuits — Squats + Goblet Squat Jack, Split Lunge + Explosive Lunge, Staggered Deadlift + Snatch, Lateral Lunge + Skaters, Wide Squat + Squat Jack."),
        ("15 Min Chest and Triceps", "HASfit", 24, "https://www.youtube.com/watch?v=0X0zflk9BqA", "chest_tricep", "moderate",
         "4 supersets — underhand chest press + overhead tricep extension, 1&1/4 push-ups + manual tricep extension, chest fly + elbow out extension."),
        ("30 Min Chest & Tricep", "Midas Movement", 31, "https://www.youtube.com/watch?v=Jd7mX0BfY2o", "chest_tricep", "high",
         "No bench needed — floor press, floor fly, hex press, single Tate press, twist floor press, lying skullcrusher."),
        ("15 Min Chest & Tricep", "Chris Heria", 15, "https://www.youtube.com/watch?v=7YiY0x6bFjU", "chest_tricep", "high",
         "Time-based format — chest press variations, incline press, tricep extensions, push-up variations, chest flyes, tricep kickbacks."),
        ("10 Min Chest and Triceps", "Fitness Blender", 10, "https://www.youtube.com/watch?v=9b2JQx0VJcA", "chest_tricep", "moderate",
         "3-block format with decreasing time windows — chest press, skull crushers, close-grip push-ups, chest fly, floor press, overhead triceps extension, crush press, single-arm kickbacks, standard push-ups."),
        ("15 Minute Prolapse Safe Workout", "Jessica Valant", 15, "https://www.youtube.com/watch?v=-1Cd-lzlb00", "prolapse", "beginner",
         "15-minute full body workout specifically designed to be safe for pelvic organ prolapse."),
        ("20 Min Prolapse Safe Full Body", "Jessica Valant", 20, "https://www.youtube.com/watch?v=VBvXdAGyFQw", "prolapse", "beginner",
         "20-minute full body workout safe for prolapse — gentle strength and movement."),
        ("Seated Chair Core & Pelvic Floor", "Dr. Bri's Vibrant Pelvic Health", 15, "https://www.youtube.com/watch?v=5T2-0JZhcqw", "prolapse", "beginner",
         "Seated chair workout for core and pelvic floor strength — no standing required, ideal for bad feet."),
        ("5 Simple Pelvic Support Exercises", "Dr. Bri's Vibrant Pelvic Health", 10, "https://www.youtube.com/watch?v=RDdp0bP7x2Q", "prolapse", "beginner",
         "5 simple at-home exercises for immediate pelvic support — follow-along format."),
        ("Best Exercises for Prolapse & Bladder Leaks", "Dr. Bri's Vibrant Pelvic Health", 15, "https://www.youtube.com/watch?v=QyYOdUGokpY", "prolapse", "beginner",
         "Safely strengthen your pelvic floor — exercises for prolapse and bladder leaks."),
        ("8-Minute Pelvic Prolapse Workout", "Dr. Kristie Ennis", 8, "https://www.youtube.com/watch?v=X2LcsQUtnzg", "prolapse", "beginner",
         "8-minute safe and effective workout to help fix pelvic prolapse."),
        ("6 Pelvic Floor & Core Exercises", "Dr. Kristie Ennis", 12, "https://www.youtube.com/watch?v=b8rpkX_10H0", "prolapse", "beginner",
         "6 pelvic floor and core exercises for prolapse healing."),
        ("Prolapse Safe Core Abdominal Exercises", "Michelle Kenway", 15, "https://www.youtube.com/watch?v=PYfvGRm2KyU", "prolapse", "beginner",
         "Core and abdominal exercises specifically designed to be safe for prolapse."),
        ("Safe Hips, Butt & Thighs for Prolapse", "Michelle Kenway", 15, "https://www.youtube.com/watch?v=-2gdZyGpyic", "prolapse", "beginner",
         "Physio-safe hips, butt and thighs exercises for prolapse and after surgery."),
        ("10-Min Rectocele Morning Routine", "Dr. Bri's Vibrant Pelvic Health", 10, "https://www.youtube.com/watch?v=gEVZ-ZJMjiI", "prolapse", "beginner",
         "10-minute morning routine for rectocele — do daily."),
        ("Yoga For Pelvic Floor", "Yoga With Adriene", 15, "https://www.youtube.com/watch?v=2aEceax_be4", "prolapse", "beginner",
         "Gentle yoga specifically for pelvic floor health — safe for prolapse."),
        ("Modify Yoga for Prolapse", "Michelle Kenway", 12, "https://www.youtube.com/watch?v=p3YeUPUtgUs", "prolapse", "beginner",
         "How to safely modify yoga poses after hysterectomy or pelvic prolapse."),
        ("Top 5 Pelvic Floor Exercises", "AskDoctorJo", 10, "https://www.youtube.com/watch?v=NKl8ImI3OVE", "prolapse", "beginner",
         "Top 5 pelvic floor exercises from a physical therapist."),
        ("Standing Pelvic Floor Exercises 10 min", "Caroline Jordan", 10, "https://www.youtube.com/watch?v=9ygJazIDgHc", "prolapse", "beginner",
         "10-minute standing pelvic floor exercises — very effective."),
        ("20 Min Prolapse Safe Weight Workout", "Dr. Bri's Vibrant Pelvic Health", 20, "https://www.youtube.com/watch?v=UVW3laviq-Y", "prolapse", "moderate",
         "Tone and tighten with prolapse-safe weight training — 20 minutes."),
    ]

    existing = c.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    if existing == 0:
        c.executemany(
            "INSERT INTO videos (name, coach, duration_min, url, category, intensity, description) VALUES (?,?,?,?,?,?,?)",
            videos,
        )

    # Seed routines
    routines = [
        ("Tabata (4 min)", "hiit", "20s all-out sprint → 10s rest. Repeat 8 times = 4 min. Add 2 min warm-up + 2 min cool-down = 8 min total.",
         "20s work / 10s rest × 8 rounds", "8", "beginner"),
        ("1:1 Intervals (15 min)", "hiit", "30s sprint → 30s easy recovery. Repeat for 15 minutes.",
         "30s work / 30s rest × 30 rounds", "15", "intermediate"),
        ("Pyramidal (20 min)", "hiit", "15s/45s → 30s/30s → 45s/15s → 60s/30s → 45s/15s → 30s/30s → 15s/45s. Repeat the cycle.",
         "Pyramid: 15/45 → 30/30 → 45/15 → 60/30 → 45/15 → 30/30 → 15/45", "20", "intermediate"),
        ("Climber + Push-ups (10 min)", "cross", "30s MaxiFitness → 10 push-ups. Repeat for 10 minutes.",
         "30s climber / 10 push-ups × repeat", "10", "beginner"),
        ("Climber + Burpees (15 min)", "cross", "15s MaxiFitness → 5 burpees. Repeat for 15 minutes.",
         "15s climber / 5 burpees × repeat", "15", "intermediate"),
        ("Climber + Jump Rope (20 min)", "cross", "60s MaxiFitness → 60s jump rope. Repeat for 20 minutes.",
         "60s climber / 60s jump rope × repeat", "20", "intermediate"),
        ("Climber + Weights (15 min)", "cross", "15s MaxiFitness → 10 overhead presses → 15 squats. Repeat.",
         "15s climber / 10 OHP / 15 squats × repeat", "15", "intermediate"),
    ]

    existing = c.execute("SELECT COUNT(*) FROM routines").fetchone()[0]
    if existing == 0:
        c.executemany(
            "INSERT INTO routines (name, category, description, structure, total_min, difficulty) VALUES (?,?,?,?,?,?)",
            routines,
        )

    # Seed schedule plans
    plans = [
        ("Foundation (Weeks 1-2)", 1, 2, "Beginner phase: 3 climbing days, ~45-55 min/week. All 10-min videos."),
        ("Build (Weeks 3-4)", 3, 4, "Intermediate phase: 4 climbing days, ~70-75 min/week. Mix of 10 and 20-min sessions."),
        ("Maintenance (Week 5+)", 5, 99, "Ongoing phase: 5 days/week, ~105-120 min. Rotating HIIT and steady-state."),
    ]

    existing = c.execute("SELECT COUNT(*) FROM schedule_plans").fetchone()[0]
    if existing == 0:
        for plan in plans:
            c.execute(
                "INSERT INTO schedule_plans (phase_name, week_start, week_end, description) VALUES (?,?,?,?)",
                plan,
            )

    # Seed schedule days
    schedule_days = [
        # Foundation
        (1, "Monday", "Rise & Climb", 10, "https://www.youtube.com/watch?v=W9G0SlxNl2M", "Beginner intervals", 0),
        (1, "Tuesday", None, 0, None, "Rest or light stretching", 1),
        (1, "Wednesday", "New Heights", 10, "https://www.youtube.com/watch?v=A2tFT4la0DU", "Sprints, reaches, intervals", 0),
        (1, "Thursday", None, 0, None, "Rest or light stretching", 1),
        (1, "Friday", "Tabata + Lower Body Sculpt", 10, "https://www.youtube.com/watch?v=hExoNY0m7pk", "Long and short strides", 0),
        (1, "Saturday", "Steady-State Climb", 15, None, "Your own pace, moderate", 0),
        (1, "Sunday", None, 0, None, "Rest day", 1),
        # Build
        (2, "Monday", "Tabata + Full-Body", 10, "https://www.youtube.com/watch?v=0DtMo88dOCk", "Sprints, strides, climbing squats", 0),
        (2, "Tuesday", "Steady-State Climb", 15, None, "Moderate pace, consistent rhythm", 0),
        (2, "Wednesday", "Full-Body Blaster", 20, "https://www.youtube.com/watch?v=TvkOIcNtWso", "Climbing squats, reverse grips, sprints, crunches", 0),
        (2, "Thursday", None, 0, None, "Rest day", 1),
        (2, "Friday", "Full-Body HIIT", 20, "https://www.youtube.com/watch?v=bzoIJ48WLxY", "Long strides, short strides, oblique crunches", 0),
        (2, "Saturday", "Steady-State or Leg Circuit", 20, None, "Moderate pace or custom routine", 0),
        (2, "Sunday", None, 0, None, "Rest or light stretching", 1),
        # Maintenance
        (3, "Monday", "HIIT Session", 20, None, "Rotate through 20-min videos", 0),
        (3, "Tuesday", "Steady-State Climb", 20, None, "Moderate pace, consistent rhythm", 0),
        (3, "Wednesday", "HIIT Session", 20, None, "Rotate through 20-min videos", 0),
        (3, "Thursday", None, 0, None, "Rest or active recovery", 1),
        (3, "Friday", "HIIT Session", 20, None, "Rotate through 20-min videos", 0),
        (3, "Saturday", "Long Climb or Custom HIIT", 30, None, "Push endurance, 25-30 min", 0),
        (3, "Sunday", None, 0, None, "Full recovery day", 1),
    ]

    existing = c.execute("SELECT COUNT(*) FROM schedule_days").fetchone()[0]
    if existing == 0:
        c.executemany(
            "INSERT INTO schedule_days (plan_id, day_name, workout_name, duration_min, video_url, description, is_rest) VALUES (?,?,?,?,?,?,?)",
            schedule_days,
        )

    # ── Plan 3: Weekly weigh-in tables ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS weekly_weighins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        weight REAL NOT NULL,
        notes TEXT,
        week_number INTEGER,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, date)
    )
    """)
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_weekly_weighins_user_date "
        "ON weekly_weighins(user_id, date DESC)"
    )

    c.execute("""
    CREATE TABLE IF NOT EXISTS weighin_milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        threshold INTEGER NOT NULL,
        achieved_date TEXT NOT NULL,
        weight_at_achievement REAL,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, threshold)
    )
    """)

    # ── Plan 6: Badge tables ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS badges (
        id INTEGER PRIMARY KEY,
        slug TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        icon TEXT NOT NULL,
        category TEXT NOT NULL,
        criteria_type TEXT NOT NULL,
        criteria_target INTEGER,
        criteria_detail TEXT,
        tier TEXT DEFAULT 'bronze',
        sort_order INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS user_badges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        badge_id INTEGER NOT NULL REFERENCES badges(id),
        earned_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(user_id, badge_id)
    )
    """)

    # ── Nutrition tables ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS nutrition_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        date TEXT NOT NULL,
        meal_type TEXT DEFAULT 'lunch' CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
        food_name TEXT NOT NULL,
        calories INTEGER,
        protein_g REAL,
        carbs_g REAL,
        fat_g REAL,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS daily_water (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        date TEXT NOT NULL,
        glasses INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, date)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS calorie_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        daily_goal INTEGER DEFAULT 1800,
        deficit_target INTEGER DEFAULT 500,
        water_glasses_goal INTEGER DEFAULT 8,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS food_database (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        calories INTEGER,
        protein_g REAL,
        carbs_g REAL,
        fat_g REAL,
        serving_desc TEXT DEFAULT 'per serving'
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS barcode_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        brand TEXT,
        category TEXT,
        calories REAL,
        protein REAL,
        carbs REAL,
        fat REAL,
        fiber REAL,
        sugar REAL,
        sodium REAL,
        cholesterol REAL,
        saturated_fat REAL,
        serving_gram_weight REAL,
        serving_description TEXT,
        data_quality REAL,
        source TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)


    # ── Workout plan tables ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS workout_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        frequency INTEGER NOT NULL DEFAULT 3,
        weeks_count INTEGER NOT NULL DEFAULT 1,
        is_template INTEGER NOT NULL DEFAULT 0,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS plan_days (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL REFERENCES workout_plans(id) ON DELETE CASCADE,
        week_number INTEGER NOT NULL DEFAULT 1,
        day_index INTEGER NOT NULL,
        is_rest INTEGER NOT NULL DEFAULT 0,
        video_id INTEGER REFERENCES videos(id),
        workout_name TEXT,
        duration_min INTEGER,
        description TEXT,
        order_within_week INTEGER NOT NULL DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS plan_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        plan_id INTEGER NOT NULL REFERENCES workout_plans(id) ON DELETE CASCADE,
        start_date TEXT NOT NULL,
        current_week INTEGER NOT NULL DEFAULT 1,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS workout_plan_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL REFERENCES plan_assignments(id) ON DELETE CASCADE,
        plan_day_id INTEGER NOT NULL REFERENCES plan_days(id) ON DELETE CASCADE,
        completed_date TEXT NOT NULL,
        skipped INTEGER NOT NULL DEFAULT 0,
        notes TEXT
    )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_plan_days_plan ON plan_days(plan_id, week_number, day_index)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_plan_assignments_user ON plan_assignments(user_id, is_active)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_plan_log_assignment ON workout_plan_log(assignment_id, plan_day_id)")

    # ── Partner accountability tables ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS partner_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_a_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        user_b_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'ended')),
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_a_id, user_b_id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        reaction_type TEXT NOT NULL CHECK (reaction_type IN ('fire', 'muscle', 'heart', 'star', 'wave')),
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(workout_id, user_id, reaction_type)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS joint_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partner_link_id INTEGER NOT NULL REFERENCES partner_links(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        description TEXT,
        goal_type TEXT NOT NULL CHECK (goal_type IN ('combined_workouts', 'combined_minutes', 'combined_days', 'combined_calories')),
        target_value INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'expired')),
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # ── Seed food database (idempotent) ──
    if existing == 0:
        foods = [
            ("Egg, large", 72, 6.3, 0.4, 4.8, "1 large egg"),
            ("Chicken breast, grilled", 165, 31, 0, 3.6, "3 oz"),
            ("Chicken thigh, grilled", 209, 25, 0, 11, "3 oz"),
            ("Ground beef, 80% lean", 250, 23, 0, 17, "3 oz"),
            ("Salmon, grilled", 206, 20, 0, 13, "3 oz"),
            ("Tuna, canned in water", 99, 22, 0, 1, "3 oz"),
            ("Turkey breast, deli", 30, 6, 0, 0.5, "1 oz"),
            ("Turkey sausage", 150, 14, 2, 9, "1 link"),
            ("Cottage cheese, 2%", 163, 24, 6, 5, "1 cup"),
            ("Greek yogurt, plain", 100, 17, 6, 0.7, "6 oz"),
            ("White rice, cooked", 206, 4.3, 45, 0.4, "1 cup"),
            ("Brown rice, cooked", 216, 5, 45, 1.8, "1 cup"),
            ("Pasta, cooked", 220, 8, 43, 1.3, "1 cup"),
            ("Bread, white, 1 slice", 79, 2.7, 15, 1, "1 slice"),
            ("Bread, whole wheat, 1 slice", 81, 4, 14, 1, "1 slice"),
            ("Potato, baked", 161, 4.3, 37, 0.2, "1 medium"),
            ("Sweet potato, baked", 112, 2, 26, 0.1, "1 medium"),
            ("Oatmeal, cooked", 154, 5.4, 27, 2.6, "1 cup"),
            ("Banana", 105, 1.3, 27, 0.4, "1 medium"),
            ("Apple", 95, 0.5, 25, 0.3, "1 medium"),
            ("Orange", 62, 1.2, 15.4, 0.2, "1 medium"),
            ("Grapes", 104, 0.7, 28, 0.2, "1 cup"),
            ("Strawberries", 49, 1.4, 12, 0.5, "1 cup"),
            ("Blueberries", 84, 1.1, 21, 0.5, "1 cup"),
            ("Tortilla, flour", 140, 3.5, 24, 2.5, "1 medium"),
            ("Broccoli, steamed", 55, 3.7, 11.5, 0.6, "1 cup"),
            ("Spinach, raw", 7, 0.9, 1.1, 0.1, "1 cup"),
            ("Carrots, raw", 52, 1.1, 12, 0.3, "1 medium"),
            ("Mixed vegetables, frozen", 70, 3, 14, 0.5, "1 cup"),
            ("Lettuce, iceberg", 10, 0.5, 2, 0.1, "1 cup"),
            ("Tomato, medium", 22, 1.1, 4.8, 0.2, "1 medium"),
            ("Corn, canned", 88, 2.5, 19, 1.2, "1/2 cup"),
            ("Peas, frozen", 115, 5.5, 21, 0.6, "1/2 cup"),
            ("Olive oil", 119, 0, 0, 14, "1 tbsp"),
            ("Butter", 102, 0.1, 0, 11.5, "1 tbsp"),
            ("Mayonnaise", 94, 0.1, 0, 10, "1 tbsp"),
            ("Peanut butter", 94, 4, 3, 8, "1 tbsp"),
            ("Almonds", 164, 6, 6, 14, "1 oz"),
            ("Milk, whole, 1 cup", 149, 8, 12, 8, "1 cup"),
            ("Milk, 2%, 1 cup", 122, 8.5, 12, 4.5, "1 cup"),
            ("Milk, 1%, 1 cup", 102, 8.5, 12, 2.5, "1 cup"),
            ("Cheddar cheese, 1 oz", 113, 7, 0.4, 9.4, "1 oz"),
            ("Mozzarella, 1 oz", 85, 6.3, 0.9, 6.3, "1 oz"),
            ("Potato chips, 1 oz", 152, 2, 15, 10, "1 oz"),
            ("Granola bar", 190, 3, 29, 7, "1 bar"),
            ("Protein bar", 220, 20, 24, 8, "1 bar"),
            ("Popcorn, air-popped, 3 cups", 62, 2.2, 12, 0.7, "3 cups"),
            ("Dark chocolate, 1 oz", 170, 2.2, 13, 12, "1 oz"),
            ("Coca-Cola, 12 oz", 140, 0, 39, 0, "12 oz can"),
            ("Water", 0, 0, 0, 0, "1 cup"),
            ("Coffee, black", 2, 0.3, 0, 0, "1 cup"),
            ("Coffee with cream/sugar", 55, 1, 7, 2, "1 cup"),
            ("Tea, unsweetened", 0, 0, 0, 0, "1 cup"),
        ]
        c.executemany(
            "INSERT INTO food_database (name, calories, protein_g, carbs_g, fat_g, serving_desc) VALUES (?, ?, ?, ?, ?, ?)",
            foods,
        )


    # ── Seed template workout plans (idempotent) ──
    existing = c.execute("SELECT COUNT(*) FROM workout_plans").fetchone()[0]
    if existing == 0:
        # Video ID lookup helper
        def _vid(name_pat):
            r = c.execute("SELECT id, name, duration_min FROM videos WHERE name LIKE ? LIMIT 1", (f"%{name_pat}%",)).fetchone()
            return dict(r) if r else None

        def _seed_plan(name, desc, freq, weeks, day_map):
            """day_map: {week: {day_index: video_name_pattern}} — 0=Mon..6=Sun"""
            pid = c.execute(
                "INSERT INTO workout_plans (name, description, frequency, weeks_count, is_template) VALUES (?,?,?,?,1)",
                (name, desc, freq, weeks),
            ).lastrowid
            for wk in range(1, weeks + 1):
                wo = 0
                wk_map = day_map.get(wk, day_map[1])  # default to week 1 if not specified
                for di in range(7):
                    if di in wk_map:
                        wo += 1
                        v = _vid(wk_map[di])
                        c.execute(
                            "INSERT INTO plan_days (plan_id, week_number, day_index, is_rest, video_id, workout_name, duration_min, order_within_week) VALUES (?,?,?,?,?,?,?,?)",
                            (pid, wk, di, 0, v["id"] if v else None, v["name"] if v else None, v["duration_min"] if v else None, wo),
                        )
                    else:
                        c.execute(
                            "INSERT INTO plan_days (plan_id, week_number, day_index, is_rest, order_within_week) VALUES (?,?,?,?,0)",
                            (pid, wk, di, 1),
                        )
            return pid

        # Beginner 3-Day (Mon/Wed/Fri = 0,2,4)
        _seed_plan(
            "Beginner 3-Day",
            "3 days/week for new users. Progressive overload across 4 weeks.",
            3, 4,
            {
                1: {0: "Rise & Climb", 2: "New Heights", 4: "Tabata + Lower Body"},
                2: {0: "Rise & Climb", 2: "Full-Body Blaster", 4: "Tabata + Lower Body"},
                3: {0: "10-Minute Yoga For Beginners", 2: "Full-Body Blaster", 4: "Full-Body HIIT"},
                4: {0: "10-Minute Yoga For Beginners", 2: "Full-Body Blaster", 4: "Full-Body HIIT", 5: "20-Minute Yoga For Beginners"},
            },
        )

        # Intermediate 4-Day (Mon/Tue/Thu/Sat = 0,1,3,5)
        _seed_plan(
            "Intermediate 4-Day",
            "4 days/week for consistent exercisers. Build strength and endurance.",
            4, 4,
            {
                1: {0: "10 Min Dumbbell Strength", 1: "Tabata + Full-Body", 3: "11 Min Back and Biceps", 5: "20 Min Home Upper Body"},
                2: {0: "10 Min Dumbbell Strength", 1: "Full-Body Blaster", 3: "11 Min Back and Biceps", 5: "20 Min Home Upper Body"},
                3: {0: "10 Min Dumbbell Strength", 1: "Full-Body Blaster", 3: "20 Min Back & Biceps", 5: "20 Min Home Upper Body"},
                4: {0: "10 Min Dumbbell Strength", 1: "Full-Body HIIT", 3: "20 Min Back & Biceps", 5: "22 Min Legs & Shoulders"},
            },
        )

        # Prolapse-Safe 3-Day (Mon/Wed/Fri = 0,2,4)
        _seed_plan(
            "Prolapse-Safe 3-Day",
            "3 days/week — all exercises vetted for pelvic floor safety.",
            3, 4,
            {
                1: {0: "5 Simple Pelvic Support", 2: "8-Minute Pelvic Prolapse", 4: "Seated Chair Core"},
                2: {0: "5 Simple Pelvic Support", 2: "Prolapse Safe Core Abdominal", 4: "Seated Chair Core"},
                3: {0: "Yoga For Pelvic Floor", 2: "Prolapse Safe Core Abdominal", 4: "15 Minute Prolapse Safe"},
                4: {0: "Yoga For Pelvic Floor", 2: "20 Min Prolapse Safe Full Body", 4: "20 Min Prolapse Safe Weight"},
            },
        )


    # ── Shared cross-plan migration: add columns used by Phase 2 plans ──
    try:
        c.execute("ALTER TABLE users ADD COLUMN prolapse_safe INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN weighin_day INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN age INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN gender TEXT DEFAULT 'female'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE workouts ADD COLUMN exertion INTEGER DEFAULT NULL CHECK (exertion BETWEEN 1 AND 5)")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE nutrition_log ADD COLUMN barcode TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN if_start_hour INTEGER DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN if_end_hour INTEGER DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN diet_focus TEXT DEFAULT 'calorie' CHECK (diet_focus IN ('calorie', 'keto', 'protein', 'balanced'))")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE calorie_goals ADD COLUMN protein_goal REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE calorie_goals ADD COLUMN carbs_goal REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE calorie_goals ADD COLUMN fat_goal REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE barcode_cache ADD COLUMN image_url TEXT")
    except sqlite3.OperationalError:
        pass

    # ── Progress photos table ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS progress_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        angle TEXT NOT NULL CHECK (angle IN ('front', 'side', 'back')),
        file_path TEXT NOT NULL,
        thumbnail_path TEXT NOT NULL,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_progress_photos_user_date ON progress_photos(user_id, date, angle)")

    # ── Wellness log table ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS wellness_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        date TEXT NOT NULL,
        energy INTEGER CHECK (energy BETWEEN 1 AND 5),
        mood INTEGER CHECK (mood BETWEEN 1 AND 5),
        sleep INTEGER CHECK (sleep BETWEEN 1 AND 5),
        clothing_fit TEXT CHECK (clothing_fit IN ('tight', 'fitting', 'loose', 'very_loose')),
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, date)
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_wellness_log_user_date ON wellness_log(user_id, date)")

    # ── Seed badge definitions (idempotent) ──
    existing = c.execute("SELECT COUNT(*) FROM badges").fetchone()[0]
    if existing == 0:
        badges = [
            # (id, slug, name, description, icon, category, criteria_type, target, detail, tier, sort_order)
            (1,  "first_workout",              "First Steps",            "Log your very first workout.",                                    "🏁", "workout",     "one_time",        1,  None,                            "bronze",   1),
            (2,  "ten_workouts",               "Ten Out of Ten",         "Complete 10 total workouts.",                                   "🎯", "workout",     "count",           10, None,                            "bronze",   2),
            (3,  "fifty_workouts",             "Fifty Shades of Sweat",  "Complete 50 total workouts.",                                   "💪", "workout",     "count",           50, None,                            "silver",   3),
            (4,  "hundred_workouts",           "Century Club",           "Complete 100 total workouts.",                                 "🏆", "workout",     "count",           100,None,                            "gold",     4),
            (5,  "ten_minute_warrior",         "Quick Hit",              "Complete any workout of at least 10 minutes.",                  "⚡", "workout",     "count_in_period", 1,  '{"min_duration":10,"period":"single"}',          "bronze",   5),
            (6,  "thirty_minute_session",      "Half Hour Hero",         "Complete a single workout of at least 30 minutes.",             "🔥", "workout",     "count_in_period", 1,  '{"min_duration":30,"period":"single"}',         "silver",   6),
            (7,  "high_intensity_5",           "Power Player",           "Complete 5 high-intensity workouts.",                             "⚡", "workout",     "count_in_period", 5,  '{"intensity":"high","period":"total"}',         "silver",   7),
            (8,  "monthly_10",                 "Monthly Commitment",     "Log 10 workouts in a single calendar month.",                  "📅", "workout",     "count_in_period", 10, '{"period":"month"}',                      "bronze",   8),
            (9,  "monthly_20",                 "Monthly Machine",        "Log 20 workouts in a single calendar month.",                  "🏋️", "workout",     "count_in_period", 20, '{"period":"month"}',                      "silver",   9),
            (10, "total_duration_10h",         "Endurance",              "Accumulate 10 hours (600 min) of total workout time.",            "⏱️", "workout",     "duration",        600,None,                            "silver",   10),
            (11, "total_duration_25h",         "Marathon Mindset",       "Accumulate 25 hours (1500 min) of total workout time.",         "🏅", "workout",     "duration",        1500,None,                           "gold",     11),
            (12, "calories_5000",              "Calorie Crusher",        "Burn 5,000 total estimated calories.",                          "🔥", "workout",     "calories",        5000,None,                           "bronze",   12),
            (13, "calories_15000",             "Furnace",                "Burn 15,000 total estimated calories.",                        "💥", "workout",     "calories",        15000,None,                          "silver",   13),
            (14, "variety_5_types",            "Jack of All Trades",     "Work out with 5 different workout types.",                     "🎲", "workout",     "variety",         5,  '{"field":"workout_type"}',              "bronze",   14),
            (15, "first_weighin",              "Weigh-In Day",           "Record your first weight entry.",                               "⚖️", "weight",      "one_time",        1,  None,                            "bronze",   1),
            (16, "weight_loss_5",              "Down 5 Pounds",          "Lose 5 lbs from your starting weight.",                        "📉", "weight",      "weight_loss",     5,  None,                            "silver",   2),
            (17, "weight_loss_10",             "Down 10 Pounds",         "Lose 10 lbs from your starting weight.",                      "🎉", "weight",      "weight_loss",     10, None,                            "gold",     3),
            (18, "weight_loss_20",             "Down 20 Pounds",         "Lose 20 lbs from your starting weight.",                      "🌟", "weight",      "weight_loss",     20, None,                            "platinum", 4),
            (19, "metrics_10_entries",         "Data Driven",            "Record 10 daily metric entries.",                              "📊", "weight",      "count",           10, '{"table":"daily_metrics"}',           "bronze",   5),
            (20, "streak_3",                   "Three Day Streak",       "Work out 3 days in a row.",                                 "🔥", "consistency", "streak",          3,  None,                            "bronze",   1),
            (21, "streak_7",                   "Week Warrior",           "Work out 7 days in a row.",                                 "🗓️", "consistency", "streak",          7,  None,                            "silver",   2),
            (22, "streak_14",                  "Two Week Streak",        "Work out 14 days in a row.",                               "💎", "consistency", "streak",          14, None,                            "gold",     3),
            (23, "streak_30",                  "Month of Fire",          "Work out 30 days in a row.",                               "🔥", "consistency", "streak",          30, None,                            "platinum", 4),
            (24, "gentle_warrior",             "Gentle Warrior",         "Complete 10 low-impact workouts — safe and steady.",          "🌸", "milestone",   "count_in_period", 10, '{"intensity":"beginner","period":"total"}', "silver",   1),
            (25, "consistency_over_intensity", "Steady as She Goes",     "Log 30 workouts of at least 15 minutes — consistency wins.", "🐢", "milestone",   "count",           30, '{"min_duration":15}',                  "bronze",   2),
        ]
        c.executemany(
            "INSERT INTO badges (id, slug, name, description, icon, category, criteria_type, criteria_target, criteria_detail, tier, sort_order) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            badges,
        )

    conn.commit()
    conn.close()
def get_streak(conn, user_id):
    """Return current streak length (consecutive days with workouts).
    
    A streak counts today or yesterday as the starting point — if the user
    worked out yesterday but not today, the streak is still alive.
    Hard-capped at 365 days to prevent runaway loops.
    """
    from datetime import date, timedelta
    rows = conn.execute(
        "SELECT DISTINCT date FROM workouts WHERE user_id = ? ORDER BY date DESC",
        (user_id,)
    ).fetchall()
    dates = {date.fromisoformat(r['date']) for r in rows}

    if not dates:
        return 0

    today = date.today()
    start = today if today in dates else today - timedelta(days=1)

    streak = 0
    d = start
    while d in dates and streak < 365:
        streak += 1
        d -= timedelta(days=1)
    return streak


def get_weekly_stats(conn, user_id):
    """Return workout days this week (Mon–today) and consistency %."""
    from datetime import date, timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday

    rows = conn.execute(
        "SELECT DISTINCT date FROM workouts WHERE user_id = ? AND date >= ?",
        (user_id, week_start.isoformat())
    ).fetchall()

    workout_days = len(rows)
    days_since_start = (today - week_start).days + 1
    consistency = round(workout_days / days_since_start * 100) if days_since_start > 0 else 0

    return {
        'workout_days': workout_days,
        'days_in_week': days_since_start,
        'consistency': consistency,
        'dates': [r['date'] for r in rows],
    }


def get_monthly_stats(conn, user_id):
    """Return workout days this month and consistency %."""
    from datetime import date, timedelta
    today = date.today()
    month_start = today.replace(day=1)

    rows = conn.execute(
        "SELECT DISTINCT date FROM workouts WHERE user_id = ? AND date >= ?",
        (user_id, month_start.isoformat())
    ).fetchall()

    workout_days = len(rows)
    days_in_month = today.day
    consistency = round(workout_days / days_in_month * 100) if days_in_month > 0 else 0

    return {
        'workout_days': workout_days,
        'days_in_month': days_in_month,
        'consistency': consistency,
        'dates': [r['date'] for r in rows],
    }


def get_heatmap_data(conn, user_id):
    """Return last 12 weeks of workout data as a 12×7 grid for the heatmap."""
    from datetime import date, timedelta
    today = date.today()
    start = today - timedelta(days=83)  # ~12 weeks

    rows = conn.execute(
        "SELECT date, COALESCE(SUM(duration_min), 0) as total_min, "
        "COALESCE(SUM(calories), 0) as total_cal "
        "FROM workouts WHERE user_id = ? AND date >= ? "
        "GROUP BY date ORDER BY date",
        (user_id, start.isoformat())
    ).fetchall()

    data = {r['date']: {'duration_min': r['total_min'], 'calories': r['total_cal']} for r in rows}

    weeks = []
    current = start - timedelta(days=start.weekday())  # Start on Monday
    for _ in range(12):
        week = []
        for day_offset in range(7):
            d = current + timedelta(days=day_offset)
            d_str = d.isoformat()
            info = data.get(d_str, {'duration_min': 0, 'calories': 0})
            week.append({
                'date': d_str,
                'duration_min': info['duration_min'],
                'calories': info['calories'],
                'has_workout': info['duration_min'] > 0,
            })
        weeks.append(week)
        current += timedelta(days=7)

    return weeks


def compute_ema_list(values, span=4):
    """Compute exponential moving average over a list of values.

    Uses alpha = 2 / (span + 1). First value is the initial EMA.
    """
    if not values:
        return []
    alpha = 2 / (span + 1)
    ema_values = [values[0]]
    for i in range(1, len(values)):
        ema = alpha * values[i] + (1 - alpha) * ema_values[-1]
        ema_values.append(round(ema, 1))
    return ema_values


def compute_ema(conn, user_id, span=4):
    """Compute the latest EMA value from weekly weigh-ins."""
    rows = conn.execute(
        "SELECT weight FROM weekly_weighins WHERE user_id = ? ORDER BY date ASC",
        (user_id,)
    ).fetchall()
    if not rows:
        return None
    weights = [r["weight"] for r in rows]
    ema_values = compute_ema_list(weights, span)
    return ema_values[-1] if ema_values else None


def check_milestones(conn, user_id, current_weight, start_weight):
    """Check and record any newly achieved milestones.

    Returns a list of milestone dicts for ones achieved this weigh-in.
    """
    from datetime import date
    if not start_weight:
        return []

    total_loss = round(start_weight - current_weight, 1)
    new_milestones = []

    for threshold in [5, 10, 15, 20, 25, 30]:
        if total_loss >= threshold:
            existing = conn.execute(
                "SELECT id FROM weighin_milestones "
                "WHERE user_id = ? AND threshold = ?",
                (user_id, threshold),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO weighin_milestones "
                    "(user_id, threshold, achieved_date, weight_at_achievement) "
                    "VALUES (?, ?, ?, ?)",
                    (user_id, threshold, date.today().isoformat(), current_weight),
                )
                new_milestones.append({
                    "threshold": threshold,
                    "message": f"You've lost {threshold} lbs! 🎉",
                })

    return new_milestones


def _check_badge(conn, user_id, badge):
    """Check if a badge criteria is met. Returns True if it should be awarded."""
    import json
    from datetime import datetime
    ct = badge["criteria_type"]
    target = badge["criteria_target"]
    detail = json.loads(badge["criteria_detail"]) if badge["criteria_detail"] else {}

    if ct == "one_time":
        count = conn.execute(
            "SELECT COUNT(*) FROM workouts WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        return count >= target

    elif ct == "count":
        table = detail.get("table", "workouts")
        where = "user_id = ?"
        params = [user_id]
        if detail.get("min_duration"):
            where += " AND duration_min >= ?"
            params.append(detail["min_duration"])
        count = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()[0]
        return count >= target

    elif ct == "duration":
        total = conn.execute(
            "SELECT COALESCE(SUM(duration_min), 0) FROM workouts WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        return total >= target

    elif ct == "calories":
        total = conn.execute(
            "SELECT COALESCE(SUM(calories), 0) FROM workouts WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        return total >= target

    elif ct == "weight_loss":
        earliest = conn.execute(
            "SELECT weight FROM daily_metrics WHERE user_id = ? AND weight IS NOT NULL ORDER BY date ASC LIMIT 1",
            (user_id,),
        ).fetchone()
        latest = conn.execute(
            "SELECT weight FROM daily_metrics WHERE user_id = ? AND weight IS NOT NULL ORDER BY date DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if earliest and latest and earliest["weight"] and latest["weight"]:
            return (earliest["weight"] - latest["weight"]) >= target
        return False

    elif ct == "streak":
        return get_streak(conn, user_id) >= target

    elif ct == "variety":
        field = detail.get("field", "workout_type")
        count = conn.execute(
            f"SELECT COUNT(DISTINCT {field}) FROM workouts WHERE user_id = ? AND {field} IS NOT NULL",
            (user_id,),
        ).fetchone()[0]
        return count >= target

    elif ct == "count_in_period":
        period = detail.get("period", "total")
        min_duration = detail.get("min_duration")
        intensity = detail.get("intensity")

        if period == "month":
            months = conn.execute(
                "SELECT DISTINCT strftime('%Y-%m', date) as month FROM workouts WHERE user_id = ? ORDER BY month",
                (user_id,),
            ).fetchall()
            for month_row in months:
                month = month_row["month"]
                where = "user_id = ? AND strftime('%Y-%m', date) = ?"
                params = [user_id, month]
                if min_duration:
                    where += " AND duration_min >= ?"
                    params.append(min_duration)
                if intensity:
                    where += " AND intensity = ?"
                    params.append(intensity)
                count = conn.execute(f"SELECT COUNT(*) FROM workouts WHERE {where}", params).fetchone()[0]
                if count >= target:
                    return True
            return False

        elif period in ("single", "total"):
            where = "user_id = ?"
            params = [user_id]
            if min_duration:
                where += " AND duration_min >= ?"
                params.append(min_duration)
            if intensity:
                where += " AND intensity = ?"
                params.append(intensity)
            count = conn.execute(f"SELECT COUNT(*) FROM workouts WHERE {where}", params).fetchone()[0]
            return count >= target

        return False

    return False


def get_badge_progress(conn, user_id, badge):
    """Return (current_value, target) for a locked badge."""
    import json
    from datetime import datetime
    ct = badge["criteria_type"]
    target = badge["criteria_target"]
    detail = json.loads(badge["criteria_detail"]) if badge["criteria_detail"] else {}

    if ct == "one_time":
        count = conn.execute(
            "SELECT COUNT(*) FROM workouts WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        return count, target

    elif ct == "count":
        table = detail.get("table", "workouts")
        where = "user_id = ?"
        params = [user_id]
        if detail.get("min_duration"):
            where += " AND duration_min >= ?"
            params.append(detail["min_duration"])
        count = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()[0]
        return count, target

    elif ct == "duration":
        total = conn.execute(
            "SELECT COALESCE(SUM(duration_min), 0) FROM workouts WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        return total, target

    elif ct == "calories":
        total = conn.execute(
            "SELECT COALESCE(SUM(calories), 0) FROM workouts WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        return total, target

    elif ct == "weight_loss":
        earliest = conn.execute(
            "SELECT weight FROM daily_metrics WHERE user_id = ? AND weight IS NOT NULL ORDER BY date ASC LIMIT 1",
            (user_id,),
        ).fetchone()
        latest = conn.execute(
            "SELECT weight FROM daily_metrics WHERE user_id = ? AND weight IS NOT NULL ORDER BY date DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if earliest and latest and earliest["weight"] and latest["weight"]:
            return max(0, earliest["weight"] - latest["weight"]), target
        return 0, target

    elif ct == "streak":
        return get_streak(conn, user_id), target

    elif ct == "variety":
        field = detail.get("field", "workout_type")
        count = conn.execute(
            f"SELECT COUNT(DISTINCT {field}) FROM workouts WHERE user_id = ? AND {field} IS NOT NULL",
            (user_id,),
        ).fetchone()[0]
        return count, target

    elif ct == "count_in_period":
        period = detail.get("period", "total")
        min_duration = detail.get("min_duration")
        intensity = detail.get("intensity")

        if period == "month":
            current_month = datetime.now().strftime("%Y-%m")
            where = "user_id = ? AND strftime('%Y-%m', date) = ?"
            params = [user_id, current_month]
            if min_duration:
                where += " AND duration_min >= ?"
                params.append(min_duration)
            if intensity:
                where += " AND intensity = ?"
                params.append(intensity)
            count = conn.execute(f"SELECT COUNT(*) FROM workouts WHERE {where}", params).fetchone()[0]
            return count, target

        elif period in ("single", "total"):
            where = "user_id = ?"
            params = [user_id]
            if min_duration:
                where += " AND duration_min >= ?"
                params.append(min_duration)
            if intensity:
                where += " AND intensity = ?"
                params.append(intensity)
            count = conn.execute(f"SELECT COUNT(*) FROM workouts WHERE {where}", params).fetchone()[0]
            return count, target

        return 0, target

    return 0, target


def evaluate_badges(user_id):
    """Check all badge criteria and award any newly earned badges.
    Returns a list of newly earned badge dicts."""
    conn = get_db()
    newly_earned = []

    badges = conn.execute("SELECT * FROM badges ORDER BY sort_order").fetchall()
    earned_ids = {
        row["badge_id"]
        for row in conn.execute(
            "SELECT badge_id FROM user_badges WHERE user_id = ?", (user_id,)
        ).fetchall()
    }

    for badge in badges:
        if badge["id"] in earned_ids:
            continue
        if _check_badge(conn, user_id, badge):
            conn.execute(
                "INSERT INTO user_badges (user_id, badge_id, earned_at) VALUES (?, ?, datetime('now'))",
                (user_id, badge["id"]),
            )
            newly_earned.append(dict(badge))

    conn.commit()
    conn.close()
    return newly_earned


def recommend_workout(conn, user_id, user):
    """Return a recommended video based on history, prolapse safety, and recovery."""
    import random
    from datetime import date, timedelta
    today = date.today().isoformat()

    # 1. Determine safe categories
    if user.get("prolapse_safe"):
        safe_categories = ["prolapse", "yoga"]
    else:
        safe_categories = ["10min", "20min", "dumbbell", "back_biceps", "chest_tricep", "shoulder_legs", "yoga"]

    # 2. Recent workout history (last 7 days) — no video_id join needed
    recent = conn.execute(
        "SELECT intensity, workout_type FROM workouts WHERE user_id = ? AND date >= ? ORDER BY date DESC, id DESC LIMIT 10",
        (user_id, (date.today() - timedelta(days=7)).isoformat()),
    ).fetchall()

    last_intensity = recent[0]["intensity"] if recent else None

    # 3. Total workouts for progressive difficulty
    total_workouts = conn.execute(
        "SELECT COUNT(*) FROM workouts WHERE user_id = ?", (user_id,)
    ).fetchone()[0]

    # 4. Get all available videos in safe categories
    placeholders = ",".join("?" * len(safe_categories))
    available = conn.execute(
        f"SELECT * FROM videos WHERE category IN ({placeholders})",
        safe_categories,
    ).fetchall()

    if not available:
        return None

    # 5. Score each video
    def score_video(video):
        score = 0
        intensity = video["intensity"]

        # Progressive difficulty
        if total_workouts < 10:
            if intensity == "beginner": score += 15
            elif intensity == "moderate": score += 5
            else: score -= 10
        elif total_workouts < 30:
            if intensity == "moderate": score += 10
            elif intensity == "beginner": score += 5
        else:
            if intensity == "high": score += 10
            elif intensity == "moderate": score += 5

        # Recovery: after high intensity, prefer lighter
        if last_intensity == "high":
            if intensity in ("beginner", "moderate"): score += 10
            else: score -= 5

        # Random factor for variety
        score += random.randint(0, 5)

        return score

    scored = [(score_video(v), v) for v in available]
    scored.sort(key=lambda x: -x[0])

    if not scored:
        return None

    recommended = scored[0][1]
    reasons = []
    if total_workouts < 10 and recommended["intensity"] == "beginner":
        reasons.append("Starting gentle to build consistency")
    elif last_intensity == "high" and recommended["intensity"] != "high":
        reasons.append("Lighter day after yesterday's intense workout")
    if not reasons:
        reasons.append("Great choice for today!")

    return {
        "video": dict(recommended),
        "reasons": reasons,
        "score": scored[0][0],
    }


def get_variety_report(conn, user_id):
    """Report on workout type variety — which categories have been tried."""
    all_categories = conn.execute("SELECT DISTINCT category FROM videos").fetchall()
    tried_types = conn.execute(
        "SELECT DISTINCT workout_type FROM workouts WHERE user_id = ? AND workout_type IS NOT NULL",
        (user_id,),
    ).fetchall()

    tried = {r["workout_type"] for r in tried_types}
    all_cats = {r["category"] for r in all_categories}

    return {
        "tried": sorted(tried),
        "untried": sorted(all_cats - tried),
        "total_categories": len(all_cats),
    }


def seed_settings_if_empty(start_weight=None, goal_weight=None):
    """Create a default settings row if none exists."""
    conn = get_db()
    existing = conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
    if existing == 0:
        conn.execute(
            "INSERT INTO settings (start_weight, goal_weight, start_date) VALUES (?, ?, ?)",
            (start_weight, goal_weight, date.today().isoformat()),
        )
        conn.commit()
    conn.close()


def calculate_bmr(user):
    """Mifflin-St Jeor BMR calculation from a user dict."""
    weight_kg = (user.get("weight_lbs") or 150) / 2.205
    height_cm = ((user.get("height_ft") or 5) * 12 + (user.get("height_in") or 0)) * 2.54
    age = user.get("age") or 30
    if user.get("gender") == "male":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

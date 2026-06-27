"""Automated test suite for MaxiFitness — run with: source venv/bin/activate && python test_all.py"""
import json, sys
sys.path.insert(0, '.')
from app import app

client = app.test_client()

def test_page(path):
    r = client.get(path, follow_redirects=True)
    icon = '✅' if r.status_code == 200 else '❌'
    snippet = ''
    if r.status_code != 200:
        snippet = f' — {r.data.decode()[:120]}'
    return f'{icon} {path:40s} {r.status_code}{snippet}', r.status_code == 200

def test_post(path, data):
    r = client.post(path, data=data, follow_redirects=True)
    icon = '✅' if r.status_code in (200, 302) else '❌'
    snippet = ''
    if r.status_code not in (200, 302):
        snippet = f' — {r.data.decode()[:120]}'
    return f'{icon} {path:40s} {r.status_code}{snippet}', r.status_code in (200, 302)

def test_json(path):
    r = client.get(path)
    icon = '✅' if r.status_code == 200 else '❌'
    snippet = ''
    if r.status_code != 200:
        snippet = f' — {r.data.decode()[:120]}'
    return f'{icon} {path:40s} {r.status_code}{snippet}', r.status_code == 200

def test_json_post(path, data, expect_codes=None):
    r = client.post(path, json=data, follow_redirects=False)
    ok_codes = expect_codes or (200, 302, 400, 403, 404)
    icon = '✅' if r.status_code in ok_codes else '❌'
    snippet = ''
    if r.status_code not in ok_codes:
        snippet = f' — {r.data.decode()[:120]}'
    return f'{icon} {path:40s} {r.status_code}{snippet}', r.status_code in ok_codes

results = []
all_ok = True

def run(label, fn):
    global all_ok
    r, ok = fn()
    results.append(r)
    print(r)
    if not ok:
        all_ok = False

# Login as first user (user 1)
print('=== Login ===')
run('Login as first user (user 1)', lambda: test_post('/users/1/select', {}))

print('\n=== PAGE LOADS ===')
run('Dashboard',          lambda: test_page('/'))
run('Workouts',           lambda: test_page('/workouts'))
run('Videos',             lambda: test_page('/videos'))
run('Routines',           lambda: test_page('/routines'))
run('Schedule',           lambda: test_page('/schedule'))
run('Progress',           lambda: test_page('/progress'))
run('Users',              lambda: test_page('/users'))
run('Badges',             lambda: test_page('/badges'))
run('Nutrition',          lambda: test_page('/nutrition'))
run('Recommend',          lambda: test_page('/recommend'))
run('Plans',              lambda: test_page('/plans'))
run('Partner',            lambda: test_page('/partner'))
run('Partner Goals',      lambda: test_page('/partner/goals'))

print('\n=== API ENDPOINTS ===')
run('Weight Chart',       lambda: test_json('/api/weight-chart'))
run('Weekly Chart',       lambda: test_json('/api/weekly-chart'))
run('Weigh-In Status',    lambda: test_json('/api/weighin-status'))
run('Recommend Random',   lambda: test_json('/api/recommend-random'))
run('Today Workout',      lambda: test_json('/api/today-workout'))
run('Photos (user 1)',    lambda: test_json('/api/photos/1'))
run('Wellness (user 1)',  lambda: test_json('/api/wellness/1'))

print('\n=== POST ACTIONS ===')
run('Log Workout',        lambda: test_post('/workouts', {'date': '2026-06-20', 'duration_min': '25', 'calories': '250', 'workout_type': 'hiit', 'intensity': 'high'}))
run('Log Nutrition',      lambda: test_post('/nutrition/log', {'food_id': '1', 'date': '2026-06-20', 'quantity': '1', 'unit': 'serving'}))
run('Log Water',          lambda: test_post('/nutrition/water', {'date': '2026-06-20', 'glasses': '1'}))
run('Log Wellness',       lambda: test_post('/progress/wellness', {'date': '2026-06-20', 'energy': '4', 'mood': '5', 'sleep': '4', 'clothing_fit': 'fitting', 'notes': 'auto-test'}))
run('Set Calorie Goal',   lambda: test_post('/nutrition/goal', {'date': '2026-06-20', 'calories': '2000'}))

print('\n=== JSON API POSTS ===')
run('Partner Reaction',   lambda: test_json_post('/api/partner/reaction', {'workout_id': 99999, 'reaction_type': 'fire'}))
run('Create Goal',        lambda: test_json_post('/api/partner/goals', {'name': 'test', 'goal_type': 'combined_workouts', 'target_value': 10, 'start_date': '2026-06-20', 'end_date': '2026-07-20'}))

print('\n=== WEIGH-IN (POST) ===')
run('Weigh-In Day POST',  lambda: test_json_post('/api/weighin-day', {'weighin_day': '1'}))
run('Weekly Weigh-In',    lambda: test_json_post('/api/weekly-weighin', {'weight': '180.0', 'notes': 'auto-test'}))

print('\n=== PLAN ROUTES ===')
run('View Plan 1',        lambda: test_page('/plans/1'))
run('New Plan page',      lambda: test_page('/plans/new'))

print('\n=== DELETE ROUTES ===')
run('Delete Nutrition',   lambda: test_post('/nutrition/delete/99999', {}))

print(f'\n{"="*60}')
failed = [r for r in results if '❌' in r]
if failed:
    print(f'FAILED ({len(failed)}):')
    for r in failed:
        print(f'  {r}')
else:
    print('ALL TESTS PASSED ✅')
print(f'Total: {len(results)} tests')

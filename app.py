from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import json
from datetime import datetime

app = Flask(__name__)
# secret key for session/flash messages; in production use an environment variable
app.secret_key = 'replace-with-secure-random'

# --- persistence helpers --------------------------------------------------

DATA_DIR = 'data'


def ensure_data_dir():
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR)


def _convert_datetimes(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _convert_datetimes(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_datetimes(v) for v in obj]
    return obj


def save_to_file(filename, data):
    ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w') as f:
        json.dump(_convert_datetimes(data), f, indent=2)


def load_from_file(filename, default):
    ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        save_to_file(filename, default)
        return default.copy() if isinstance(default, list) else default
    with open(path) as f:
        data = json.load(f)
    # convert known iso strings back to datetime
    if filename == 'users.json':
        for item in data:
            if isinstance(item.get('last_login'), str):
                try:
                    item['last_login'] = datetime.fromisoformat(item['last_login'])
                except ValueError:
                    pass
    return data

# load or seed persistent lists
users = load_from_file('users.json', [])
next_user_id = max((u.get('id', 0) for u in users), default=0) + 1

assessments = load_from_file('assessments.json', [])
next_assessment_id = max((a.get('id', 0) for a in assessments), default=0) + 1


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # placeholder authentication logic
        if username == 'admin' and password == '1234':
            session['logged_in'] = True
            session['role'] = 'admin'
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        elif username == 'candidate' and password == '1234':
            session['logged_in'] = True
            session['role'] = 'candidate'
            flash('Login successful', 'success')
            return redirect(url_for('candidate_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    # Admin overview page (previously dashboard)
    return redirect(url_for('admin_overview'))

# admin area pages
@app.route('/admin')
def admin_overview():
    # calculate stats from file-backed store
    current_users = users
    current_assessments = assessments
    stats = {
        'total_candidates': len([u for u in current_users if u['role'] == 'Candidate']),
        'active_assessments': len([a for a in current_assessments if a.get('is_published')]),
        'completed_attempts': sum(a.get('attempt_count', 0) for a in current_assessments),
        'average_score': 85,
    }

    overview_assessments = [
        {
            'id': a['id'],
            'title': a['title'],
            'is_published': a.get('is_published'),
            'duration': a.get('duration'),
            'attempt_count': a.get('attempt_count', 0),
        }
        for a in current_assessments
    ]

    return render_template(
        'admin_overview.html',
        active='overview',
        users=current_users,
        assessments=overview_assessments,
        **stats,
    )

@app.route('/admin/candidates')
def admin_candidates():
    candidate_list = [u for u in users if u['role'] == 'Candidate']
    return render_template('admin_candidates.html', active='candidates', users=candidate_list)

@app.route('/admin/assessments')
def admin_assessments():
    return render_template('admin_assessments.html', active='assessments', assessments=assessments)

@app.route('/admin/results')
def admin_results():
    return render_template('admin_results.html', active='results')

@app.route('/admin/reports')
def admin_reports():
    return render_template('admin_reports.html', active='reports')

@app.route('/admin/security')
def admin_security():
    return render_template('admin_security.html', active='security')

@app.route('/admin/settings')
def admin_settings():
    return render_template('admin_settings.html', active='settings')

# placeholders for user/assessment management links on overview
@app.route('/admin/users/add', methods=['GET', 'POST'])
def add_user():
    global next_user_id
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'Candidate')
        is_active = bool(request.form.get('is_active'))
        new_user = {
            'id': next_user_id,
            'get_full_name': full_name,
            'email': email,
            'password': password,
            'is_active': is_active,
            'role': role,
            'last_login': None,
        }
        users.append(new_user)
        next_user_id += 1
        save_to_file('users.json', users)
        flash(f'User "{full_name}" added successfully.', 'success')
        return redirect(url_for('admin_overview'))

    return render_template('user_form.html', action='add', user={})

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_overview'))

    if request.method == 'POST':
        user['get_full_name'] = request.form.get('full_name', '').strip()
        user['email'] = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        if password:  # Only update password if a new one is provided
            user['password'] = password
        user['role'] = request.form.get('role', user['role'])
        user['is_active'] = bool(request.form.get('is_active'))
        save_to_file('users.json', users)
        flash(f'User "{user["get_full_name"]}" updated successfully.', 'success')
        return redirect(url_for('admin_overview'))

    return render_template('user_form.html', action='edit', user=user)

@app.route('/admin/assessments/create', methods=['GET', 'POST'])
def create_assessment():
    global next_assessment_id
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        duration = int(request.form.get('duration', '0') or 0)
        passing_score = int(request.form.get('passing_score', '0') or 0)
        question_count = int(request.form.get('question_count', '0') or 0)
        is_published = bool(request.form.get('is_published'))

        new_assessment = {
            'id': next_assessment_id,
            'title': title,
            'description': description,
            'duration': duration,
            'passing_score': passing_score,
            'question_count': question_count,
            'is_published': is_published,
            'attempt_count': 0,
            'assigned': 0,
        }
        assessments.append(new_assessment)
        next_assessment_id += 1
        save_to_file('assessments.json', assessments)

        flash(f'Assessment "{title}" created successfully.', 'success')
        return redirect(url_for('admin_assessments'))

    return render_template('assessment_form.html', action='create', assessment={})

@app.route('/admin/assessments/<int:assessment_id>/edit', methods=['GET', 'POST'])
def edit_assessment(assessment_id):
    assessment = next((a for a in assessments if a['id'] == assessment_id), None)
    if not assessment:
        flash('Assessment not found.', 'danger')
        return redirect(url_for('admin_assessments'))

    if request.method == 'POST':
        assessment['title'] = request.form.get('title', '').strip()
        assessment['description'] = request.form.get('description', '').strip()
        assessment['duration'] = int(request.form.get('duration', assessment.get('duration', 0)) or 0)
        assessment['passing_score'] = int(request.form.get('passing_score', assessment.get('passing_score', 0)) or 0)
        assessment['question_count'] = int(request.form.get('question_count', assessment.get('question_count', 0)) or 0)
        assessment['is_published'] = bool(request.form.get('is_published'))
        save_to_file('assessments.json', assessments)

        flash(f'Assessment "{assessment["title"]}" updated successfully.', 'success')
        return redirect(url_for('admin_assessments'))

    return render_template('assessment_form.html', action='edit', assessment=assessment)

@app.route('/candidate')
def candidate_dashboard():
    # Candidate dashboard
    return render_template('candidate_dashboard.html', active='dashboard')

# candidate area sub-pages
@app.route('/candidate/assessments')
def candidate_assessments():
    return render_template('candidate_assessments.html', active='assessments')

@app.route('/candidate/results')
def candidate_results():
    return render_template('candidate_results.html', active='results')

@app.route('/candidate/notifications')
def candidate_notifications():
    return render_template('candidate_notifications.html', active='notifications')

@app.route('/candidate/profile')
def candidate_profile():
    return render_template('candidate_profile.html', active='profile')

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    # remove the user from the existing list so references stay valid
    user = next((u for u in users if u['id'] == user_id), None)
    if user:
        users.remove(user)
        save_to_file('users.json', users)
        flash(f'User "{user.get("get_full_name")}" removed.', 'warning')
    else:
        flash('User not found.', 'danger')
    return redirect(url_for('admin_overview'))

@app.route('/logout')
def logout():
    # placeholder; in a real app clear session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

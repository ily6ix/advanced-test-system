from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
# secret key for session/flash messages; in production use an environment variable
app.secret_key = 'replace-with-secure-random'

# in-memory templates for initial data; session will hold the working copy
initial_assessments = [
    {
        'id': 1,
        'title': 'Intro to Python',
        'description': 'A basic assessment covering Python fundamentals.',
        'duration': 60,  # minutes
        'passing_score': 70,
        'question_count': 25,
        'is_published': True,
        'attempt_count': 34,
        'assigned': 120,
    },
    {
        'id': 2,
        'title': 'Advanced SQL',
        'description': 'Query optimization and complex joins.',
        'duration': 45,
        'passing_score': 80,
        'question_count': 20,
        'is_published': False,
        'attempt_count': 12,
        'assigned': 0,
    },
]

# simple helper to allocate new ids
initial_next_assessment_id = 3

# In-memory store for users (initial seed)
from datetime import datetime
initial_users = [
    {
        'id': 1,
        'get_full_name': 'Alice Johnson',
        'email': 'alice@example.com',
        'is_active': True,
        'role': 'Administrator',
        'last_login': datetime(2025, 2, 10),
    },
    {
        'id': 2,
        'get_full_name': 'Bob Lee',
        'email': 'bob@example.com',
        'is_active': False,
        'role': 'Manager',
        'last_login': datetime(2025, 1, 22),
    },
]
initial_next_user_id = 3

# In-memory store for users
from datetime import datetime

users = [
    {
        'id': 1,
        'get_full_name': 'Alice Johnson',
        'email': 'alice@example.com',
        'is_active': True,
        'role': 'Administrator',
        'last_login': datetime(2025, 2, 10),
    },
    {
        'id': 2,
        'get_full_name': 'Bob Lee',
        'email': 'bob@example.com',
        'is_active': False,
        'role': 'Manager',
        'last_login': datetime(2025, 1, 22),
    },
]
next_user_id = 3

# helpers for session-backed state

def ensure_session_data():
    """Populate session with default lists if not already present."""
    if 'assessments' not in session:
        session['assessments'] = initial_assessments.copy()
        session['next_assessment_id'] = initial_next_assessment_id
    if 'users' not in session:
        # strip datetime to isoformat for serialization
        users_copy = []
        for u in initial_users:
            uc = u.copy()
            if isinstance(uc.get('last_login'), datetime):
                uc['last_login'] = uc['last_login'].isoformat()
            users_copy.append(uc)
        session['users'] = users_copy
        session['next_user_id'] = initial_next_user_id


def get_session_assessments():
    ensure_session_data()
    return session['assessments']


def save_session_assessments(list_obj):
    session['assessments'] = list_obj
    # update id counter if modified
    session['next_assessment_id'] = session.get('next_assessment_id', initial_next_assessment_id)


def get_session_users():
    ensure_session_data()
    # convert isoformat back to datetime for last_login if needed
    us = []
    for u in session['users']:
        uc = u.copy()
        if uc.get('last_login'):
            try:
                uc['last_login'] = datetime.fromisoformat(uc['last_login'])
            except Exception:
                pass
        us.append(uc)
    return us


def save_session_users(list_obj):
    # convert datetimes to isoformat for storage
    us = []
    for u in list_obj:
        uc = u.copy()
        if isinstance(uc.get('last_login'), datetime):
            uc['last_login'] = uc['last_login'].isoformat()
        us.append(uc)
    session['users'] = us
    session['next_user_id'] = session.get('next_user_id', initial_next_user_id)

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
    # calculate stats from session-backed store
    current_users = get_session_users()
    current_assessments = get_session_assessments()
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
    current_users = get_session_users()
    candidate_list = [u for u in current_users if u['role'] == 'Candidate']
    return render_template('admin_candidates.html', active='candidates', users=candidate_list)

@app.route('/admin/assessments')
def admin_assessments():
    current_assessments = get_session_assessments()
    return render_template('admin_assessments.html', active='assessments', assessments=current_assessments)

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
        role = request.form.get('role', 'Candidate')
        is_active = bool(request.form.get('is_active'))
        new_user = {
            'id': next_user_id,
            'get_full_name': full_name,
            'email': email,
            'is_active': is_active,
            'role': role,
            'last_login': None,
        }
        users.append(new_user)
        next_user_id += 1
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
        user['role'] = request.form.get('role', user['role'])
        user['is_active'] = bool(request.form.get('is_active'))
        flash(f'User "{user["get_full_name"]}" updated successfully.', 'success')
        return redirect(url_for('admin_overview'))

    return render_template('user_form.html', action='edit', user=user)

@app.route('/admin/assessments/create', methods=['GET', 'POST'])
def create_assessment():
    if request.method == 'POST':
        current_assessments = get_session_assessments()
        next_id = session.get('next_assessment_id', initial_next_assessment_id)
        # gather form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        duration = int(request.form.get('duration', '0') or 0)
        passing_score = int(request.form.get('passing_score', '0') or 0)
        question_count = int(request.form.get('question_count', '0') or 0)
        is_published = bool(request.form.get('is_published'))

        new_assessment = {
            'id': next_id,
            'title': title,
            'description': description,
            'duration': duration,
            'passing_score': passing_score,
            'question_count': question_count,
            'is_published': is_published,
            'attempt_count': 0,
            'assigned': 0,
        }
        current_assessments.append(new_assessment)
        session['next_assessment_id'] = next_id + 1
        save_session_assessments(current_assessments)

        flash(f'Assessment "{title}" created successfully.', 'success')
        return redirect(url_for('admin_assessments'))

    return render_template('assessment_form.html', action='create', assessment={})

@app.route('/admin/assessments/<int:assessment_id>/edit', methods=['GET', 'POST'])
def edit_assessment(assessment_id):
    current_assessments = get_session_assessments()
    assessment = next((a for a in current_assessments if a['id'] == assessment_id), None)
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
        save_session_assessments(current_assessments)

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

from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
# secret key for session/flash messages; in production use an environment variable
app.secret_key = 'replace-with-secure-random'

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
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        elif username == 'candidate' and password == '1234':
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
    # sample data that would normally be pulled from a database
    stats = {
        'total_candidates': 42,
        'active_assessments': 7,
        'completed_attempts': 123,
        'average_score': 85,
    }

    # example user list with attributes used in the template
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

    # example assessments list
    assessments = [
        {
            'id': 1,
            'title': 'Intro to Python',
            'is_published': True,
            'duration': 60,
            'attempt_count': 34,
        },
        {
            'id': 2,
            'title': 'Advanced SQL',
            'is_published': False,
            'duration': 45,
            'attempt_count': 12,
        },
    ]

    return render_template(
        'admin_overview.html',
        active='overview',
        users=users,
        assessments=assessments,
        **stats,
    )

@app.route('/admin/candidates')
def admin_candidates():
    return render_template('admin_candidates.html', active='candidates')

@app.route('/admin/assessments')
def admin_assessments():
    return render_template('admin_assessments.html', active='assessments')

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
@app.route('/admin/users/add')
def add_user():
    # in a real app you'd show a form
    flash('Add user page not implemented yet.', 'info')
    return redirect(url_for('admin_overview'))

@app.route('/admin/users/<int:user_id>/edit')
def edit_user(user_id):
    flash(f'Edit user {user_id} page not implemented yet.', 'info')
    return redirect(url_for('admin_overview'))

@app.route('/admin/assessments/create')
def create_assessment():
    flash('Create assessment page not implemented yet.', 'info')
    return redirect(url_for('admin_overview'))

@app.route('/admin/assessments/<int:assessment_id>/edit')
def edit_assessment(assessment_id):
    flash(f'Edit assessment {assessment_id} page not implemented yet.', 'info')
    return redirect(url_for('admin_overview'))

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

@app.route('/logout')
def logout():
    # placeholder; in a real app clear session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

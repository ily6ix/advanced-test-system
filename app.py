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
    return render_template('admin_overview.html', active='overview')

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

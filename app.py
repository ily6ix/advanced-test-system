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
    # Admin / client dashboard
    return render_template('dashboard.html')

@app.route('/candidate')
def candidate_dashboard():
    # Simple dashboard for candidates
    return render_template('candidate_dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)

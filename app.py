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

# Migrate old assessment format to new format
for assessment in assessments:
    if 'assigned_to' not in assessment:
        assessment['assigned_to'] = []
    if 'results' not in assessment:
        assessment['results'] = []
    if 'questions' not in assessment:
        assessment['questions'] = []
    # Remove old fields for consistency
    assessment.pop('attempt_count', None)
    assessment.pop('assigned', None)
    assessment.pop('question_count', None)

next_assessment_id = max((a.get('id', 0) for a in assessments), default=0) + 1


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        
        # Find user by email
        user = next((u for u in users if u['email'] == email), None)
        
        if user and user['password'] == password:
            # Check if user is active
            if not user['is_active']:
                flash('Your account is inactive. Contact an administrator.', 'danger')
            else:
                # Update last login
                user['last_login'] = datetime.now()
                save_to_file('users.json', users)
                
                # Set session
                session['logged_in'] = True
                session['user_id'] = user['id']
                session['email'] = user['email']
                session['role'] = user['role']
                session['name'] = user['get_full_name']
                flash('Login successful', 'success')
                
                # Redirect based on role
                if user['role'] == 'Administrator':
                    return redirect(url_for('admin_overview'))
                else:
                    return redirect(url_for('candidate_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    # Admin overview page (previously dashboard)
    return redirect(url_for('admin_overview'))

# admin area pages
@app.route('/admin')
def admin_overview():
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    
    # calculate stats from file-backed store
    current_users = users
    current_assessments = assessments
    
    # Calculate stats from actual results
    all_results = []
    for assessment in current_assessments:
        all_results.extend(assessment.get('results', []))
    
    completed_results = [r for r in all_results if r.get('status') == 'completed']
    completed_scores = [r['score_percentage'] for r in completed_results if r.get('score_percentage') is not None]
    average_score = (sum(completed_scores) // len(completed_scores)) if completed_scores else 0
    
    stats = {
        'total_candidates': len([u for u in current_users if u['role'] == 'Candidate']),
        'active_assessments': len([a for a in current_assessments if a.get('is_published')]),
        'completed_attempts': len(completed_results),
        'average_score': average_score,
    }

    overview_assessments = [
        {
            'id': a['id'],
            'title': a['title'],
            'is_published': a.get('is_published'),
            'duration': a.get('duration'),
            'attempt_count': len([r for r in a.get('results', []) if r.get('status') == 'completed']),
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
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    candidate_list = [u for u in users if u['role'] == 'Candidate']
    return render_template('admin_candidates.html', active='candidates', users=candidate_list)

@app.route('/admin/assessments')
def admin_assessments():
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    return render_template('admin_assessments.html', active='assessments', assessments=assessments)

@app.route('/admin/results')
def admin_results():
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    # provide assessments and users to the template so grading links can be rendered
    return render_template('admin_results.html', active='results', assessments=assessments, users=users)

@app.route('/admin/reports')
def admin_reports():
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    return render_template('admin_reports.html', active='reports')

@app.route('/admin/security')
def admin_security():
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    return render_template('admin_security.html', active='security')

@app.route('/admin/settings')
def admin_settings():
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    return render_template('admin_settings.html', active='settings')

# placeholders for user/assessment management links on overview
@app.route('/admin/users/add', methods=['GET', 'POST'])
def add_user():
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    
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
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    
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
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    
    global next_assessment_id
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        duration = int(request.form.get('duration', '0') or 0)
        passing_score = int(request.form.get('passing_score', '0') or 0)
        is_published = bool(request.form.get('is_published'))

        new_assessment = {
            'id': next_assessment_id,
            'title': title,
            'description': description,
            'duration': duration,
            'passing_score': passing_score,
            'is_published': is_published,
            'assigned_to': [],
            'questions': [],
            'results': [],
        }
        assessments.append(new_assessment)
        next_assessment_id += 1
        save_to_file('assessments.json', assessments)

        flash(f'Assessment "{title}" created successfully.', 'success')
        return redirect(url_for('admin_assessments'))

    return render_template('assessment_form.html', action='create', assessment={})

@app.route('/admin/assessments/<int:assessment_id>/edit', methods=['GET', 'POST'])
def edit_assessment(assessment_id):
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    
    assessment = next((a for a in assessments if a['id'] == assessment_id), None)
    if not assessment:
        flash('Assessment not found.', 'danger')
        return redirect(url_for('admin_assessments'))

    if request.method == 'POST':
        assessment['title'] = request.form.get('title', '').strip()
        assessment['description'] = request.form.get('description', '').strip()
        assessment['duration'] = int(request.form.get('duration', assessment.get('duration', 0)) or 0)
        assessment['passing_score'] = int(request.form.get('passing_score', assessment.get('passing_score', 0)) or 0)
        assessment['is_published'] = bool(request.form.get('is_published'))
        
        # Ensure required fields exist
        if 'assigned_to' not in assessment:
            assessment['assigned_to'] = []
        if 'results' not in assessment:
            assessment['results'] = []
        if 'questions' not in assessment:
            assessment['questions'] = []
        
        save_to_file('assessments.json', assessments)

        flash(f'Assessment "{assessment["title"]}" updated successfully.', 'success')
        return redirect(url_for('admin_assessments'))

    return render_template('assessment_form.html', action='edit', assessment=assessment)

# Helper function to check login
def require_login(required_role=None):
    if not session.get('logged_in'):
        flash('Please log in first.', 'danger')
        return False
    if required_role and session.get('role') != required_role:
        flash('You do not have permission to access this page.', 'danger')
        return False
    return True


def get_candidate_assessments(candidate_id):
    """Get assessments assigned to a candidate with their results"""
    candidate_assessments = []
    for assessment in assessments:
        if candidate_id in assessment.get('assigned_to', []):
            # Find the result for this candidate
            result = next(
                (r for r in assessment.get('results', []) if r['candidate_id'] == candidate_id),
                None
            )
            candidate_assessments.append({
                'assessment': assessment,
                'result': result or {'status': 'not_assigned', 'score': None, 'passed': None}
            })
    return candidate_assessments


def calculate_candidate_stats(candidate_id):
    """Calculate statistics for a candidate based on their assessment results"""
    cand_assessments = get_candidate_assessments(candidate_id)
    
    completed = sum(1 for ca in cand_assessments if ca['result'].get('status') == 'completed')
    pending = sum(1 for ca in cand_assessments if ca['result'].get('status') in ['not_started', 'in_progress'])
    
    scores = [ca['result']['score_percentage'] for ca in cand_assessments if ca['result'].get('score_percentage') is not None]
    average_score = int(sum(scores) / len(scores)) if scores else 0
    
    # Find the nearest due date
    next_due = None
    for ca in cand_assessments:
        if ca['result'].get('status') != 'completed' and ca['result'].get('due_date'):
            due = datetime.fromisoformat(ca['result']['due_date'])
            if next_due is None or due < next_due:
                next_due = due
    
    return {
        'completed': completed,
        'pending': pending,
        'average_score': average_score,
        'next_due': next_due.strftime('%d %b %Y') if next_due else 'N/A'
    }


@app.route('/candidate')
def candidate_dashboard():
    if not require_login('Candidate'):
        return redirect(url_for('login'))
    
    candidate_id = session.get('user_id')
    candidate_name = session.get('name')
    
    # Get candidate's assessments
    cand_assessments = get_candidate_assessments(candidate_id)
    
    # Calculate stats
    stats = calculate_candidate_stats(candidate_id)
    
    return render_template(
        'candidate_dashboard.html',
        active='dashboard',
        candidate_name=candidate_name,
        candidate_assessments=cand_assessments,
        **stats
    )


# candidate area sub-pages
@app.route('/candidate/assessments')
def candidate_assessments():
    if not require_login('Candidate'):
        return redirect(url_for('login'))
    
    candidate_id = session.get('user_id')
    cand_assessments = get_candidate_assessments(candidate_id)
    
    return render_template(
        'candidate_assessments.html',
        active='assessments',
        candidate_assessments=cand_assessments
    )


@app.route('/candidate/results')
def candidate_results():
    if not require_login('Candidate'):
        return redirect(url_for('login'))
    
    candidate_id = session.get('user_id')
    cand_assessments = get_candidate_assessments(candidate_id)
    
    # Filter only completed assessments
    completed_assessments = [
        ca for ca in cand_assessments 
        if ca['result'].get('status') == 'completed'
    ]
    
    return render_template(
        'candidate_results.html',
        active='results',
        completed_assessments=completed_assessments
    )


@app.route('/candidate/notifications')
def candidate_notifications():
    if not require_login('Candidate'):
        return redirect(url_for('login'))
    
    candidate_id = session.get('user_id')
    cand_assessments = get_candidate_assessments(candidate_id)
    
    # Generate notifications: upcoming deadlines, pending assessments, etc.
    notifications = []
    
    for ca in cand_assessments:
        if ca['result'].get('status') == 'not_started' and ca['result'].get('due_date'):
            notifications.append({
                'type': 'pending',
                'message': f"You have a pending assessment: {ca['assessment']['title']}",
                'date': ca['result']['due_date']
            })
        elif ca['result'].get('status') == 'in_progress':
            notifications.append({
                'type': 'in_progress',
                'message': f"Resume your assessment: {ca['assessment']['title']}",
                'date': ca['result']['due_date']
            })
    
    return render_template(
        'candidate_notifications.html',
        active='notifications',
        notifications=notifications
    )


@app.route('/candidate/profile', methods=['GET', 'POST'])
def candidate_profile():
    if not require_login('Candidate'):
        return redirect(url_for('login'))
    
    candidate_id = session.get('user_id')
    candidate = next((u for u in users if u['id'] == candidate_id), None)
    
    if not candidate:
        flash('Candidate not found.', 'danger')
        return redirect(url_for('candidate_dashboard'))
    
    if request.method == 'POST':
        # Update candidate profile
        candidate['get_full_name'] = request.form.get('full_name', '').strip()
        candidate['email'] = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if password:
            candidate['password'] = password
        
        save_to_file('users.json', users)
        
        # Update session
        session['name'] = candidate['get_full_name']
        session['email'] = candidate['email']
        
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('candidate_profile'))
    
    return render_template(
        'candidate_profile.html',
        active='profile',
        candidate=candidate
    )

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    
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
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# Assessment Question Management Routes
@app.route('/admin/assessments/<int:assessment_id>/questions', methods=['GET', 'POST'])
def manage_questions(assessment_id):
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    
    assessment = next((a for a in assessments if a['id'] == assessment_id), None)
    if not assessment:
        flash('Assessment not found.', 'danger')
        return redirect(url_for('admin_assessments'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            question_text = request.form.get('question_text', '').strip()
            question_type = request.form.get('question_type', 'multiple_choice')
            points = int(request.form.get('points', '10') or 10)
            
            new_question = {
                'id': max([q.get('id', 0) for q in assessment.get('questions', [])], default=0) + 1,
                'text': question_text,
                'type': question_type,
                'points': points,
            }
            
            if question_type == 'multiple_choice':
                options = [opt.strip() for opt in request.form.get('options', '').split('\n') if opt.strip()]
                correct_answer = int(request.form.get('correct_answer', '0') or 0)
                new_question['options'] = options
                new_question['correct_answer'] = correct_answer
            
            assessment['questions'].append(new_question)
            save_to_file('assessments.json', assessments)
            flash('Question added successfully.', 'success')
        
        elif action == 'delete':
            question_id = int(request.form.get('question_id'))
            assessment['questions'] = [q for q in assessment.get('questions', []) if q['id'] != question_id]
            save_to_file('assessments.json', assessments)
            flash('Question deleted successfully.', 'danger')
        
        return redirect(url_for('manage_questions', assessment_id=assessment_id))
    
    return render_template('manage_questions.html', assessment=assessment)


@app.route('/candidate/assessments/<int:assessment_id>/take', methods=['GET', 'POST'])
def take_assessment(assessment_id):
    if not require_login('Candidate'):
        return redirect(url_for('login'))
    
    candidate_id = session.get('user_id')
    assessment = next((a for a in assessments if a['id'] == assessment_id), None)
    
    if not assessment:
        flash('Assessment not found.', 'danger')
        return redirect(url_for('candidate_assessments'))
    
    if candidate_id not in assessment.get('assigned_to', []):
        flash('This assessment is not assigned to you.', 'danger')
        return redirect(url_for('candidate_assessments'))
    
    # Find or create result for this candidate
    result = next(
        (r for r in assessment.get('results', []) if r['candidate_id'] == candidate_id),
        None
    )
    
    # If no result exists, create one on first access
    if not result:
        result = {
            'candidate_id': candidate_id,
            'status': 'not_started',
            'answers': [],
            'submitted_date': None,
            'graded_date': None,
            'score_percentage': None,
            'allocated_points': None,
            'passed': None,
            'time_spent': 0,
            'due_date': None
        }
        assessment.get('results', []).append(result)
        save_to_file('assessments.json', assessments)
    
    # If assessment is already completed, show results instead
    if result.get('status') == 'completed':
        return render_template('assessment_results.html', assessment=assessment, result=result)
    
    # Handle GET request - show assessment rules
    if request.method == 'GET':
        return render_template('assessment_rules.html', assessment=assessment)
    
    # Handle POST requests
    action = request.form.get('action')
    
    if action == 'abort':
        flash('Assessment cancelled.', 'info')
        return redirect(url_for('candidate_assessments'))
    
    if action == 'start':
        # User clicked "Start Assessment" - mark as in_progress and show the assessment form
        result['status'] = 'in_progress'
        result['start_date'] = datetime.now().isoformat()
        save_to_file('assessments.json', assessments)
        return render_template('take_assessment.html', assessment=assessment, result=result)
    
    # Otherwise, process submitted answers
    if result.get('status') == 'submitted':
        flash('This assessment has already been submitted.', 'warning')
        return redirect(url_for('candidate_assessments'))
    
    # Collect answers
    answers = []
    for question in assessment.get('questions', []):
        question_id = question['id']
        answer_key = f'question_{question_id}'
        candidate_answer = request.form.get(answer_key)
        
        if candidate_answer is not None:
            answers.append({
                'question_id': question_id,
                'candidate_answer': candidate_answer,
                'allocated_points': None,
                'graded': False
            })
    
    # Update result
    result['answers'] = answers
    result['status'] = 'submitted'
    result['submitted_date'] = datetime.now().isoformat()
    result['time_spent'] = int(request.form.get('time_spent', '0') or 0)
    
    save_to_file('assessments.json', assessments)
    flash('Assessment submitted successfully. Waiting for admin to grade.', 'success')
    return redirect(url_for('candidate_assessments'))


@app.route('/admin/assessments/<int:assessment_id>/grade/<int:candidate_id>', methods=['GET', 'POST'])
def grade_assessment(assessment_id, candidate_id):
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    
    assessment = next((a for a in assessments if a['id'] == assessment_id), None)
    if not assessment:
        flash('Assessment not found.', 'danger')
        return redirect(url_for('admin_assessments'))
    
    result = next(
        (r for r in assessment.get('results', []) if r['candidate_id'] == candidate_id),
        None
    )
    if not result:
        flash('Assessment result not found.', 'danger')
        return redirect(url_for('admin_assessments'))
    
    candidate = next((u for u in users if u['id'] == candidate_id), None)
    
    if request.method == 'POST':
        # Update allocated points
        for answer in result.get('answers', []):
            points_key = f'points_{answer["question_id"]}'
            allocated_points = request.form.get(points_key)
            if allocated_points:
                answer['allocated_points'] = int(allocated_points)
                answer['graded'] = True
        
        # Calculate total score
        total_points = sum(a.get('allocated_points', 0) for a in result.get('answers', []) if a.get('allocated_points') is not None)
        max_points = sum(q.get('points', 10) for q in assessment.get('questions', []))
        score_percentage = int((total_points / max_points * 100)) if max_points > 0 else 0
        
        result['total_score'] = total_points
        result['score_percentage'] = score_percentage
        result['passed'] = score_percentage >= assessment.get('passing_score', 70)
        result['status'] = 'completed'
        result['graded_by_admin'] = session.get('user_id')
        result['graded_date'] = datetime.now().isoformat()
        
        save_to_file('assessments.json', assessments)
        flash('Assessment graded successfully.', 'success')
        return redirect(url_for('admin_results'))
    
    return render_template('grade_assessment.html', 
                         assessment=assessment, 
                         result=result, 
                         candidate=candidate)


if __name__ == '__main__':
    app.run(debug=True)

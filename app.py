from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import json
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)
# secret key for session/flash messages; in production use an environment variable
app.secret_key = 'replace-with-secure-random'

# --- email helper ---
def send_verification_email(email, code):
    """Send verification code to email. In production, configure SMTP."""
    subject = "Your Verification Code - Advanced Test System"
    body = f"Your verification code is: {code}\n\nPlease enter this code to complete your registration."
    
    # For development, just print the code
    print(f"Verification code for {email}: {code}")
    
    # In production, uncomment and configure:
    # msg = MIMEText(body)
    # msg['Subject'] = subject
    # msg['From'] = 'noreply@yourdomain.com'
    # msg['To'] = email
    # 
    # with smtplib.SMTP('smtp.yourdomain.com', 587) as server:
    #     server.starttls()
    #     server.login('your_email@yourdomain.com', 'password')
    #     server.sendmail(msg['From'], [msg['To']], msg.as_string())
    
    return True  # Indicate success

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

# Load notifications
notifications = load_from_file('notifications.json', [])

groups = load_from_file('groups.json', [])

next_group_id = max((g.get('id', 0) for g in groups), default=0) + 1

# Migrate old assessment format to new format
for assessment in assessments:
    if 'assigned_to' not in assessment:
        assessment['assigned_to'] = []
    if 'results' not in assessment:
        assessment['results'] = []
    if 'questions' not in assessment:
        assessment['questions'] = []
    # new permission fields
    if 'allow_back_navigation' not in assessment:
        assessment['allow_back_navigation'] = True
    if 'per_question_timer' not in assessment:
        assessment['per_question_timer'] = False
    if 'allow_face_tracking' not in assessment:
        assessment['allow_face_tracking'] = True
    if 'allow_voice_tracking' not in assessment:
        assessment['allow_voice_tracking'] = False
    if 'max_attempts' not in assessment:
        assessment['max_attempts'] = 1
    # Ensure proctoring counts exist
    if 'face_warnings' not in assessment:
        # not stored at assessment level; but ensure results later
        pass
    # Remove old fields for consistency
    assessment.pop('attempt_count', None)
    assessment.pop('assigned', None)
    assessment.pop('question_count', None)

next_assessment_id = max((a.get('id', 0) for a in assessments), default=0) + 1


# ============= NOTIFICATION HELPERS =============

def create_notification(notification_type, user_id, title, message, related_assessment_id=None, related_candidate_id=None):
    """
    Create a notification for a user.
    
    Types:
      - 'assessment_assigned': Test assigned to candidate
      - 'assessment_submitted': Test submitted by candidate (for admin)
      - 'assessment_graded': Test graded (for candidate)
    """
    notification = {
        'id': len(notifications) + 1,
        'type': notification_type,
        'user_id': user_id,
        'title': title,
        'message': message,
        'created_at': datetime.now().isoformat(),
        'read': False,
        'related_assessment_id': related_assessment_id,
        'related_candidate_id': related_candidate_id,
    }
    notifications.append(notification)
    save_to_file('notifications.json', notifications)
    return notification


def get_user_notifications(user_id, unread_only=False):
    """Get notifications for a specific user."""
    user_notifs = [n for n in notifications if n['user_id'] == user_id]
    if unread_only:
        user_notifs = [n for n in user_notifs if not n.get('read')]
    # Sort by created_at descending
    return sorted(user_notifs, key=lambda x: x['created_at'], reverse=True)


def mark_notification_read(notification_id):
    """Mark a notification as read."""
    notif = next((n for n in notifications if n['id'] == notification_id), None)
    if notif:
        notif['read'] = True
        save_to_file('notifications.json', notifications)
        return True
    return False


def delete_notification(notification_id):
    """Delete a notification."""
    global notifications
    notifications = [n for n in notifications if n['id'] != notification_id]
    save_to_file('notifications.json', notifications)


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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        step = request.form.get('step', '1')
        
        if step == '1':
            # Step 1: Collect info and send code
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            
            # Validation
            if not full_name or not email or not password:
                flash('All fields are required.', 'danger')
                return render_template('register.html', step=1)
            
            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('register.html', step=1)
            
            # Check if email already exists
            if any(u['email'] == email for u in users):
                flash('Email already registered.', 'danger')
                return render_template('register.html', step=1)
            
            # Generate verification code
            code = str(random.randint(100000, 999999))
            
            # Send email
            send_verification_email(email, code)
            
            # Store in session
            session['reg_full_name'] = full_name
            session['reg_email'] = email
            session['reg_password'] = password
            session['reg_code'] = code
            
            # For development: show code in flash message
            flash(f'Verification code sent to your email. For development testing, your code is: {code}', 'info')
            return render_template('register.html', step=2, email=email)
        
        elif step == '2':
            # Step 2: Verify code and create user
            entered_code = request.form.get('code', '').strip()
            stored_code = session.get('reg_code')
            
            if not entered_code or entered_code != stored_code:
                flash('Invalid verification code.', 'danger')
                return render_template('register.html', step=2, email=session.get('reg_email'))
            
            # Create user
            global next_user_id
            new_user = {
                'id': next_user_id,
                'get_full_name': session['reg_full_name'],
                'email': session['reg_email'],
                'password': session['reg_password'],
                'is_active': True,
                'role': 'Candidate',
                'last_login': None,
            }
            users.append(new_user)
            next_user_id += 1
            save_to_file('users.json', users)
            
            # Clear session
            session.pop('reg_full_name', None)
            session.pop('reg_email', None)
            session.pop('reg_password', None)
            session.pop('reg_code', None)
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
    
    # GET request
    step = request.args.get('step', '1')
    return render_template('register.html', step=step)

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

@app.route('/admin/users')
def admin_users():
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    user_list = users  # all users
    return render_template('admin_users.html', active='users', users=user_list, groups=groups)

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
    # supply lists for filtering controls
    candidate_users = [u for u in users if u['role'] == 'Candidate']
    # compute summary statistics across all results
    total_results = 0
    passed = 0
    failed = 0
    scores = []
    total_violations = 0
    highest = None
    lowest = None
    for a in assessments:
        for r in a.get('results', []):
            if r.get('status') == 'completed' and r.get('score_percentage') is not None:
                total_results += 1
                scores.append(r['score_percentage'])
                if r['score_percentage'] >= a.get('passing_score', 0):
                    passed += 1
                else:
                    failed += 1
                v = (r.get('face_warnings', 0) or 0) + (r.get('voice_warnings', 0) or 0)
                total_violations += v
                if highest is None or r['score_percentage'] > highest:
                    highest = r['score_percentage']
                if lowest is None or r['score_percentage'] < lowest:
                    lowest = r['score_percentage']
    avg_score = int(sum(scores)/len(scores)) if scores else 0
    summary = {
        'total_results': total_results,
        'passed': passed,
        'failed': failed,
        'average_score': avg_score,
        'highest': highest if highest is not None else 0,
        'lowest': lowest if lowest is not None else 0,
        'total_violations': total_violations,
    }
    return render_template(
        'admin_reports.html',
        active='reports',
        assessments=assessments,
        candidates=candidate_users,
        summary=summary
    )


@app.route('/admin/reports/export', methods=['POST'])
def export_reports():
    if not require_login('Administrator'):
        return redirect(url_for('login'))

    # gather filters
    aid = request.form.get('assessment_id')
    cid = request.form.get('candidate_id')
    start = request.form.get('start_date')
    end = request.form.get('end_date')
    min_w = request.form.get('min_warnings')
    fmt = request.form.get('format', 'csv')

    # convert
    aid = int(aid) if aid else None
    cid = int(cid) if cid else None
    min_w = int(min_w) if min_w else 0

    # build data rows
    rows = []
    for a in assessments:
        if aid and a['id'] != aid:
            continue
        for r in a.get('results', []):
            if cid and r['candidate_id'] != cid:
                continue
            # parse submitted date for range filtering
            if r.get('submitted_date') and (start or end):
                try:
                    dt = datetime.fromisoformat(r['submitted_date'])
                except Exception:
                    dt = None
                if dt and start and dt.date() < datetime.fromisoformat(start).date():
                    continue
                if dt and end and dt.date() > datetime.fromisoformat(end).date():
                    continue
            total_warn = (r.get('face_warnings', 0) or 0) + (r.get('voice_warnings', 0) or 0)
            if total_warn < min_w:
                continue
            cand = next((u for u in users if u['id'] == r['candidate_id']), None)
            rows.append({
                'assessment': a['title'],
                'candidate': cand['get_full_name'] if cand else 'Unknown',
                'score': r.get('score_percentage'),
                'submitted': r.get('submitted_date'),
                'face_warnings': r.get('face_warnings', 0),
                'voice_warnings': r.get('voice_warnings', 0),
            })

    # generate export content
    if fmt == 'csv':
        import csv, io
        si = io.StringIO()
        writer = csv.DictWriter(si, fieldnames=['assessment','candidate','score','submitted','face_warnings','voice_warnings'])
        writer.writeheader()
        writer.writerows(rows)
        content = si.getvalue()
        resp = app.response_class(content, mimetype='text/csv')
        resp.headers['Content-Disposition'] = 'attachment; filename=report.csv'
        return resp
    elif fmt == 'pdf':
        text = 'Assessment Report\n' + '\n'.join(str(r) for r in rows)
        resp = app.response_class(text, mimetype='application/pdf')
        resp.headers['Content-Disposition'] = 'attachment; filename=report.pdf'
        return resp
    else:  # doc
        text = 'Assessment Report\n' + '\n'.join(str(r) for r in rows)
        resp = app.response_class(text, mimetype='application/msword')
        resp.headers['Content-Disposition'] = 'attachment; filename=report.doc'
        return resp

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


# ============= ADMIN NOTIFICATION ROUTES =============

@app.route('/admin/notifications')
def admin_notifications():
    """Admin notifications page"""
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    
    admin_id = session.get('user_id')
    user_notifs = get_user_notifications(admin_id)
    unread_count = len([n for n in user_notifs if not n.get('read')])
    
    return render_template(
        'admin_notifications.html',
        active='notifications',
        notifications=user_notifs,
        unread_count=unread_count
    )


@app.route('/admin/notifications/<int:notification_id>/read', methods=['POST'])
def mark_notification_read_route(notification_id):
    """Mark a notification as read"""
    if not require_login('Administrator'):
        return {'error': 'not logged in'}, 403
    
    success = mark_notification_read(notification_id)
    return {'success': success}, 200 if success else 404


@app.route('/admin/notifications/<int:notification_id>', methods=['DELETE'])
def delete_notification_route(notification_id):
    """Delete a notification"""
    if not require_login('Administrator'):
        return {'error': 'not logged in'}, 403
    
    delete_notification(notification_id)
    return {'success': True}, 200


@app.route('/admin/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    """Mark all notifications as read for the admin"""
    if not require_login('Administrator'):
        return {'error': 'not logged in'}, 403
    
    admin_id = session.get('user_id')
    for notif in get_user_notifications(admin_id):
        mark_notification_read(notif['id'])
    
    return {'success': True}, 200


@app.route('/admin/notifications/clear-all', methods=['DELETE'])
def clear_all_notifications():
    """Delete all notifications for the admin"""
    if not require_login('Administrator'):
        return {'error': 'not logged in'}, 403
    
    global notifications
    admin_id = session.get('user_id')
    initial_count = len(notifications)
    notifications = [n for n in notifications if n['user_id'] != admin_id]
    save_to_file('notifications.json', notifications)
    
    return {'success': True, 'deleted': initial_count - len(notifications)}, 200


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

@app.route('/admin/groups/add', methods=['GET', 'POST'])
def add_group():
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    
    global next_group_id
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        members = [int(uid) for uid in request.form.getlist('members') if uid]
        new_group = {
            'id': next_group_id,
            'name': name,
            'description': description,
            'members': members,
        }
        groups.append(new_group)
        next_group_id += 1
        save_to_file('groups.json', groups)
        flash(f'Group "{name}" added successfully.', 'success')
        return redirect(url_for('admin_users'))
    candidate_users = [u for u in users if u['role'] == 'Candidate']
    return render_template('group_form.html', action='add', group={}, users=candidate_users)

@app.route('/admin/groups/<int:group_id>/edit', methods=['GET', 'POST'])
def edit_group(group_id):
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    
    group = next((g for g in groups if g['id'] == group_id), None)
    if not group:
        flash('Group not found.', 'danger')
        return redirect(url_for('admin_users'))
    if request.method == 'POST':
        group['name'] = request.form.get('name', '').strip()
        group['description'] = request.form.get('description', '').strip()
        group['members'] = [int(uid) for uid in request.form.getlist('members') if uid]
        save_to_file('groups.json', groups)
        flash(f'Group "{group["name"]}" updated successfully.', 'success')
        return redirect(url_for('admin_users'))
    candidate_users = [u for u in users if u['role'] == 'Candidate']
    return render_template('group_form.html', action='edit', group=group, users=candidate_users)

@app.route('/admin/groups/<int:group_id>/delete', methods=['POST'])
def delete_group(group_id):
    if not require_login('Administrator'):
        return redirect(url_for('login'))
    
    global groups
    group = next((g for g in groups if g['id'] == group_id), None)
    if group:
        groups = [g for g in groups if g['id'] != group_id]
        save_to_file('groups.json', groups)
        flash(f'Group "{group["name"]}" deleted successfully.', 'success')
    else:
        flash('Group not found.', 'danger')
    return redirect(url_for('admin_users'))

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
        max_attempts = int(request.form.get('max_attempts', '1') or 1)
        is_published = bool(request.form.get('is_published'))
        allow_back = bool(request.form.get('allow_back_navigation'))
        per_q_timer = bool(request.form.get('per_question_timer'))
        face_track = bool(request.form.get('allow_face_tracking'))
        voice_track = bool(request.form.get('allow_voice_tracking'))
        assigned = [int(uid) for uid in request.form.getlist('assigned_to') if uid]
        assigned_groups = [int(gid) for gid in request.form.getlist('assigned_groups') if gid]
        for gid in assigned_groups:
            group = next((g for g in groups if g['id'] == gid), None)
            if group:
                assigned.extend(group['members'])
        assigned = list(set(assigned))  # remove duplicates

        new_assessment = {
            'id': next_assessment_id,
            'title': title,
            'description': description,
            'duration': duration,
            'passing_score': passing_score,
            'max_attempts': max_attempts,
            'is_published': is_published,
            'allow_back_navigation': allow_back,
            'per_question_timer': per_q_timer,
            'allow_face_tracking': face_track,
            'allow_voice_tracking': voice_track,
            'assigned_to': assigned,
            'questions': [],
            'results': [],
        }
        assessments.append(new_assessment)
        next_assessment_id += 1
        save_to_file('assessments.json', assessments)
        
        # Send notifications to assigned candidates
        if assigned:
            for candidate_id in assigned:
                candidate = next((u for u in users if u['id'] == candidate_id), None)
                if candidate:
                    create_notification(
                        notification_type='assessment_assigned',
                        user_id=candidate_id,
                        title=f'New Assessment Assigned: {title}',
                        message=f'You have been assigned a new assessment: "{title}". Please review it in your dashboard.',
                        related_assessment_id=new_assessment['id']
                    )

        flash(f'Assessment "{title}" created successfully.', 'success')
        return redirect(url_for('admin_assessments'))

    # pass candidate list for assigning
    candidate_users = [u for u in users if u['role'] == 'Candidate']
    return render_template('assessment_form.html', action='create', assessment={}, users=candidate_users, groups=groups)

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
        assessment['max_attempts'] = int(request.form.get('max_attempts', assessment.get('max_attempts', 1)) or 1)
        assessment['is_published'] = bool(request.form.get('is_published'))
        assessment['allow_back_navigation'] = bool(request.form.get('allow_back_navigation'))
        assessment['per_question_timer'] = bool(request.form.get('per_question_timer'))
        assessment['allow_face_tracking'] = bool(request.form.get('allow_face_tracking'))
        assessment['allow_voice_tracking'] = bool(request.form.get('allow_voice_tracking'))
        
        # Track which candidates are newly assigned
        old_assigned = set(assessment.get('assigned_to', []))
        new_assigned = set([int(uid) for uid in request.form.getlist('assigned_to') if uid])
        assigned_groups = [int(gid) for gid in request.form.getlist('assigned_groups') if gid]
        for gid in assigned_groups:
            group = next((g for g in groups if g['id'] == gid), None)
            if group:
                new_assigned.update(group['members'])
        newly_assigned = new_assigned - old_assigned
        
        assessment['assigned_to'] = list(new_assigned)
        
        # Ensure required fields exist
        if 'assigned_to' not in assessment:
            assessment['assigned_to'] = []
        if 'results' not in assessment:
            assessment['results'] = []
        if 'questions' not in assessment:
            assessment['questions'] = []
        
        save_to_file('assessments.json', assessments)
        
        # Send notifications to newly assigned candidates
        for candidate_id in newly_assigned:
            candidate = next((u for u in users if u['id'] == candidate_id), None)
            if candidate:
                create_notification(
                    notification_type='assessment_assigned',
                    user_id=candidate_id,
                    title=f'New Assessment Assigned: {assessment["title"]}',
                    message=f'You have been assigned a new assessment: "{assessment["title"]}". Please review it in your dashboard.',
                    related_assessment_id=assessment_id
                )

        flash(f'Assessment "{assessment["title"]}" updated successfully.', 'success')
        return redirect(url_for('admin_assessments'))

    candidate_users = [u for u in users if u['role'] == 'Candidate']
    return render_template('assessment_form.html', action='edit', assessment=assessment, users=candidate_users, groups=groups)

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
            # Find all results for this candidate
            candidate_results = [r for r in assessment.get('results', []) if r['candidate_id'] == candidate_id]
            # Sort by submitted_date or start_date, latest first
            candidate_results.sort(key=lambda r: r.get('submitted_date') or r.get('start_date') or '', reverse=True)
            latest_result = candidate_results[0] if candidate_results else None
            candidate_assessments.append({
                'assessment': assessment,
                'result': latest_result or {'status': 'not_assigned', 'score': None, 'passed': None},
                'attempts_count': len([r for r in candidate_results if r.get('status') == 'completed'])
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
    
    # Get notifications from the system
    system_notifications = get_user_notifications(candidate_id)
    
    # Get assessment-related notifications
    cand_assessments = get_candidate_assessments(candidate_id)
    assessment_notifications = []
    
    for ca in cand_assessments:
        if ca['result'].get('status') == 'not_started' and ca['result'].get('due_date'):
            assessment_notifications.append({
                'type': 'pending',
                'title': f"Pending: {ca['assessment']['title']}",
                'message': f"You have a pending assessment: {ca['assessment']['title']}",
                'date': ca['result']['due_date'],
                'read': True,
                'source': 'assessment'
            })
        elif ca['result'].get('status') == 'in_progress':
            assessment_notifications.append({
                'type': 'in_progress',
                'title': f"In Progress: {ca['assessment']['title']}",
                'message': f"Resume your assessment: {ca['assessment']['title']}",
                'date': ca['result']['due_date'],
                'read': True,
                'source': 'assessment'
            })
    
    # Combine and sort all notifications
    all_notifications = []
    
    # Add system notifications
    for notif in system_notifications:
        all_notifications.append({
            'id': notif['id'],
            'type': notif['type'],
            'title': notif['title'],
            'message': notif['message'],
            'date': notif['created_at'],
            'read': notif.get('read', False),
            'source': 'system'
        })
    
    # Add assessment notifications
    all_notifications.extend(assessment_notifications)
    
    # Sort by date descending
    all_notifications = sorted(all_notifications, key=lambda x: x['date'], reverse=True)
    
    return render_template(
        'candidate_notifications.html',
        active='notifications',
        notifications=all_notifications
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
    # Clear all session data to fully log the user out
    session.clear()
    flash('You have been logged out.', 'info')
    # After logging out redirect to the landing page (index) rather than the
    # login form so the user ends up at the site front‑page.
    return redirect(url_for('index'))


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
    
    # Get all results for this candidate
    candidate_results = [r for r in assessment.get('results', []) if r['candidate_id'] == candidate_id]
    completed_count = len([r for r in candidate_results if r.get('status') == 'completed'])
    # Sort by submitted_date or start_date, latest first
    candidate_results.sort(key=lambda r: r.get('submitted_date') or r.get('start_date') or '', reverse=True)
    latest_result = candidate_results[0] if candidate_results else None
    
    # Check if can take the assessment
    can_retake = False
    if latest_result and latest_result.get('status') == 'completed':
        if latest_result.get('passed'):
            # Passed, can't retake
            pass
        elif completed_count >= assessment.get('max_attempts', 1):
            # No more attempts
            pass
        else:
            can_retake = True
    
    # Determine which result to use
    if can_retake:
        # Create new result for retake
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
            'due_date': None,
            'face_warnings': 0,
            'voice_warnings': 0,
            'cancelled': False
        }
        assessment.get('results', []).append(result)
        save_to_file('assessments.json', assessments)
    else:
        # Use existing latest result or create if none
        if not latest_result:
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
                'due_date': None,
                'face_warnings': 0,
                'voice_warnings': 0,
                'cancelled': False
            }
            assessment.get('results', []).append(result)
            save_to_file('assessments.json', assessments)
        else:
            result = latest_result
    
    # if assessment has been cancelled for rules violations, kick user back
    if result.get('status') == 'cancelled' or result.get('cancelled'):
        flash('This assessment has been cancelled due to rule violations.', 'danger')
        return redirect(url_for('candidate_assessments'))

    # If the latest attempt is completed and cannot retake, show results
    if latest_result and latest_result.get('status') == 'completed' and not can_retake:
        return render_template('assessment_results.html', assessment=assessment, result=latest_result)
    
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
        # reset warnings when the candidate begins
        result['face_warnings'] = 0
        result['cancelled'] = False
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
    
    # Send notification to all admins when assessment is submitted
    candidate = next((u for u in users if u['id'] == candidate_id), None)
    candidate_name = candidate['get_full_name'] if candidate else f'Candidate #{candidate_id}'
    admin_users = [u for u in users if u['role'] == 'Administrator']
    
    for admin in admin_users:
        create_notification(
            notification_type='assessment_submitted',
            user_id=admin['id'],
            title=f'Assessment Submitted: {assessment["title"]}',
            message=f'{candidate_name} has submitted the assessment "{assessment["title"]}" and is waiting for grading.',
            related_assessment_id=assessment_id,
            related_candidate_id=candidate_id
        )
    
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
        # deduct 5% for each warning (face or voice), up to 2 total
        face = result.get('face_warnings', 0) or 0
        voice = result.get('voice_warnings', 0) or 0
        total_warn = face + voice
        deduction = min(total_warn, 2) * 5
        if deduction:
            score_percentage = max(score_percentage - deduction, 0)
            result['deduction_percentage'] = deduction
        result['score_percentage'] = score_percentage
        result['passed'] = score_percentage >= assessment.get('passing_score', 70)
        result['status'] = 'completed'
        result['graded_by_admin'] = session.get('user_id')
        result['graded_date'] = datetime.now().isoformat()
        
        save_to_file('assessments.json', assessments)
        
        # Send notification to candidate
        create_notification(
            notification_type='assessment_graded',
            user_id=candidate_id,
            title=f'Assessment Graded: {assessment["title"]}',
            message=f'Your assessment "{assessment["title"]}" has been graded. Score: {score_percentage}%. Status: {"Passed" if result["passed"] else "Failed"}.',
            related_assessment_id=assessment_id
        )
        
        flash('Assessment graded successfully.', 'success')
        return redirect(url_for('admin_results'))
    
    return render_template('grade_assessment.html', 
                         assessment=assessment, 
                         result=result, 
                         candidate=candidate)



# new endpoint for recording proctoring warnings
@app.route('/candidate/assessments/<int:assessment_id>/warning', methods=['POST'])
def record_warning(assessment_id):
    """AJAX handler for proctoring warnings.

    The POST body may include a JSON field ``reason`` with values
    ``"face"`` or ``"voice"``; defaults to ``"face"``.  Each warning
    increments the corresponding counter.  A total of more than two
    combined warnings (face + voice) will cancel the assessment.
    """
    if not require_login('Candidate'):
        return json.dumps({'error': 'not logged in'}), 403
    candidate_id = session.get('user_id')
    assessment = next((a for a in assessments if a['id'] == assessment_id), None)
    if not assessment:
        return json.dumps({'error': 'assessment not found'}), 404
    result = next((r for r in assessment.get('results', []) if r['candidate_id'] == candidate_id), None)
    if not result or result.get('status') != 'in_progress':
        return json.dumps({'error': 'not in progress'}), 400

    data = {}
    try:
        data = request.get_json() or {}
    except Exception:
        pass
    reason = data.get('reason', 'face')

    if reason == 'voice':
        result['voice_warnings'] = result.get('voice_warnings', 0) + 1
        count = result['voice_warnings']
    else:
        result['face_warnings'] = result.get('face_warnings', 0) + 1
        count = result['face_warnings']

    # compute combined total
    total_warnings = (result.get('face_warnings', 0) or 0) + (result.get('voice_warnings', 0) or 0)
    save_to_file('assessments.json', assessments)

    # Notify admins of the violation
    candidate = next((u for u in users if u['id'] == candidate_id), None)
    candidate_name = candidate['get_full_name'] if candidate else f'Candidate #{candidate_id}'
    admin_users = [u for u in users if u['role'] == 'Administrator']
    
    for admin in admin_users:
        create_notification(
            notification_type='proctoring_violation',
            user_id=admin['id'],
            title=f'Proctoring Violation: {assessment["title"]}',
            message=f'{candidate_name} triggered a {reason} violation during assessment "{assessment["title"]}". Warning #{count} for this type.',
            related_assessment_id=assessment_id,
            related_candidate_id=candidate_id
        )

    if total_warnings > 2:
        result['status'] = 'cancelled'
        result['cancelled'] = True
        save_to_file('assessments.json', assessments)
        return json.dumps({'cancelled': True}), 200

    return json.dumps({'reason': reason, 'count': count, 'total': total_warnings}), 200


@app.route('/api/analyze_frame/<int:assessment_id>', methods=['POST'])
def analyze_frame(assessment_id):
    """Analyze a video frame for cheating detection using computer vision."""
    if not require_login('Candidate'):
        return json.dumps({'error': 'not logged in'}), 403
    
    candidate_id = session.get('user_id')
    assessment = next((a for a in assessments if a['id'] == assessment_id), None)
    if not assessment:
        return json.dumps({'error': 'assessment not found'}), 404
    
    result = next((r for r in assessment.get('results', []) if r['candidate_id'] == candidate_id), None)
    if not result or result.get('status') != 'in_progress':
        return json.dumps({'error': 'not in progress'}), 400

    # Get the base64 image data
    data = request.get_json()
    if not data or 'image' not in data:
        return json.dumps({'error': 'no image provided'}), 400
    
    image_data = data['image']
    # Remove the data URL prefix if present
    if ',' in image_data:
        image_data = image_data.split(',')[1]
    
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        # Convert to OpenCV format
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Load face cascade classifier
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        violations = []
        
        # Check for multiple faces (potential cheating)
        if len(faces) > 1:
            violations.append('multiple_faces')
        
        # Check if no face detected
        elif len(faces) == 0:
            violations.append('no_face')
        
        # If exactly one face, check if it's centered
        elif len(faces) == 1:
            face = faces[0]
            h, w = opencv_image.shape[:2]
            face_center_x = face[0] + face[2] / 2
            face_center_y = face[1] + face[3] / 2
            
            # Check if face is in center region (roughly 40% of screen)
            center_region_left = w * 0.3
            center_region_right = w * 0.7
            center_region_top = h * 0.3
            center_region_bottom = h * 0.7
            
            if not (center_region_left <= face_center_x <= center_region_right and 
                    center_region_top <= face_center_y <= center_region_bottom):
                violations.append('face_not_centered')
        
        # If violations detected, record warning
        if violations:
            # Use the first violation as the reason
            reason = violations[0]
            
            # Increment face warnings (since this is vision-based)
            result['face_warnings'] = result.get('face_warnings', 0) + 1
            count = result['face_warnings']
            
            total_warnings = (result.get('face_warnings', 0) or 0) + (result.get('voice_warnings', 0) or 0)
            save_to_file('assessments.json', assessments)
            
            # Notify admins
            candidate = next((u for u in users if u['id'] == candidate_id), None)
            candidate_name = candidate['get_full_name'] if candidate else f'Candidate #{candidate_id}'
            admin_users = [u for u in users if u['role'] == 'Administrator']
            
            for admin in admin_users:
                create_notification(
                    notification_type='proctoring_violation',
                    user_id=admin['id'],
                    title=f'Computer Vision Alert: {assessment["title"]}',
                    message=f'{candidate_name} detected with {reason.replace("_", " ")} during assessment "{assessment["title"]}". Warning #{count}.',
                    related_assessment_id=assessment_id,
                    related_candidate_id=candidate_id
                )
            
            # Check if assessment should be cancelled
            if total_warnings > 2:
                result['status'] = 'cancelled'
                result['cancelled'] = True
                save_to_file('assessments.json', assessments)
                return json.dumps({'violations': violations, 'cancelled': True, 'count': count}), 200
            
            return json.dumps({'violations': violations, 'count': count, 'total': total_warnings}), 200
        
        return json.dumps({'violations': []}), 200
        
    except Exception as e:
        print(f"Error processing frame: {e}")
        return json.dumps({'error': 'processing failed'}), 500


# prevent browsers from caching sensitive pages so that hitting the back
# button after logging out doesn't display stale content
@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


if __name__ == '__main__':
    app.run(debug=True)

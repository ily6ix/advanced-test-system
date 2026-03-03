# Advanced Test System

A comprehensive Flask-based assessment platform with admin and candidate interfaces. The system supports creating assessments with questions, candidates taking assessments, and admins grading with point allocation.

---

## 🚀 Getting Started

1. **Clone and Setup**
   ```bash
   git clone <repo>
   cd advanced-test-system
   source .venv/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   pip install flask
   ```

3. **Run the Application**
   ```bash
   python app.py
   ```
   Open `http://localhost:5000` in your browser.

4. **First Login**
   The system uses JSON-based user authentication. Default credentials:
   - **Admin**: alice@example.com / alice_pass
   - **Candidate**: goitseonetrade@gmail.com / goitseone_pass

---

## 🗂️ Project Structure

```
advanced-test-system/
├── app.py                      # Flask application & routes
├── data/
│   ├── users.json              # User accounts & credentials
│   └── assessments.json        # Assessments, questions, & results
├── templates/
│   ├── login.html              # Login page
│   ├── index.html              # Landing page
│   ├── admin_base.html         # Admin layout base
│   ├── admin_*.html            # Admin pages
│   ├── candidate_base.html     # Candidate layout base
│   ├── candidate_*.html        # Candidate pages
│   ├── assessment_form.html    # Create/edit assessments
│   ├── manage_questions.html   # Add/delete questions
│   ├── take_assessment.html    # Candidate takes test
│   └── grade_assessment.html   # Admin grades test
└── README.md
```

---

## 🔐 Authentication

- **Email & Password**: Users authenticate with email and password stored in `users.json`
- **Session Management**: Session stores user_id, email, role, and name
- **Role-Based Access**: 
  - `Administrator`: Can manage users, create assessments, grade submissions
  - `Candidate`: Can take assigned assessments and view results
  - `Manager`: Currently inactive role for future expansion

---

## 📊 Data Structure

### Users (users.json)
```json
{
  "id": 1,
  "get_full_name": "Alice Johnson",
  "email": "alice@example.com",
  "password": "alice_pass",
  "is_active": true,
  "role": "Administrator",
  "last_login": "2026-03-02T13:06:46.251941"
}
```

### Assessments (assessments.json)
```json
{
  "id": 1,
  "title": "Intro to Python",
  "description": "...",
  "duration": 60,
  "passing_score": 70,
  "is_published": true,
  "assigned_to": [4],
  "questions": [
    {
      "id": 1,
      "text": "What is correct?",
      "type": "multiple_choice",
      "options": ["A", "B", "C"],
      "correct_answer": 0,
      "points": 10
    },
    {
      "id": 2,
      "text": "Explain X",
      "type": "short_answer",
      "points": 10
    }
  ],
  "results": [
    {
      "candidate_id": 4,
      "status": "completed",
      "submitted_date": "2026-02-15T10:30:00",
      "time_spent": 45,
      "answers": [
        {
          "question_id": 1,
          "candidate_answer": 0,
          "allocated_points": 10,
          "graded": true
        }
      ],
      "total_score": 28,
      "score_percentage": 93,
      "passed": true,
      "graded_by_admin": 1,
      "graded_date": "2026-02-15T11:00:00"
    }
  ]
}
```

---

## 🔄 Website Flow Diagram

### User Navigation Flow
```mermaid

flowchart LR
    Start(["User"]) --> Login["/login"]
    Login -->|Email & Password| Auth{"Role Check"}
    Auth -->|Administrator| Admin["🔑 /admin"]
    Auth -->|Candidate| Candidate["📝 /candidate"]
    
    Admin --> AO["Overview<br>/admin"]
    Admin --> AC["Manage Users<br>/admin/candidates"]
    Admin --> AA["Manage Assessments<br>/admin/assessments"]
    Admin --> MQ["Manage Questions<br>/admin/assessments/id/questions"]
    Admin --> AR["Grade Results<br>/admin/results"]
    
    Candidate --> CD["Dashboard<br>/candidate"]
    Candidate --> CA["Assessments<br>/candidate/assessments"]
    Candidate --> TA["Take Test<br>/candidate/assessments/id/take"]
    Candidate --> CR["View Results<br>/candidate/results"]
    Candidate --> CN["Notifications<br>/candidate/notifications"]
    Candidate --> CP["Profile<br>/candidate/profile"]
    
    AO --> Logout["/logout"]
    AR --> Logout
    CR --> Logout

---

## 📈 Assessment Lifecycle (Data Flow)

### Phase 1: Admin Creates Assessment
```
Admin Creates Assessment
    ↓
[/admin/assessments/create POST]
    ↓
{assessment object created}
  - title, description, duration
  - passing_score
  - assigned_to: []
  - questions: []
  - results: []
    ↓
Saved to: data/assessments.json
```

### Phase 2: Admin Adds Questions
```
Admin Navigates to Manage Questions
    ↓
[/admin/assessments/<id>/questions GET]
    ↓
Display: Existing questions + Add form
    ↓
[/admin/assessments/<id>/questions POST (action=add)]
    ↓
{question object created}
  - id, text, type
  - points (configurable per question)
  - For multiple choice:
    * options: array
    * correct_answer: index
    ↓
Assessment.questions[] ← new question
    ↓
Saved to: data/assessments.json
```

### Phase 3: Admin Assigns to Candidates
```
Admin Views Assessment
    ↓
[/admin/assessments/<id>/edit]
    ↓
Allocates candidate IDs to assessment.assigned_to[]
    ↓
For each candidate in assigned_to:
  Create result object {
    candidate_id,
    status: "not_started",
    answers: [],
    total_score: null,
    score_percentage: null,
    passed: null
  }
    ↓
Saved to: data/assessments.json
```

### Phase 4: Candidate Takes Assessment
```
Candidate Opens Assessment
    ↓
[/candidate/assessments/<id>/take GET]
    ↓
Render: All questions from assessment.questions[]
    ↓
Candidate Answers Questions
    ↓
[/candidate/assessments/<id>/take POST]
    ↓
{answers submitted}
For each question:
  answers[] ← {
    question_id,
    candidate_answer: (text or index),
    allocated_points: null,
    graded: false
  }
    ↓
result.status = "submitted"
result.submitted_date = NOW
result.time_spent = calculated
    ↓
Saved to: data/assessments.json
```

### Phase 5: Admin Grades Assessment
```
Admin Views Grading Queue
    ↓
[/admin/results GET]
    ↓
Display: Pending (status="submitted") assessments
    ↓
Admin Clicks "Grade"
    ↓
[/admin/assessments/<id>/grade/<candidate_id> GET]
    ↓
Display: All questions + candidate answers + point input
    ↓
[/admin/assessments/<id>/grade/<candidate_id> POST]
    ↓
Admin Allocates Points Per Question
For each answer:
  answer.allocated_points = admin_input
  answer.graded = true
    ↓
System Calculates:
  total_score = SUM(answer.allocated_points)
  score_percentage = (total_score / max_points) * 100
  passed = score_percentage >= assessment.passing_score
    ↓
result.status = "completed"
result.graded_by_admin = admin_id
result.graded_date = NOW
    ↓
Saved to: data/assessments.json
```

### Phase 6: Candidate Reviews Results
```
Candidate Views Results
    ↓
[/candidate/results GET]
    ↓
Filter: Results where status = "completed"
    ↓
Display:
  - Assessment title
  - Score percentage
  - Pass/Fail status
  - Passing score requirement
    ↓
Optional: View detailed answer feedback
```

---

## 🎯 Key Features

### Admin Features
- ✅ Create/edit assessments with configurable duration & passing score
- ✅ Create multiple types of questions (multiple choice, short answer)
- ✅ Set points per question
- ✅ Manage candidates (view, add, edit, deactivate)
- ✅ Assign assessments to candidates
- ✅ Grade submitted assessments
- ✅ Allocate points per question
- ✅ View grading results and analytics

### Candidate Features
- ✅ View assigned assessments
- ✅ Take assessments with timer tracking
- ✅ Answer multiple choice & short answer questions
- ✅ Submit assessments
- ✅ View results once graded
- ✅ View passing/failing score & status
- ✅ Update profile information

### System Features
- ✅ Email/password authentication
- ✅ Session-based access control
- ✅ JSON-based persistence
- ✅ Automatic data migration for format changes
- ✅ Last login tracking
- ✅ Responsive admin & candidate interfaces

---

## 🛣️ API Routes Reference

### Authentication
| Route | Method | Purpose |
|-------|--------|---------|
| `/login` | GET, POST | User login with email & password |
| `/logout` | GET | Clear session and logout |

### Admin Routes
| Route | Method | Purpose |
|-------|--------|---------|
| `/admin` | GET | Overview dashboard |
| `/admin/candidates` | GET | List candidates |
| `/admin/assessments` | GET | List assessments |
| `/admin/assessments/create` | GET, POST | Create assessment |
| `/admin/assessments/<id>/edit` | GET, POST | Edit assessment |
| `/admin/assessments/<id>/questions` | GET, POST | Manage assessment questions |
| `/admin/results` | GET | View pending & completed results |
| `/admin/assessments/<id>/grade/<candidate_id>` | GET, POST | Grade submission |
| `/admin/users/add` | GET, POST | Add user |
| `/admin/users/<id>/edit` | GET, POST | Edit user |
| `/admin/users/<id>/delete` | POST | Delete user |

### Candidate Routes
| Route | Method | Purpose |
|-------|--------|---------|
| `/candidate` | GET | Dashboard |
| `/candidate/assessments` | GET | List assigned assessments |
| `/candidate/assessments/<id>/take` | GET, POST | Take assessment |
| `/candidate/results` | GET | View completed results |
| `/candidate/notifications` | GET | View notifications |
| `/candidate/profile` | GET, POST | View/edit profile |

---

## 🔧 Development Notes

### Data Persistence
- All data is persisted to JSON files in `data/` directory
- Files are automatically created on first run if missing
- No database ORM required for this prototype

### Question Types
- **Multiple Choice**: Admin defines options and correct answer index
- **Short Answer**: Candidates submit text; admin awards points manually

### Scoring
- Points are allocated per question (configurable by admin)
- Total score = sum of allocated points
- Percentage = (total_score / max_points) * 100
- Pass/Fail determined by assessment's passing_score threshold

### Time Tracking
- Assessed time is tracked in seconds
- Automatically calculated from submission timestamp
- Useful for analytics and assessment difficulty analysis

---

## 📝 Example Workflow

1. **Admin Alice** logs in with alice@example.com
2. Creates "Python Fundamentals" assessment (60 min, 70% pass)
3. Adds 3 questions:
   - Q1: Multiple choice (10 points) - "What is a list?"
   - Q2: Multiple choice (10 points) - "What is a function?"
   - Q3: Short answer (10 points) - "Explain mutable vs immutable"
4. Assigns to candidate Goitseone (ID: 4)
5. **Candidate Goitseone** logs in
6. Answers all 3 questions and submits
7. **Admin Alice** grades the submission:
   - Q1: 10/10 (correct)
   - Q2: 10/10 (correct)
   - Q3: 8/10 (good but incomplete)
   - **Total: 28/30 (93%) → PASSED ✓**
8. **Candidate Goitseone** views results showing 93% passed

---

## 🚀 Future Enhancements

- [ ] Question bank & question reuse across assessments
- [ ] Automatic multiple choice grading
- [ ] Assessment templates & duplication
- [ ] Proctoring options
- [ ] Analytics dashboard with charts
- [ ] Email notifications
- [ ] CSV/PDF export
- [ ] Assessment scheduling & deadlines
- [ ] Cheating detection (time analysis)
- [ ] Real database integration (PostgreSQL/MongoDB)

---

## 📄 License

This project is open source. Feel free to modify and extend as needed.


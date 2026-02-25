# advanced-test-system

A lightweight Flask-based assessment system prototype. The repository includes both **admin** and **candidate** interfaces along with a simple routing structure and templating.

---

## 🚀 Getting Started

1. Clone the repo and create a Python virtual environment (the project already contains a `.venv`).
2. Activate the environment:

   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt  # if you add dependencies
   ```

3. Run the app:

   ```bash
   python app.py
   ```

4. Open `http://localhost:5000` in your browser.

*The login is stubbed – use `admin`/`1234` for admin or `candidate`/`1234` for a candidate.*

---

## 🧭 Page Functionality Overview

The system is split into two main areas: **admin** and **candidate**. Access is determined by the login credentials and the application logic in `app.py`.

### Public Routes

- `/` – Redirects to index (landing page, not yet implemented beyond a placeholder).
- `/login` – Login form for admins and candidates.
- `/logout` – Clears session placeholder and returns to login.

### Admin Area (prefixed with `/admin`)

| Route                    | Template                | Purpose                                                      |
|--------------------------|-------------------------|--------------------------------------------------------------|
| `/admin`                 | `admin_overview.html`   | Dashboard summary with KPIs, user list, and assessment list.  |
| `/admin/candidates`      | `admin_candidates.html` | Candidate management table (search/add/edit/suspend etc.).   |
| `/admin/assessments`     | `admin_assessments.html`| List and manage assessment content (publish/draft, edit).    |
| `/admin/results`         | `admin_results.html`    | Analytics placeholders (charts, score distributions).        |
| `/admin/reports`         | `admin_reports.html`    | Export reports (CSV, PDF, logs).                             |
| `/admin/security`        | `admin_security.html`   | Audit log display for admin actions.                         |
| `/admin/settings`        | `admin_settings.html`   | System-wide settings (password policy, defaults, etc.).      |

There are also stubbed auxiliary routes used by links inside the overview page:

- `/admin/users/add`, `/admin/users/<id>/edit` – user forms (currently flash a message).
- `/admin/assessments/create`, `/admin/assessments/<id>/edit` – assessment forms.

### Candidate Area (prefixed with `/candidate`)

| Route                       | Template                     | Purpose                                                   |
|-----------------------------|------------------------------|-----------------------------------------------------------|
| `/candidate`                | `candidate_dashboard.html`   | Candidate homepage with current assessment status/cards.   |
| `/candidate/assessments`    | `candidate_assessments.html` | List of assigned assessments and ability to start/resume.  |
| `/candidate/results`        | `candidate_results.html`     | Individual results overview.                              |
| `/candidate/notifications`  | `candidate_notifications.html`| Alerts/messages for candidate.                            |
| `/candidate/profile`        | `candidate_profile.html`     | Personal profile view (editable).                        |

Each area uses a base template (`admin_base.html` or `candidate_base.html`) that defines the top bar, sidebar nav, and includes shared CSS styles.

---

## 🔄 Website Flow Diagram

Below is a high-level navigation flow showing how a user moves through the application. ⚠️ This is a static, mermaid-style diagram – renderable on supported Markdown viewers.

```mermaid
flowchart LR
    A[Landing /] --> B[/login]
    B -->|admin| C[/admin]
    B -->|candidate| D[/candidate]
    C --> E[/admin/candidates]
    C --> F[/admin/assessments]
    C --> G[/admin/results]
    C --> H[/admin/reports]
    C --> I[/admin/security]
    C --> J[/admin/settings]
    D --> K[/candidate/assessments]
    D --> L[/candidate/results]
    D --> M[/candidate/notifications]
    D --> N[/candidate/profile]
    C --> Z[/logout]
    D --> Z
```

---

## 📊 Data Flow Diagram

This diagram illustrates the typical processing path when a page is requested. It is deliberately simple due to the current lack of a real database.

```mermaid
flowchart TD
    U[User Browser] -->|HTTP GET| S[Flask Route]
    S --> T{Is Admin?}
    T -->|yes| A[admin_* views]
    T -->|no| C[candidate_* views]
    A --> DB[(Database placeholder)]
    C --> DB
    DB --> A
    DB --> C
    A --> R[render_template()]
    C --> R
    R --> U

    subgraph Processing
        S --> Auth[check credentials]
    end
```

> 💡 In a production system, `DB` would be replaced by actual models/ORM queries; the placeholder arrows represent data retrieval and update operations performed by each view.

---

## 🧩 Development Notes

* Templates use Jinja2 with shared CSS variables defined in the base files.
* Navigation bars are kept consistent between admin and candidate bases.
* Backend logic is currently minimal; expand the route handlers with real data accesses as needed.
* A future refactor might extract common base template elements into a shared partial.

Feel free to expand this README with deployment instructions, API details, or architecture decisions as the project grows.

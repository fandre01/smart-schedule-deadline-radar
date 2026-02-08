# Smart Schedule + Deadline Radar

A web app that helps college students stay on top of classes, deadlines, and weekly planning. It turns syllabus items into a schedule, highlights high-risk weeks, and suggests a realistic weekly plan.

## Goals

- Make deadlines visible early and avoid last-minute surprises.
- Reduce planning effort by auto-building weekly schedules.
- Keep usage quick: 1-2 minutes a day.

## Target Users

- College students juggling multiple courses.
- Students who struggle with time management or planning.
- Clubs or peer study groups that coordinate shared deadlines.

## Core Features (MVP)

- **Syllabus import**: manual entry and CSV upload for assignments, exams, and readings.
- **Deadline Radar**: weekly heatmap of upcoming workload and risk alerts.
- **Weekly Plan**: auto-suggested study blocks based on due dates and available time.
- **Task list**: break assignments into smaller tasks with estimated durations.
- **Reminders**: email or push-style notifications for upcoming deadlines.

## Nice-to-Have Features (Post-MVP)

- Calendar sync (Google/Apple/Outlook).
- Study group sharing and accountability.
- Campus resource links (tutoring, office hours).
- Focus mode with timer and break suggestions.
- Mobile-first PWA support.

## User Stories

- As a student, I want to upload my syllabus so I do not have to enter everything by hand.
- As a student, I want to see a weekly workload heatmap so I can plan ahead.
- As a student, I want the app to suggest study blocks so I can follow a realistic plan.
- As a student, I want reminders so I do not miss deadlines.
- As a student, I want to adjust the plan quickly when my schedule changes.

## MVP Scope (Build Order)

1. User auth and onboarding.
2. Courses and deadline entry.
3. Deadline Radar (weekly view + risk score).
4. Weekly Plan generator (basic algorithm).
5. Notifications.

## Basic Planning Logic (First Pass)

- Calculate required study time per item (simple estimate by type).
- Spread tasks across available time windows, prioritizing nearest deadlines.
- Flag overload when planned time > available time.

## Tech Stack (Streamlit, Python)

- **App**: Streamlit (UI + backend in one app).
- **Database**: SQLite (local) with a simple upgrade path to PostgreSQL.
- **Auth**: Basic email/password (local, hashed).
- **Notifications**: Email (post-MVP).

## Data Model (Draft)

- **User**: id, name, email, timezone.
- **Course**: id, user_id, title, color.
- **Deadline**: id, course_id, title, type, due_at, estimated_hours.
- **Task**: id, deadline_id, title, estimated_hours, status.
- **Availability**: id, user_id, day_of_week, start_time, end_time.

## App Structure

- `app.py` - main Streamlit app
- `data/db.py` - SQLite connection + schema
- `services/auth.py` - auth helpers
- `services/planning.py` - planning logic
- `requirements.txt`

## Pages (Draft)

- Landing
- Onboarding (import / manual entry)
- Dashboard (Deadline Radar + next tasks)
- Weekly Plan
- Course Details
- Settings (availability and notifications)

## Milestones

- **Day 1-2**: project setup, auth, DB schema.
- **Day 3-4**: course + deadline CRUD.
- **Day 5**: Deadline Radar UI.
- **Day 6-7**: planning logic + weekly plan view.
- **Day 8**: reminders and polish.

## Setup (Streamlit)

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
streamlit run app.py
```

## Open Questions

- Should syllabus import prioritize CSV or PDF parsing first?
- Do we want a point system or streaks for motivation?
- How granular should availability windows be by default?

## License

MIT
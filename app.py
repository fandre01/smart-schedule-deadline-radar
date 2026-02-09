import datetime
import sqlite3
from typing import List, Optional, Tuple

import streamlit as st

from data.db import init_db, get_connection
from services.auth import authenticate_user, create_user
from services.planning import build_weekly_plan, deadline_radar


def fetch_courses(user_id: int) -> List[Tuple[int, str, str]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, color FROM courses WHERE user_id = ? ORDER BY title",
            (user_id,),
        ).fetchall()
    return [(row[0], row[1], row[2]) for row in rows]


def add_course(user_id: int, title: str, color: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO courses (user_id, title, color) VALUES (?, ?, ?)",
            (user_id, title.strip(), color.strip()),
        )
        conn.commit()


def delete_course(course_id: int, user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM courses WHERE id = ? AND user_id = ?",
            (course_id, user_id),
        )
        conn.execute(
            "DELETE FROM deadlines WHERE course_id = ?",
            (course_id,),
        )
        conn.commit()


def fetch_deadlines(user_id: int) -> List[sqlite3.Row]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT d.id, d.title, d.type, d.due_at, d.estimated_hours,
                   c.title AS course_title
            FROM deadlines d
            JOIN courses c ON c.id = d.course_id
            WHERE c.user_id = ?
            ORDER BY d.due_at ASC
            """,
            (user_id,),
        ).fetchall()
    return rows


def add_deadline(
    course_id: int,
    title: str,
    item_type: str,
    due_at: datetime.date,
    estimated_hours: float,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO deadlines (course_id, title, type, due_at, estimated_hours)
            VALUES (?, ?, ?, ?, ?)
            """,
            (course_id, title.strip(), item_type, due_at.isoformat(), estimated_hours),
        )
        conn.commit()


def delete_deadline(deadline_id: int, user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            DELETE FROM deadlines
            WHERE id = ? AND course_id IN (
                SELECT id FROM courses WHERE user_id = ?
            )
            """,
            (deadline_id, user_id),
        )
        conn.commit()


def fetch_availability(user_id: int) -> List[sqlite3.Row]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, day_of_week, start_time, end_time
            FROM availability
            WHERE user_id = ?
            ORDER BY day_of_week, start_time
            """,
            (user_id,),
        ).fetchall()
    return rows


def add_availability(
    user_id: int,
    day_of_week: int,
    start_time: datetime.time,
    end_time: datetime.time,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO availability (user_id, day_of_week, start_time, end_time)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, day_of_week, start_time.strftime("%H:%M"), end_time.strftime("%H:%M")),
        )
        conn.commit()


def delete_availability(availability_id: int, user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM availability WHERE id = ? AND user_id = ?",
            (availability_id, user_id),
        )
        conn.commit()


def format_day(day_index: int) -> str:
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][day_index]


def ensure_login_state() -> None:
    if "user" not in st.session_state:
        st.session_state.user = None


def render_login() -> None:
    st.title("Smart Schedule + Deadline Radar")
    st.subheader("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            user = authenticate_user(email, password)
            if user is None:
                st.error("Invalid email or password.")
            else:
                st.session_state.user = user
                st.success("Logged in.")

    with col2:
        if st.button("Create Account"):
            try:
                user = create_user(email, password)
                st.session_state.user = user
                st.success("Account created.")
            except ValueError as exc:
                st.error(str(exc))

    st.caption("Use a real email if you plan to add notifications later.")


def render_dashboard(user_id: int) -> None:
    st.header("Dashboard")
    radar = deadline_radar(user_id)

    st.metric("7-day workload (hrs)", f"{radar.total_hours:.1f}")
    st.metric("Risk level", radar.risk_level)

    st.subheader("Upcoming deadlines")
    if not radar.items:
        st.info("No deadlines in the next 7 days.")
        return

    for item in radar.items:
        st.write(
            f"{item['due_at']} - {item['course_title']} - {item['title']}"
            f" ({item['estimated_hours']:.1f}h)"
        )


def render_courses(user_id: int) -> None:
    st.header("Courses")

    with st.form("add_course"):
        title = st.text_input("Course title")
        color = st.text_input("Color tag", value="#4C8BF5")
        submitted = st.form_submit_button("Add course")
        if submitted:
            if not title.strip():
                st.error("Course title is required.")
            else:
                add_course(user_id, title, color)
                st.success("Course added.")

    courses = fetch_courses(user_id)
    if not courses:
        st.info("No courses yet.")
        return

    st.subheader("Your courses")
    for course_id, title, color in courses:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"{title} ({color})")
        with col2:
            if st.button("Delete", key=f"del_course_{course_id}"):
                delete_course(course_id, user_id)
                st.warning("Course deleted.")
                st.experimental_rerun()


def render_deadlines(user_id: int) -> None:
    st.header("Deadlines")
    courses = fetch_courses(user_id)
    if not courses:
        st.info("Add a course first.")
        return

    course_map = {title: course_id for course_id, title, _ in courses}

    with st.form("add_deadline"):
        course_title = st.selectbox("Course", options=list(course_map.keys()))
        title = st.text_input("Deadline title")
        item_type = st.selectbox("Type", ["Assignment", "Exam", "Project", "Reading"])
        due_at = st.date_input("Due date", value=datetime.date.today())
        estimated_hours = st.number_input("Estimated hours", min_value=0.5, max_value=100.0, value=3.0)
        submitted = st.form_submit_button("Add deadline")
        if submitted:
            if not title.strip():
                st.error("Deadline title is required.")
            else:
                add_deadline(course_map[course_title], title, item_type, due_at, estimated_hours)
                st.success("Deadline added.")

    rows = fetch_deadlines(user_id)
    if not rows:
        st.info("No deadlines yet.")
        return

    st.subheader("All deadlines")
    for row in rows:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(
                f"{row['due_at']} - {row['course_title']} - {row['title']}"
                f" ({row['estimated_hours']:.1f}h)"
            )
        with col2:
            if st.button("Delete", key=f"del_deadline_{row['id']}"):
                delete_deadline(row["id"], user_id)
                st.warning("Deadline deleted.")
                st.rerun()


def render_plan(user_id: int) -> None:
    st.header("Weekly Plan")

    start_date = st.date_input("Week starting", value=datetime.date.today())
    plan = build_weekly_plan(user_id, start_date)

    if plan.overloaded:
        st.warning("This week is overloaded. Reduce tasks or add more availability.")

    for day, items in plan.items_by_day.items():
        st.subheader(day)
        if not items:
            st.caption("No planned study blocks.")
        for item in items:
            st.write(
                f"{item['title']} - {item['course_title']}"
                f" ({item['allocated_hours']:.1f}h)"
            )


def render_settings(user_id: int) -> None:
    st.header("Settings")

    st.subheader("Availability")
    with st.form("add_availability"):
        day_of_week = st.selectbox("Day of week", list(range(7)), format_func=format_day)
        start_time = st.time_input("Start time", value=datetime.time(18, 0))
        end_time = st.time_input("End time", value=datetime.time(20, 0))
        submitted = st.form_submit_button("Add availability")
        if submitted:
            if end_time <= start_time:
                st.error("End time must be after start time.")
            else:
                add_availability(user_id, day_of_week, start_time, end_time)
                st.success("Availability added.")

    rows = fetch_availability(user_id)
    if not rows:
        st.info("No availability windows yet.")
        return

    for row in rows:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"{format_day(row['day_of_week'])}: {row['start_time']} - {row['end_time']}")
        with col2:
            if st.button("Delete", key=f"del_av_{row['id']}"):
                delete_availability(row["id"], user_id)
                st.warning("Availability deleted.")
                st.rerun()


def main() -> None:
    st.set_page_config(page_title="Smart Schedule", page_icon="📚")
    init_db()
    ensure_login_state()

    if st.session_state.user is None:
        render_login()
        return

    user = st.session_state.user
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Dashboard", "Courses", "Deadlines", "Weekly Plan", "Settings"],
    )

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    if page == "Dashboard":
        render_dashboard(user["id"])
    elif page == "Courses":
        render_courses(user["id"])
    elif page == "Deadlines":
        render_deadlines(user["id"])
    elif page == "Weekly Plan":
        render_plan(user["id"])
    elif page == "Settings":
        render_settings(user["id"])


if __name__ == "__main__":
    main()

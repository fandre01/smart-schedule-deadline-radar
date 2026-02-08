import datetime
from dataclasses import dataclass
from typing import Dict, List

from data.db import get_connection


@dataclass
class RadarSummary:
    total_hours: float
    risk_level: str
    items: List[Dict[str, str]]


@dataclass
class WeeklyPlan:
    items_by_day: Dict[str, List[Dict[str, str]]]
    overloaded: bool


def deadline_radar(user_id: int) -> RadarSummary:
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=7)

    with get_connection() as conn:
        conn.row_factory = None
        rows = conn.execute(
            """
            SELECT d.title, d.due_at, d.estimated_hours, c.title AS course_title
            FROM deadlines d
            JOIN courses c ON c.id = d.course_id
            WHERE c.user_id = ? AND d.due_at BETWEEN ? AND ?
            ORDER BY d.due_at ASC
            """,
            (user_id, today.isoformat(), end_date.isoformat()),
        ).fetchall()

    total_hours = sum(row[2] for row in rows) if rows else 0.0
    if total_hours >= 12:
        risk_level = "High"
    elif total_hours >= 6:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    items = [
        {
            "title": row[0],
            "due_at": row[1],
            "estimated_hours": row[2],
            "course_title": row[3],
        }
        for row in rows
    ]

    return RadarSummary(total_hours=total_hours, risk_level=risk_level, items=items)


def build_weekly_plan(user_id: int, start_date: datetime.date) -> WeeklyPlan:
    end_date = start_date + datetime.timedelta(days=6)

    with get_connection() as conn:
        conn.row_factory = None
        deadlines = conn.execute(
            """
            SELECT d.title, d.due_at, d.estimated_hours, c.title AS course_title
            FROM deadlines d
            JOIN courses c ON c.id = d.course_id
            WHERE c.user_id = ? AND d.due_at BETWEEN ? AND ?
            ORDER BY d.due_at ASC
            """,
            (user_id, start_date.isoformat(), end_date.isoformat()),
        ).fetchall()

        availability_rows = conn.execute(
            """
            SELECT day_of_week, start_time, end_time
            FROM availability
            WHERE user_id = ?
            ORDER BY day_of_week, start_time
            """,
            (user_id,),
        ).fetchall()

    availability_hours = {i: 0.0 for i in range(7)}
    for day_of_week, start_time, end_time in availability_rows:
        start = datetime.datetime.strptime(start_time, "%H:%M")
        end = datetime.datetime.strptime(end_time, "%H:%M")
        hours = max((end - start).seconds / 3600.0, 0)
        availability_hours[day_of_week] += hours

    plan: Dict[str, List[Dict[str, str]]] = {}
    total_required = 0.0
    total_available = sum(availability_hours.values())

    for i in range(7):
        day_label = (start_date + datetime.timedelta(days=i)).strftime("%a %b %d")
        plan[day_label] = []

    for title, due_at, estimated_hours, course_title in deadlines:
        total_required += estimated_hours

        due_date = datetime.date.fromisoformat(due_at)
        days_until_due = max((due_date - start_date).days, 0)
        days_until_due = min(days_until_due, 6)
        allocated_days = list(range(0, days_until_due + 1))

        remaining = estimated_hours
        for day_index in allocated_days:
            if remaining <= 0:
                break
            available_today = availability_hours.get(day_index, 0)
            if available_today <= 0:
                continue
            allocate = min(remaining, max(available_today * 0.5, 0.5))
            remaining -= allocate
            availability_hours[day_index] -= allocate

            day_label = (start_date + datetime.timedelta(days=day_index)).strftime("%a %b %d")
            plan[day_label].append(
                {
                    "title": title,
                    "course_title": course_title,
                    "allocated_hours": allocate,
                }
            )

    overloaded = total_required > total_available
    return WeeklyPlan(items_by_day=plan, overloaded=overloaded)

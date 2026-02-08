import datetime
from typing import Dict, Optional

import bcrypt

from data.db import get_connection


def create_user(email: str, password: str) -> Dict[str, str]:
    email = email.strip().lower()
    if not email or not password:
        raise ValueError("Email and password are required.")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    created_at = datetime.datetime.utcnow().isoformat()

    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (email, password_hash, created_at),
            )
            conn.commit()
        except Exception as exc:
            raise ValueError("Account already exists.") from exc

        row = conn.execute("SELECT id, email FROM users WHERE email = ?", (email,)).fetchone()

    return {"id": row[0], "email": row[1]}


def authenticate_user(email: str, password: str) -> Optional[Dict[str, str]]:
    email = email.strip().lower()
    if not email or not password:
        return None

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    if row is None:
        return None

    password_hash = row[2]
    if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
        return None

    return {"id": row[0], "email": row[1]}

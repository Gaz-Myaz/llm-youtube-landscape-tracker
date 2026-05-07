from __future__ import annotations

import psycopg


def check_connection(database_url: str) -> bool:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select 1")
            return cursor.fetchone() == (1,)

from datetime import datetime
from flask import render_template, request

def string_to_bool(string: str) -> bool:
    """Given a string, convert it into a boolean value."""
    return string == "True"


def string_to_date(string: str) -> datetime:
    """Given a string, convert it into yyyy-mm-dd hh:mm:ss and then to yyyy-MM-dd"""
    return datetime.strptime(
        string,
        "%Y-%m-%d",  # Strips the datetime (yyyy-MM-dd hh:mm:ss)
    ).date() # Converts it to yyyy-MM-dd


def string_to_number(number):
    """Tries to cast a string to an integer."""
    try:
        return int(number)  # Attempts to cast the id (if any) to an integer
    except (ValueError, TypeError):  # If either not an integer or None
        pass
    return number


def is_admin() -> bool:
    """Returns the result of querying for the cookie 'admin.'"""
    return string_to_bool(request.cookies.get("admin"))

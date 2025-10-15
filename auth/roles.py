from typing import Literal, Dict

Role = Literal["admin", "manager", "employee"]


def is_admin(user: Dict) -> bool:
    return (user or {}).get("role") == "admin"


def is_manager(user: Dict) -> bool:
    return (user or {}).get("role") == "manager"


def is_employee(user: Dict) -> bool:
    return (user or {}).get("role") == "employee"

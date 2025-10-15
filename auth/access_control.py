from typing import Dict, List, Set
from config.database import get_db
from supabase import Client
from auth.roles import is_admin, is_manager, is_employee


class AccessControl:
    def __init__(self):
        self.db: Client = get_db()

    def get_assigned_projects(self, user_id: str, organization_id: str) -> Set[str]:
        try:
            res = (
                self.db.table("project_assignments")
                .select("project_id")
                .eq("user_id", user_id)
                .eq("organization_id", organization_id)
                .execute()
            )
            return {r["project_id"] for r in (res.data or []) if r.get("project_id")}
        except Exception:
            return set()

    def can_view_budget(self, user: Dict, budget: Dict) -> bool:
        if is_admin(user):
            return True
        if (user or {}).get("organization_id") != budget.get("organization_id"):
            return False
        if is_manager(user) or is_employee(user):
            assigned = self.get_assigned_projects(user["id"], user["organization_id"])
            return budget.get("project_id") in assigned or not budget.get("project_id")
        return False

    def can_edit_budget(self, user: Dict, budget: Dict) -> bool:
        if is_admin(user):
            return True
        if is_manager(user) and (user or {}).get("organization_id") == budget.get(
            "organization_id"
        ):
            assigned = self.get_assigned_projects(user["id"], user["organization_id"])
            return budget.get("project_id") in assigned
        return False

    def can_delete_budget(self, user: Dict, budget: Dict) -> bool:
        return self.can_edit_budget(user, budget)

    def can_submit_proposal(self, user: Dict, project_id: str) -> bool:
        if not (is_employee(user) or is_manager(user) or is_admin(user)):
            return False
        if is_admin(user):
            return True
        assigned = self.get_assigned_projects(user["id"], user["organization_id"])
        return project_id in assigned

    def is_project_manager(self, user: Dict, project_id: str) -> bool:
        if is_admin(user):
            return True
        if not is_manager(user):
            return False
        assigned = self.get_assigned_projects(user["id"], user["organization_id"])
        return project_id in assigned

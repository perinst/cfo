# services/data_service.py
from auth.roles import is_employee, is_manager, is_admin
from auth.access_control import AccessControl
from config.database import get_db
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import re
from supabase import Client
from services.stripe_service import StripeService


class DataService:
    def __init__(self):
        self.db: Client = get_db()
        # Access control helper for role and assignment checks
        self.ac = AccessControl()
        # Lazy init StripeService when needed
        self._stripe: Optional[StripeService] = None

    def get_organizations(self):
        """Get all organizations"""
        return self.db.table("organizations").select("*").execute().data

    # ---------------- Transactions ----------------
    def _ensure_stripe(self) -> StripeService:
        if not self._stripe:
            self._stripe = StripeService()
        return self._stripe

    def sync_transactions_from_stripe(self, current_user: Dict, days: int = 7) -> Dict:
        """Admin-only: sync recent Stripe transactions into Supabase."""
        try:
            if not current_user or not current_user.get("organization_id"):
                return {"success": False, "error": "Missing organization context"}
            if not is_admin(current_user):
                return {"success": False, "error": "Only admin can sync Stripe"}
            svc = self._ensure_stripe()
            return svc.sync_recent(current_user["organization_id"], days)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_transaction_manual(
        self,
        current_user: Dict,
        amount: float,
        date: str,
        category: str,
        merchant: Optional[str] = None,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        status: str = "pending",
        currency: str = "USD",
        payment_method: Optional[str] = None,
        invoice_id: Optional[str] = None,
        card_id: Optional[str] = None,
    ) -> Dict:
        """Create a manual transaction (source=manual). Respect role-based permissions."""
        try:
            org_id = (current_user or {}).get("organization_id")
            if not org_id:
                return {"success": False, "error": "No organization"}

            # Permission: employees can only create for assigned project and themselves
            if is_employee(current_user) or is_manager(current_user):
                if project_id and not self.ac.can_submit_proposal(
                    current_user, project_id
                ):
                    return {"success": False, "error": "Not assigned to project"}
            elif not is_admin(current_user):
                return {"success": False, "error": "Unauthorized"}

            data = {
                "transaction_id": None,
                "amount": amount,
                "date": date,
                "category": category,
                "merchant": merchant,
                "employee_id": current_user.get("id"),
                "fraud_flag": 0,
                "description": description,
                "payment_method": payment_method or "manual",
                "currency": currency,
                "status": status,
                "approval_required": 0,
                "organization_id": org_id,
                "created_by": current_user.get("id"),
                "project_id": project_id,
            }
            try:
                res = self.db.table("transactions").insert(data).execute()
            except Exception:
                # Fallback without project_id if column missing
                data2 = data.copy()
                data2.pop("project_id", None)
                res = self.db.table("transactions").insert(data2).execute()

            tx_row = res.data[0] if res.data else None

            # Side-effects: card_transactions/invoices link if provided
            if card_id and tx_row:
                try:
                    self.db.table("card_transactions").insert(
                        {
                            "card_id": card_id,
                            "transaction_id": tx_row["id"],
                            "amount": amount,
                            "merchant": merchant,
                            "category": category,
                            "status": status,
                        }
                    ).execute()
                except Exception:
                    pass

            if invoice_id and org_id:
                try:
                    inv = (
                        self.db.table("invoices")
                        .select("id")
                        .eq("invoice_id", invoice_id)
                        .eq("organization_id", org_id)
                        .limit(1)
                        .execute()
                    )
                    if inv.data:
                        self.db.table("invoices").update({"status": "paid"}).eq(
                            "id", inv.data[0]["id"]
                        ).execute()
                except Exception:
                    pass

            return {"success": True, "data": tx_row}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_transactions(
        self,
        current_user: Dict,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        project_id: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        merchant: Optional[str] = None,
    ) -> List[Dict]:
        """List transactions with org scope and role-based filters."""
        try:
            org_id = (current_user or {}).get("organization_id")
            if not org_id:
                return []
            q = self.db.table("transactions").select("*")
            q = q.eq("organization_id", org_id)

            # Role scoping
            if is_manager(current_user) or is_employee(current_user):
                assigned = self.ac.get_assigned_projects(current_user["id"], org_id)
                if assigned:
                    try:
                        q = q.in_("project_id", list(assigned))
                    except Exception:
                        # If project_id column missing, no project-level scoping can be applied
                        pass
                if is_employee(current_user):
                    q = q.eq(
                        "created_by", current_user["id"]
                    )  # only their transactions

            if start_date:
                q = q.gte("date", start_date)
            if end_date:
                q = q.lte("date", end_date)
            if category:
                q = q.eq("category", category)
            if status:
                q = q.eq("status", status)
            if merchant:
                q = q.eq("merchant", merchant)
            if project_id:
                try:
                    q = q.eq("project_id", project_id)
                except Exception:
                    pass

            res = q.order("date", desc=True).limit(500).execute()
            return res.data or []
        except Exception as e:
            print(f"Error in list_transactions: {e}")
            return []

    def list_pending_transactions_for_manager(self, current_user: Dict) -> List[Dict]:
        """Return transactions that require approval and are pending, scoped to manager's assigned projects or all for admin."""
        try:
            org_id = (current_user or {}).get("organization_id")
            if not org_id:
                return []
            q = self.db.table("transactions").select("*")
            q = (
                q.eq("organization_id", org_id)
                .eq("approval_required", 1)
                .eq("status", "pending")
            )
            if is_manager(current_user):
                assigned = self.ac.get_assigned_projects(current_user["id"], org_id)
                try:
                    if assigned:
                        q = q.in_("project_id", list(assigned))
                except Exception:
                    # If project scoping not possible, fall back to none (no visibility)
                    return []
            res = q.order("date", desc=True).limit(200).execute()
            return res.data or []
        except Exception as e:
            print(f"Error in list_pending_transactions_for_manager: {e}")
            return []

    def approve_transaction(
        self, current_user: Dict, tx_id: str, decision: str
    ) -> Dict:
        """Approve or reject a pending transaction. Admin or project manager for tx.project_id."""
        try:
            if decision not in ("approve", "reject"):
                return {"success": False, "error": "Invalid decision"}

            cur = (
                self.db.table("transactions")
                .select("*")
                .eq("id", tx_id)
                .limit(1)
                .execute()
            )

            if not cur.data:
                return {"success": False, "error": "Not found"}
            tx = cur.data[0]
            # Permission
            if not is_admin(current_user):
                proj = tx.get("project_id")
                if not proj or not self.ac.is_project_manager(current_user, proj):
                    return {"success": False, "error": "Unauthorized"}
            new_status = "approved" if decision == "approve" else "rejected"
            self.db.table("transactions").update({"status": new_status}).eq(
                "id", tx_id
            ).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_spending_summary(
        self,
        org_id: int = None,
        days: int = 30,
    ) -> Dict:
        """Get spending summary for last N days"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            q = self.db.table("transactions").select("*")
            if org_id is not None:
                q = q.eq("organization_id", org_id)
            q = q.gte("date", start_date.date().isoformat()).lte(
                "date", end_date.date().isoformat()
            )
            result = q.execute()

            if not result.data:
                return {
                    "total_spent": 0,
                    "transaction_count": 0,
                    "avg_transaction": 0,
                    "by_category": {},
                    "by_status": {},
                }

            df = pd.DataFrame(result.data)

            return {
                "total_spent": float(df["amount"].sum()),
                "transaction_count": len(df),
                "avg_transaction": float(df["amount"].mean()),
                "by_category": df.groupby("category")["amount"].sum().to_dict(),
                "by_status": df.groupby("status")["amount"].count().to_dict(),
                "top_merchants": df.groupby("merchant")["amount"]
                .sum()
                .nlargest(5)
                .to_dict(),
            }
        except Exception as e:
            print(f"Error in get_spending_summary: {e}")
            return {"error": str(e)}

    def get_budget_analysis(self, org_id: int) -> List[Dict]:
        """Analyze budget varia,nce"""
        try:
            result = (
                self.db.table("budgets")
                .select("*")
                .eq("organization_id", org_id)
                .execute()
            )
            budgets = []
            for budget in result.data:
                approved_raw = budget.get("approved_amount")
                spent_raw = budget.get("actual_spent")

                try:
                    approved = float(approved_raw) if approved_raw is not None else 0.0
                    spent = float(spent_raw) if spent_raw is not None else 0.0
                except (TypeError, ValueError):
                    # Skip rows with non-numeric values returned as unexpected types
                    continue

                if approved <= 0:
                    continue

                variance = ((spent - approved) / approved) * 100

                budgets.append(
                    {
                        "department": budget.get("dept", "Unknown"),
                        "category": budget.get("category", "N/A"),
                        "approved": approved,
                        "spent": spent,
                        "variance_percent": round(variance, 2),
                        "status": "over" if variance > 0 else "under",
                        "quarter": budget.get("quarter", "N/A"),
                        "year": budget.get("year", datetime.now().year),
                    }
                )
            return sorted(
                budgets, key=lambda x: abs(x["variance_percent"]), reverse=True
            )
        except Exception as e:
            print(f"Error in get_budget_analysis: {e}")
            return []

    def get_overdue_invoices(self, org_id: Optional[int] = None) -> Dict:
        """Get overdue invoices summary. Optionally scope by organization_id."""
        try:
            q = self.db.table("invoices").select("*").eq("is_overdue", True)
            if org_id is not None:
                q = q.eq("organization_id", org_id)
            result = q.execute()

            if not result.data:
                return {"count": 0, "total_amount": 0, "invoices": []}

            df = pd.DataFrame(result.data)

            return {
                "count": len(df),
                "total_amount": float(df["amount"].sum()),
                "by_vendor": df.groupby("vendor")["amount"].sum().to_dict(),
                "oldest_days": (
                    datetime.now() - pd.to_datetime(df["due_date"]).min()
                ).days,
            }
        except Exception as e:
            print(f"Error in get_overdue_invoices: {e}")
            return {"error": str(e)}

    def get_cashflow_forecast(self, org_id: int, months: int = 3) -> Dict:
        """Simple cashflow forecast"""
        try:
            # Get historical spending
            # pass org_id into spending summary so historical spend is scoped to org
            spending_90d = self.get_spending_summary(org_id=org_id, days=90)
            monthly_burn = float(spending_90d.get("total_spent", 0)) / 3

            # Get pending invoices (receivables)
            invoices = (
                self.db.table("invoices")
                .select("*")
                .eq("organization_id", org_id)
                .eq("status", "pending")
                .execute()
            )

            pending_receivables = sum(
                inv["amount"] for inv in invoices.data if inv["amount"]
            )

            return {
                "monthly_burn_rate": monthly_burn,
                "projected_spend": monthly_burn * months,
                "pending_receivables": pending_receivables,
                "net_position": pending_receivables - (monthly_burn * months),
                "months": months,
            }
        except Exception as e:
            print(f"Error in get_cashflow_forecast: {e}")
            return {"error": str(e)}

    def get_budget_filter_options(
        self, current_user: Optional[Dict] = None
    ) -> Dict[str, List]:
        """Return distinct filter options from budgets: departments, project_ids, quarters, years.

        Works even if project_id column is missing; it will simply be empty.
        """
        try:
            # Build query and scope by organization if provided
            query = self.db.table("budgets").select("*")

            if current_user and current_user.get("organization_id"):
                query = query.eq("organization_id", current_user["organization_id"])

            res = query.execute()

            depts: set = set()
            projects: set = set()
            quarters: set = set()
            years: set = set()

            for b in res.data or []:
                d = b.get("dept")
                if d:
                    depts.add(str(d))
                # project_id may not exist in schema
                p = b.get("project_id") if isinstance(b, dict) else None
                if p:
                    projects.add(str(p))
                q = b.get("quarter")
                if q:
                    qs = str(q).upper()
                    if qs in {"Q1", "Q2", "Q3", "Q4"}:
                        quarters.add(qs)
                y = b.get("year")
                if y is not None and str(y).isdigit():
                    try:
                        years.add(int(y))
                    except Exception:
                        pass

            return {
                "departments": sorted(depts),
                "project_ids": sorted(projects),
                "quarters": sorted(quarters),
                "years": sorted(years),
            }
        except Exception as e:
            print(f"Error in get_budget_filter_options: {e}")
            return {"departments": [], "project_ids": [], "quarters": [], "years": []}

    def get_all_budgets(
        self,
        dept: Optional[str] = None,
        project_id: Optional[str] = None,
        quarter: Optional[str] = None,
        year: Optional[int] = None,
        current_user: Optional[Dict] = None,
    ) -> List[Dict]:
        """Get budgets scoped by org and role, with calculated usage."""

        try:
            # Base query
            query = self.db.table("budgets").select("*")
            # Organization scope (safe if current_user is None)
            org_id = (current_user or {}).get("organization_id")

            if org_id:
                query = query.eq("organization_id", org_id)
            if dept:
                query = query.eq("dept", dept)
            if quarter:
                query = query.eq("quarter", quarter)
            if year:
                query = query.eq("year", year)
            if project_id:
                try:
                    query = query.eq("project_id", project_id)
                except Exception:
                    pass

            result = query.execute()
            budgets: List[Dict] = []

            # Role restriction: managers/employees see only assigned projects
            assigned = set()
            if current_user and (is_manager(current_user) or is_employee(current_user)):
                assigned = self.ac.get_assigned_projects(current_user.get("id"), org_id)

            for budget in result.data or []:
                # if current_user and (
                #     is_manager(current_user) or is_employee(current_user)
                # ):
                #     if (
                #         budget.get("project_id")
                #         and budget.get("project_id") not in assigned
                #     ):
                #         continue

                approved_raw = budget.get("approved_amount")
                spent_raw = budget.get("actual_spent")
                try:
                    approved = float(approved_raw) if approved_raw is not None else 0.0
                    spent = float(spent_raw) if spent_raw is not None else 0.0
                except (TypeError, ValueError):
                    continue

                remaining = approved - spent
                usage_percent = (spent / approved * 100) if approved > 0 else 0

                budgets.append(
                    {
                        "id": budget.get("id"),
                        "department": budget.get("dept", "Unknown"),
                        "category": budget.get("category", "General"),
                        "approved_amount": approved,
                        "actual_spent": spent,
                        "remaining": remaining,
                        "usage_percent": round(usage_percent, 2),
                        "quarter": budget.get("quarter", "N/A"),
                        "year": budget.get("year", datetime.now().year),
                        "is_over_budget": spent > approved,
                        "is_near_limit": usage_percent >= 90,
                        "project_id": budget.get("project_id"),
                        "organization_id": budget.get("organization_id"),
                    }
                )

            return sorted(budgets, key=lambda x: x["usage_percent"], reverse=True)
        except Exception as e:
            print(f"Error in get_all_budgets: {e}")
            return []

    def get_budget_status(self, org_id):
        """Get budget vs actual for organization"""
        result = (
            self.db.table("budgets").select("*").eq("organization_id", org_id).execute()
        )

        budgets = []
        for budget in result.data:
            if budget["approved_amount"] > 0:
                variance = (
                    (budget["actual_spent"] - budget["approved_amount"])
                    / budget["approved_amount"]
                    * 100
                )
                budgets.append(
                    {
                        "department": budget["dept"],
                        "approved": budget["approved_amount"],
                        "spent": budget["actual_spent"],
                        "variance_percent": variance,
                        "status": "over" if variance > 0 else "under",
                    }
                )

        return budgets

    def get_budget_by_id(self, budget_id: str) -> Optional[Dict]:
        """Get a specific budget by ID"""
        try:
            result = self.db.table("budgets").select("*").eq("id", budget_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error in get_budget_by_id: {e}")
            return None

    def create_budget(
        self,
        department: str,
        approved_amount: float,
        category: str = "General",
        project_id: Optional[str] = None,
        quarter: str = None,
        year: int = None,
        current_user: Optional[Dict] = None,
    ) -> Dict:
        """Create a new budget (admin; managers only for assigned projects)."""
        try:
            if not current_user or not current_user.get("organization_id"):
                return {"success": False, "error": "Unauthorized"}

            if not project_id or not self.ac.is_project_manager(
                current_user, project_id
            ):
                return {"success": False, "error": "Not allowed for this project"}

            if year is None:
                year = datetime.now().year
            if quarter is None:
                current_month = datetime.now().month
                quarter = f"Q{(current_month - 1) // 3 + 1}"

            data = {
                "dept": department,
                "category": category,
                "approved_amount": approved_amount,
                "actual_spent": 0,
                "quarter": quarter,
                "year": year,
                "project_id": project_id,
                "organization_id": current_user["organization_id"],
            }
            # ...existing insert with project_id fallback if needed...
            result = self.db.table("budgets").insert(data).execute()
            return {"success": True, "data": result.data[0] if result.data else None}
        except Exception as e:
            print(f"Error in create_budget: {e}")
            return {"success": False, "error": str(e)}

    def update_budget(
        self,
        budget_id: str,
        department: str = None,
        approved_amount: float = None,
        actual_spent: float = None,
        category: str = None,
        project_id: Optional[str] = None,
        quarter: str = None,
        year: int = None,
        current_user: Optional[Dict] = None,
    ) -> Dict:
        """Update budget with role checks."""
        try:
            if not current_user:
                return {"success": False, "error": "Unauthorized"}
            # Load target
            cur = (
                self.db.table("budgets")
                .select("*")
                .eq("id", budget_id)
                .limit(1)
                .execute()
            )
            if not cur.data:
                return {"success": False, "error": "Budget not found"}
            target = cur.data[0]
            if not self.ac.can_edit_budget(current_user, target):
                return {"success": False, "error": "Forbidden"}

            data = {}
            if department is not None:
                data["dept"] = department
            if approved_amount is not None:
                data["approved_amount"] = approved_amount
            if actual_spent is not None:
                data["actual_spent"] = actual_spent
            if category is not None:
                data["category"] = category
            if project_id is not None:
                data["project_id"] = project_id
            if quarter is not None:
                data["quarter"] = quarter
            if year is not None:
                data["year"] = year

            result = self.db.table("budgets").update(data).eq("id", budget_id).execute()
            return {"success": True, "data": result.data[0] if result.data else None}
        except Exception as e:
            print(f"Error in update_budget: {e}")
            return {"success": False, "error": str(e)}

    def delete_budget(
        self, budget_id: str, current_user: Optional[Dict] = None
    ) -> Dict:
        """Delete a budget with role checks."""
        try:
            if not current_user:
                return {"success": False, "error": "Unauthorized"}
            cur = (
                self.db.table("budgets")
                .select("*")
                .eq("id", budget_id)
                .limit(1)
                .execute()
            )
            if not cur.data:
                return {"success": False, "error": "Budget not found"}
            target = cur.data[0]
            if not self.ac.can_delete_budget(current_user, target):
                return {"success": False, "error": "Forbidden"}
            self.db.table("budgets").delete().eq("id", budget_id).execute()
            return {"success": True}
        except Exception as e:
            print(f"Error in delete_budget: {e}")
            return {"success": False, "error": str(e)}

    def calculate_budget_usage(
        self,
        department: str = None,
        category: str = None,
        project_id: Optional[str] = None,
        quarter: Optional[str] = None,
        year: Optional[int] = None,
        org_id: Optional[int] = None,
    ) -> Dict:
        """Calculate total budget usage with optional filters."""
        try:
            query = self.db.table("budgets").select("*")

            if org_id is not None:
                query = query.eq("organization_id", org_id)

            if department:
                query = query.eq("dept", department)
            if category:
                query = query.eq("category", category)
            if quarter:
                query = query.eq("quarter", quarter)
            if year:
                query = query.eq("year", year)

            if project_id:
                try:
                    result = query.eq("project_id", project_id).execute()
                except Exception:
                    result = query.execute()
            else:
                result = query.execute()

            if not result.data:
                return {
                    "total_approved": 0,
                    "total_spent": 0,
                    "total_remaining": 0,
                    "overall_usage_percent": 0,
                }

            total_approved = sum(
                float(b.get("approved_amount", 0)) for b in result.data
            )
            total_spent = sum(float(b.get("actual_spent", 0)) for b in result.data)
            total_remaining = total_approved - total_spent
            usage_percent = (
                (total_spent / total_approved * 100) if total_approved > 0 else 0
            )

            return {
                "total_approved": total_approved,
                "total_spent": total_spent,
                "total_remaining": total_remaining,
                "overall_usage_percent": round(usage_percent, 2),
                "count": len(result.data),
            }
        except Exception as e:
            print(f"Error in calculate_budget_usage: {e}")
            return {"error": str(e)}

    def submit_spending_proposal(
        self,
        current_user: Dict,
        project_id: str,
        dept: str,
        amount: float,
        description: str,
    ) -> Dict:
        try:
            if not current_user or not self.ac.can_submit_proposal(
                current_user, project_id
            ):
                return {"success": False, "error": "Forbidden"}
            data = {
                "project_id": project_id,
                "dept": dept,
                "amount": amount,
                "description": description,
                "status": "pending",
                "requested_by": current_user["id"],
                "organization_id": current_user["organization_id"],
            }
            r = self.db.table("spending_proposals").insert(data).execute()
            proposal = r.data[0]

            # Create approval_workflow placeholder (manager will act)
            self.db.table("approval_workflows").insert(
                {
                    "proposal_id": proposal["id"],
                    "approver_id": None,
                    "approval_level": "manager",
                    "status": "pending",
                    "organization_id": current_user["organization_id"],
                    "comments": "Awaiting manager approval",
                }
            ).execute()
            return {"success": True, "data": proposal}
        except Exception as e:
            print(f"Error in submit_spending_proposal: {e}")
            return {"success": False, "error": str(e)}

    def get_my_proposals(self, current_user: Dict) -> List[Dict]:
        try:
            res = (
                self.db.table("spending_proposals")
                .select("*")
                .eq("requested_by", current_user["id"])
                .order("created_at", desc=True)
                .execute()
            )
            return res.data or []
        except Exception as e:
            print(f"Error in get_my_proposals: {e}")
            return []

    def get_pending_proposals_for_manager(self, current_user: Dict) -> List[Dict]:
        """Managers see pending proposals for their assigned projects."""
        try:
            if not (current_user and is_manager(current_user)) and not is_admin(
                current_user
            ):
                return []
            assigned = (
                self.ac.get_assigned_projects(
                    current_user["id"], current_user["organization_id"]
                )
                if is_manager(current_user)
                else None
            )
            q = (
                self.db.table("spending_proposals")
                .select("*")
                .eq("status", "pending")
                .eq("organization_id", current_user["organization_id"])
            )
            res = q.execute()
            rows = res.data or []
            if is_manager(current_user):
                rows = [r for r in rows if r.get("project_id") in assigned]
            return rows
        except Exception as e:
            print(f"Error in get_pending_proposals_for_manager: {e}")
            return []

    def get_proposals_history_for_manager(self, current_user: Dict) -> List[Dict]:
        """Managers/admins see non-pending proposals in their org (scoped to assigned projects for managers)."""
        try:
            if not (
                current_user and (is_manager(current_user) or is_admin(current_user))
            ):
                return []
            assigned = (
                self.ac.get_assigned_projects(
                    current_user["id"], current_user["organization_id"]
                )
                if is_manager(current_user)
                else None
            )
            q = (
                self.db.table("spending_proposals")
                .select("*")
                .neq("status", "pending")
                .eq("organization_id", current_user["organization_id"])
                .order("updated_at", desc=True)
            )
            res = q.execute()
            rows = res.data or []
            if is_manager(current_user):
                rows = [r for r in rows if r.get("project_id") in assigned]
            return rows
        except Exception as e:
            print(f"Error in get_proposals_history_for_manager: {e}")
            return []

    def decide_proposal(
        self, current_user: Dict, proposal_id: str, decision: str, comments: str = ""
    ) -> Dict:
        """Approve/Reject proposal. Only project manager or admin."""
        try:
            # Load proposal
            pr = (
                self.db.table("spending_proposals")
                .select("*")
                .eq("id", proposal_id)
                .limit(1)
                .execute()
            )
            if not pr.data:
                return {"success": False, "error": "Proposal not found"}
            proposal = pr.data[0]
            if not (
                is_admin(current_user)
                or self.ac.is_project_manager(current_user, proposal["project_id"])
            ):
                return {"success": False, "error": "Forbidden"}

            new_status = "approved" if decision == "approve" else "rejected"
            upd = (
                self.db.table("spending_proposals")
                .update({"status": new_status, "approved_by": current_user["id"]})
                .eq("id", proposal_id)
                .execute()
            )

            # Archive approval step
            self.db.table("approval_workflows").insert(
                {
                    "proposal_id": proposal_id,
                    "approver_id": current_user["id"],
                    "approval_level": "manager",
                    "status": new_status,
                    "comments": comments or (f"{new_status.title()} by manager"),
                    "organization_id": current_user["organization_id"],
                    "approved_at": datetime.now().isoformat(),
                }
            ).execute()
            return {"success": True, "data": upd.data[0] if upd.data else None}
        except Exception as e:
            print(f"Error in decide_proposal: {e}")
            return {"success": False, "error": str(e)}

    def get_approval_history(self, proposal_id: str) -> List[Dict]:
        try:
            r = (
                self.db.table("approval_workflows")
                .select("*")
                .eq("proposal_id", proposal_id)
                .order("created_at", desc=True)
                .execute()
            )
            return r.data or []
        except Exception as e:
            print(f"Error in get_approval_history: {e}")
            return []

    # --- File upload support for proposal documentation ---
    def upload_proposal_document(
        self, current_user: Dict, file_bytes: bytes, filename: str
    ) -> Dict:
        """Upload proposal documentation to Supabase Storage and return a public URL.
        Expects a bucket named 'proposal_docs' to exist. Returns {success, url|error}.
        """
        try:
            bucket = "CFO"
            # sanitize filename
            safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
            ts = int(time.time())
            org_id = (current_user or {}).get("organization_id") or "no_org"
            user_id = (current_user or {}).get("id") or "no_user"
            path = f"{org_id}/{user_id}/{ts}_{safe_name}"
            # Upload
            self.db.storage.from_(bucket).upload(
                path,
                file_bytes,
                {
                    "contentType": "application/octet-stream",
                    "upsert": True,
                },
            )
            public_url = self.db.storage.from_(bucket).get_public_url(path)
            url = (
                public_url
                if isinstance(public_url, str)
                else public_url.get("publicUrl")
            )
            return {"success": True, "url": url}
        except Exception as e:
            print(f"Error in upload_proposal_document: {e}")
            return {"success": False, "error": str(e)}

    def get_alerts(self, org_id):
        """Get unread alerts"""
        return (
            self.db.table("alerts")
            .select("*")
            .eq("organization_id", org_id)
            .eq("is_read", False)
            .order("created_at", desc=True)
            .execute()
            .data
        )

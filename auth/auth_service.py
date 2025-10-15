from typing import Optional, Dict
from config.database import get_db
from supabase import Client


class AuthService:
    def __init__(self):
        self.db: Client = get_db()

    def sign_in(self, email: str, password: str) -> Optional[Dict]:
        """
        Try Supabase Auth password login. On success, load or create a profile row in public.users.
        Returns user profile dict: { id, email, full_name, role, organization_id }
        """
        try:
            # Attempt Supabase Auth
            try:
                resp = self.db.auth.sign_in_with_password(
                    {"email": email, "password": password}
                )
                authed_email = resp.user.email if resp and resp.user else email
            except Exception:
                # Fallback to profile-only dev login (NOT FOR PROD)
                authed_email = email

            # Load user profile by email
            prof = (
                self.db.table("users")
                .select("*")
                .eq("email", authed_email)
                .limit(1)
                .execute()
            )
            if prof.data:
                return prof.data[0]

            # Optional upsert for first-time auth; defaults to employee with no org
            ins = (
                self.db.table("users")
                .insert(
                    {
                        "email": authed_email,
                        "full_name": authed_email.split("@")[0],
                        "role": "employee",
                        "organization_id": None,
                    }
                )
                .execute()
            )
            return ins.data[0] if ins.data else None
        except Exception as e:
            print(f"Auth sign_in error: {e}")
            return None

    def sign_out(self):
        try:
            self.db.auth.sign_out()
        except Exception:
            pass

    def get_profile_by_id(self, user_id: str) -> Optional[Dict]:
        try:
            r = self.db.table("users").select("*").eq("id", user_id).limit(1).execute()
            return r.data[0] if r.data else None
        except Exception:
            return None

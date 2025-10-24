import os
from config.enviroment import get_config
from services.data_service import DataService
from services.stripe_service import StripeService

"""
Simulate a transfer or transfer+payout for a given employee.
Requires env vars:
- ORG_ID
- USER_ID (employee receiving funds)
- AMOUNT (USD float)
- PROJECT_ID (optional)
- STRIPE_DRY_RUN=1 to avoid real money movement
- STRIPE_AUTOPAYOUT=1 to perform payout immediately; otherwise transfer only

Usage (cmd.exe):
  set STRIPE_DRY_RUN=1
  set ORG_ID=...
  set USER_ID=...
  set PROJECT_ID=...
  set AMOUNT=25
  python -m scripts.simulate_payout
"""


def main():
    org_id = get_config("ORG_ID")
    user_id = get_config("USER_ID")
    amount = float(get_config("AMOUNT", "0"))
    project_id = get_config("PROJECT_ID")
    autopayout = get_config("STRIPE_AUTOPAYOUT", "0") in {"1", "true", "True"}

    if not org_id or not user_id or amount <= 0:
        print("Missing ORG_ID/USER_ID/AMOUNT")
        return

    ds = DataService()
    acct_id = ds._get_user_stripe_account(user_id)
    if not acct_id:
        print("Employee has no connected account (stripe_account_id)")
        return

    ss = StripeService()
    if autopayout:
        res = ss.transfer_and_payout(
            organization_id=str(org_id),
            to_account_id=acct_id,
            amount_usd=amount,
            currency="USD",
            project_id=project_id,
            employee_id=str(user_id),
            created_by="simulate_script",
            proposal_id=None,
            idempotency_key=f"simulate_{user_id}_{amount}",
        )
    else:
        res = ss.transfer_only(
            organization_id=str(org_id),
            to_account_id=acct_id,
            amount_usd=amount,
            currency="USD",
            project_id=project_id,
            employee_id=str(user_id),
            created_by="simulate_script",
            proposal_id=None,
            idempotency_key=f"simulate_{user_id}_{amount}",
            description="Simulation transfer",
        )

    print(res)


if __name__ == "__main__":
    main()

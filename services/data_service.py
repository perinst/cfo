# services/data_service.py
from config.database import get_db
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class DataService:
    def __init__(self):
        self.db = get_db()
    
    def get_spending_summary(self, days: int = 30) -> Dict:
        """Get spending summary for last N days"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            result = self.db.table('transactions')\
                .select("*")\
                .gte('date', start_date.date().isoformat())\
                .lte('date', end_date.date().isoformat())\
                .execute()
            
            if not result.data:
                return {
                    "total_spent": 0,
                    "transaction_count": 0,
                    "avg_transaction": 0,
                    "by_category": {},
                    "by_status": {}
                }
            
            df = pd.DataFrame(result.data)
            
            return {
                "total_spent": float(df['amount'].sum()),
                "transaction_count": len(df),
                "avg_transaction": float(df['amount'].mean()),
                "by_category": df.groupby('category')['amount'].sum().to_dict(),
                "by_status": df.groupby('status')['amount'].count().to_dict(),
                "top_merchants": df.groupby('merchant')['amount'].sum().nlargest(5).to_dict()
            }
        except Exception as e:
            print(f"Error in get_spending_summary: {e}")
            return {"error": str(e)}
    
    def get_budget_analysis(self) -> List[Dict]:
        """Analyze budget variance"""
        try:
            result = self.db.table('budgets').select("*").execute()
            
            budgets = []
            for budget in result.data:
                if budget['approved_amount'] and budget['approved_amount'] > 0:
                    variance = ((budget['actual_spent'] - budget['approved_amount']) 
                               / budget['approved_amount'] * 100)
                    budgets.append({
                        "department": budget['dept'],
                        "category": budget.get('category', 'N/A'),
                        "approved": float(budget['approved_amount']),
                        "spent": float(budget['actual_spent']),
                        "variance_percent": round(variance, 2),
                        "status": "over" if variance > 0 else "under",
                        "quarter": budget.get('quarter', 'N/A'),
                        "year": budget.get('year', datetime.now().year)
                    })
            
            return sorted(budgets, key=lambda x: abs(x['variance_percent']), reverse=True)
        except Exception as e:
            print(f"Error in get_budget_analysis: {e}")
            return []
    
    def get_overdue_invoices(self) -> Dict:
        """Get overdue invoices summary"""
        try:
            result = self.db.table('invoices')\
                .select("*")\
                .eq('is_overdue', True)\
                .execute()
            
            if not result.data:
                return {
                    "count": 0,
                    "total_amount": 0,
                    "invoices": []
                }
            
            df = pd.DataFrame(result.data)
            
            return {
                "count": len(df),
                "total_amount": float(df['amount'].sum()),
                "by_vendor": df.groupby('vendor')['amount'].sum().to_dict(),
                "oldest_days": (datetime.now() - pd.to_datetime(df['due_date']).min()).days
            }
        except Exception as e:
            print(f"Error in get_overdue_invoices: {e}")
            return {"error": str(e)}
    
    def get_cashflow_forecast(self, months: int = 3) -> Dict:
        """Simple cashflow forecast"""
        try:
            # Get historical spending
            spending_90d = self.get_spending_summary(90)
            monthly_burn = spending_90d['total_spent'] / 3
            
            # Get pending invoices (receivables)
            invoices = self.db.table('invoices')\
                .select("*")\
                .eq('status', 'pending')\
                .execute()
            
            pending_receivables = sum(inv['amount'] for inv in invoices.data if inv['amount'])
            
            return {
                "monthly_burn_rate": monthly_burn,
                "projected_spend": monthly_burn * months,
                "pending_receivables": pending_receivables,
                "net_position": pending_receivables - (monthly_burn * months),
                "months": months
            }
        except Exception as e:
            print(f"Error in get_cashflow_forecast: {e}")
            return {"error": str(e)}
# agents/cashflow_agent.py
from agents.base_agent import BaseAgent
import pandas as pd
from datetime import datetime, timedelta

class CashflowAgent(BaseAgent):
    """📊 Cashflow Forecaster - predicts cash flow and runway"""
    
    def __init__(self):
        super().__init__(
            name="Cashflow Forecaster Agent",
            description="Analyzes and forecasts cash flow"
        )
    
    def analyze(self, org_id: str, query: str):
        """Analyze cashflow for organization"""
        # Get transaction data
        transactions = self._get_transactions(org_id)
        invoices = self._get_invoices(org_id)
        
        # Calculate metrics
        metrics = self._calculate_metrics(transactions, invoices)
        
        # Generate AI insights
        prompt = f"""
        As a CFO, analyze this cashflow data:
        
        Monthly burn rate: ${metrics['monthly_burn']:,.2f}
        Monthly income: ${metrics['monthly_income']:,.2f}
        Net cashflow: ${metrics['net_flow']:,.2f}
        Current runway: {metrics['runway_months']:.1f} months
        
        Outstanding receivables: ${metrics['receivables']:,.2f}
        Overdue invoices: {metrics['overdue_count']}
        
        User question: {query}
        
        Provide specific insights and recommendations.
        """
        
        response = self.llm.invoke(prompt)
        return response.content
    
    def _get_transactions(self, org_id):
        """Get transaction data from database"""
        result = self.db.table('transactions')\
            .select("*")\
            .eq('organization_id', org_id)\
            .gte('date', (datetime.now() - timedelta(days=90)).date().isoformat())\
            .execute()
        return result.data
    
    def _get_invoices(self, org_id):
        """Get invoice data"""
        result = self.db.table('invoices')\
            .select("*")\
            .eq('organization_id', org_id)\
            .execute()
        return result.data
    
    def _calculate_metrics(self, transactions, invoices):
        """Calculate cashflow metrics"""
        if transactions:
            df = pd.DataFrame(transactions)
            monthly_burn = df['amount'].sum() / 3  # 90 days / 3
        else:
            monthly_burn = 0
        
        # Calculate receivables
        pending_invoices = [inv for inv in invoices if inv['status'] == 'pending']
        receivables = sum(inv['amount'] for inv in pending_invoices)
        
        # Count overdue
        overdue = [inv for inv in invoices if inv.get('is_overdue')]
        
        return {
            'monthly_burn': monthly_burn,
            'monthly_income': receivables / 3,  # Assume 3 month average
            'net_flow': (receivables / 3) - monthly_burn,
            'runway_months': 12 if monthly_burn == 0 else 100000 / monthly_burn,  # Assume 100k balance
            'receivables': receivables,
            'overdue_count': len(overdue)
        }
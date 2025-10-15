# agents/alert_agent.py
from agents.base_agent import BaseAgent
from datetime import datetime

class AlertAgent(BaseAgent):
    """⚠️ Alert & Risk Agent - monitors and alerts on issues"""
    
    def __init__(self):
        super().__init__(
            name="Alert & Risk Agent",
            description="Monitors alerts and risks"
        )
    
    def analyze(self, org_id: str, query: str):
        """Check and analyze alerts"""
        # Get current alerts
        alerts = self._get_active_alerts(org_id)
        
        # Check for new risks
        risks = self._check_risks(org_id)
        
        # Generate alert summary
        prompt = f"""
        Current alert status:
        
        Active alerts: {len(alerts)}
        Critical: {len([a for a in alerts if a['severity'] == 'critical'])}
        High priority: {len([a for a in alerts if a['severity'] == 'high'])}
        
        Recent alerts:
        {self._format_alerts(alerts[:5])}
        
        Identified risks:
        {risks}
        
        User question: {query}
        
        Provide risk assessment and recommendations.
        """
        
        response = self.llm.invoke(prompt)
        return response.content
    
    def _get_active_alerts(self, org_id):
        """Get active alerts from database"""
        result = self.db.table('alerts')\
            .select("*")\
            .eq('organization_id', org_id)\
            .eq('is_read', False)\
            .order('created_at', desc=True)\
            .execute()
        return result.data
    
    def _check_risks(self, org_id):
        """Check for various risks"""
        risks = []
        
        # Check budget overruns
        budgets = self.db.table('budgets')\
            .select("*")\
            .eq('organization_id', org_id)\
            .execute().data
        
        for budget in budgets:
            if budget['actual_spent'] > budget['approved_amount'] * 1.2:
                risks.append(f"{budget['dept']} is 20%+ over budget")
        
        # Check overdue invoices
        invoices = self.db.table('invoices')\
            .select("*")\
            .eq('organization_id', org_id)\
            .eq('is_overdue', True)\
            .execute().data
        
        if len(invoices) > 5:
            total_overdue = sum(inv['amount'] for inv in invoices)
            risks.append(f"{len(invoices)} overdue invoices totaling ${total_overdue:,.2f}")
        
        return risks
    
    def _format_alerts(self, alerts):
        """Format alerts for display"""
        if not alerts:
            return "No recent alerts"
        
        formatted = []
        for alert in alerts:
            formatted.append(f"- [{alert['severity']}] {alert['message']}")
        
        return "\n".join(formatted)
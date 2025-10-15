# agents/budget_agent.py
from agents.base_agent import BaseAgent
import pandas as pd

class BudgetAgent(BaseAgent):
    """🧾 Budget Planning Agent - manages and optimizes budgets"""
    
    def __init__(self):
        super().__init__(
            name="Budget Planning Agent",
            description="Budget planning and variance analysis"
        )
    
    def analyze(self, org_id: str, query: str):
        """Analyze budget performance"""
        # Get budget data
        budgets = self._get_budgets(org_id)
        
        # Calculate variance
        analysis = self._analyze_variance(budgets)
        
        # Generate recommendations
        prompt = f"""
        Budget analysis:
        
        Total budgets: {len(budgets)}
        Over budget: {analysis['over_count']} departments
        Under budget: {analysis['under_count']} departments
        Average variance: {analysis['avg_variance']:.1f}%
        
        Worst performers:
        {self._format_worst_performers(analysis['worst'])}
        
        User question: {query}
        
        Provide budget optimization recommendations.
        """
        
        response = self.llm.invoke(prompt)
        return response.content
    
    def _get_budgets(self, org_id):
        """Get budget data"""
        result = self.db.table('budgets')\
            .select("*")\
            .eq('organization_id', org_id)\
            .execute()
        return result.data
    
    def _analyze_variance(self, budgets):
        """Analyze budget variance"""
        over_budget = []
        under_budget = []
        variances = []
        
        for budget in budgets:
            if budget['approved_amount'] > 0:
                variance = ((budget['actual_spent'] - budget['approved_amount']) 
                           / budget['approved_amount'] * 100)
                variances.append(variance)
                
                if variance > 0:
                    over_budget.append({
                        'dept': budget['dept'],
                        'variance': variance,
                        'amount_over': budget['actual_spent'] - budget['approved_amount']
                    })
                else:
                    under_budget.append(budget)
        
        # Sort to get worst performers
        over_budget.sort(key=lambda x: x['variance'], reverse=True)
        
        return {
            'over_count': len(over_budget),
            'under_count': len(under_budget),
            'avg_variance': sum(variances) / len(variances) if variances else 0,
            'worst': over_budget[:3]
        }
    
    def _format_worst_performers(self, worst):
        """Format worst performers"""
        if not worst:
            return "All departments within budget"
        
        formatted = []
        for dept in worst:
            formatted.append(f"- {dept['dept']}: {dept['variance']:.1f}% over (${dept['amount_over']:,.2f})")
        
        return "\n".join(formatted)
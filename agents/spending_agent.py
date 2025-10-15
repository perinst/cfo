# agents/spending_agent.py
from agents.base_agent import BaseAgent
import pandas as pd
import json

class SpendingAgent(BaseAgent):
    """💸 Spending Analyzer - analyzes expenses and finds savings"""
    
    def __init__(self):
        super().__init__(
            name="Spending Analyzer Agent",
            description="Analyzes spending patterns and optimization"
        )
    
    def analyze(self, org_id: str, query: str):
        """Analyze spending patterns"""
        # Get data
        transactions = self._get_recent_transactions(org_id)
        
        if not transactions:
            return "No transaction data available for analysis."
        
        # Analyze
        analysis = self._analyze_spending(transactions)
        
        # Generate insights
        prompt = f"""
        Analyze this spending data and answer the user's question:
        
        Total spent (30 days): ${analysis['total']:,.2f}
        Categories: {json.dumps(analysis['by_category'], indent=2)}
        Top merchants: {json.dumps(analysis['top_merchants'], indent=2)}
        Unusual transactions: {analysis['anomalies']}
        
        User question: {query}
        
        Provide:
        1. Direct answer to the question
        2. Key insights
        3. Cost saving opportunities
        4. Specific recommendations
        """
        
        response = self.llm.invoke(prompt)
        return response.content
    
    def _get_recent_transactions(self, org_id):
        """Get recent transactions"""
        result = self.db.table('transactions')\
            .select("*")\
            .eq('organization_id', org_id)\
            .gte('date', (datetime.now() - timedelta(days=30)).date().isoformat())\
            .execute()
        return result.data
    
    def _analyze_spending(self, transactions):
        """Analyze spending patterns"""
        df = pd.DataFrame(transactions)
        
        return {
            'total': float(df['amount'].sum()),
            'by_category': df.groupby('category')['amount'].sum().to_dict(),
            'top_merchants': df.groupby('merchant')['amount'].sum().nlargest(5).to_dict(),
            'anomalies': len(df[df['fraud_flag'] == 1])
        }
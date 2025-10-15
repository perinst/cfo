# agents/cfo_agent.py - FIXED VERSION
from agents.base_agent import BaseAgent
from config.llm_config import get_llm
from services.data_service import DataService
from langchain.agents import Tool
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import json


class CFOAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="CFO Assistant", description="Financial analysis and insights"
        )
        self.llm = get_llm(temperature=0.1)
        self.data_service = DataService()
        self.org_id = None  # Will be set when analyzing

    def analyze_spending(self, query: str, org_id: str) -> str:
        """Analyze spending with AI insights"""
        # Get data from database
        spending_data = self.data_service.get_spending_by_org(org_id)

        if not spending_data:
            return "No spending data available"

        # Create prompt with real data
        prompt = f"""
        As a CFO, analyze this spending data from our database:
        
        Total Spent (30 days): ${spending_data['total_spent']:,.2f}
        Number of Transactions: {spending_data['transaction_count']}
        Average Transaction: ${spending_data['avg_transaction']:,.2f}
        
        Spending by Category:
        {json.dumps(spending_data['by_category'], indent=2)}
        
        Top Merchants:
        {json.dumps(spending_data['top_merchants'], indent=2)}
        
        Fraud Alerts: {spending_data['fraud_flagged']} transactions flagged
        
        User Question: {query}
        
        Provide:
        1. Key insights and trends
        2. Risk areas or concerns  
        3. Cost optimization recommendations
        4. Action items for the finance team
        """

        # Get AI analysis
        response = self.llm.invoke(prompt)
        return response.content

    def analyze_budget(self, query: str, org_id: str) -> str:
        """Analyze budget variance"""
        budgets = self.data_service.get_budget_status(org_id)

        prompt = PromptTemplate(
            input_variables=["budgets", "query"],
            template="""
            As a CFO, analyze these budget variances:
            
            {budgets}
            
            Question: {query}
            
            Focus on:
            1. Departments significantly over/under budget
            2. Root causes
            3. Action items
            """,
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)
        response = chain.run(budgets=json.dumps(budgets[:10]), query=query)

        return response

    def forecast_cashflow(self, query: str, org_id: str) -> str:
        """Cashflow forecasting"""
        forecast = self.data_service.get_cashflow_forecast(org_id)

        prompt = PromptTemplate(
            input_variables=["forecast", "query"],
            template="""
            Based on this cashflow data, provide CFO-level analysis:
            
            {forecast}
            
            Question: {query}
            
            Include:
            1. Runway analysis
            2. Risk factors
            3. Recommendations for improvement
            """,
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)
        response = chain.run(forecast=json.dumps(forecast), query=query)

        return response

    def check_budget_health(self, org_id: str) -> str:
        """Check budget status with AI recommendations"""
        budget_data = self.data_service.get_budget_status(org_id)

        over_budget = [b for b in budget_data if b["status"] == "over"]

        prompt = f"""
        Analyze our budget performance:
        
        Departments over budget: {len(over_budget)}
        
        Details:
        {json.dumps(over_budget[:5], indent=2)}
        
        Provide specific recommendations to get back on track.
        """

        response = self.llm.invoke(prompt)
        return response.content

    def get_alerts_summary(self, org_id: str) -> str:
        """Get and analyze alerts"""
        alerts = self.data_service.get_alerts(org_id)

        if not alerts:
            return "No active alerts"

        critical = [a for a in alerts if a["severity"] == "critical"]
        high = [a for a in alerts if a["severity"] == "high"]

        return f"""
        🚨 Active Alerts:
        - Critical: {len(critical)}
        - High: {len(high)}
        - Total: {len(alerts)}
        
        Most Recent:
        {alerts[0]['message'] if alerts else 'None'}
        """

    def chat(self, message: str, org_id: str = None) -> str:
        """Main chat interface - routes to appropriate function"""
        # Set org_id if provided
        if org_id:
            self.org_id = org_id

        if not self.org_id:
            return "Please select an organization first."

        message_lower = message.lower()

        try:
            if any(
                word in message_lower
                for word in ["spend", "expense", "cost", "purchase"]
            ):
                response = self.analyze_spending(message, self.org_id)
            elif any(
                word in message_lower
                for word in ["budget", "variance", "over", "under"]
            ):
                response = self.analyze_budget(message, self.org_id)
            elif any(
                word in message_lower for word in ["cash", "flow", "forecast", "runway"]
            ):
                response = self.forecast_cashflow(message, self.org_id)
            elif any(
                word in message_lower for word in ["alert", "warning", "critical"]
            ):
                response = self.get_alerts_summary(self.org_id)
            elif any(word in message_lower for word in ["health", "status"]):
                response = self.check_budget_health(self.org_id)
            else:
                # General query - analyze spending by default
                response = self.analyze_spending(message, self.org_id)

            # Save to history if method exists
            if hasattr(self, "save_chat_history"):
                self.save_chat_history(message, response)

            return response

        except Exception as e:
            return f"I encountered an error analyzing your request: {str(e)}"

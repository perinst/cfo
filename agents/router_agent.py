# agents/router_agent.py
from agents.base_agent import BaseAgent
from agents.cashflow_agent import CashflowAgent
from agents.spending_agent import SpendingAgent
from agents.alert_agent import AlertAgent
from agents.budget_agent import BudgetAgent
from agents.policy_agent import PolicyAgent


class RouterAgent(BaseAgent):
    """🧠 Main router - directs queries to appropriate agents"""

    def __init__(self):
        super().__init__(
            name="CFO Router Agent",
            description="Main orchestrator that routes requests",
        )

        # Initialize all sub-agents
        self.agents = {
            "cashflow": CashflowAgent(),
            "spending": SpendingAgent(),
            "alert": AlertAgent(),
            "budget": BudgetAgent(),
            "policy": PolicyAgent(),
        }

    def route_query(self, query: str, org_id: str):
        """Analyze query and route to appropriate agent"""
        query_lower = query.lower()

        # Determine which agent to use based on keywords
        if any(word in query_lower for word in ["cash", "flow", "runway", "forecast"]):
            return self.agents["cashflow"].analyze(org_id, query)

        elif any(
            word in query_lower for word in ["spend", "expense", "cost", "purchase"]
        ):
            return self.agents["spending"].analyze(org_id, query)

        elif any(word in query_lower for word in ["alert", "warning", "risk", "fraud"]):
            return self.agents["alert"].analyze(org_id, query)

        elif any(word in query_lower for word in ["budget", "variance", "allocation"]):
            return self.agents["budget"].analyze(org_id, query)

        elif any(
            word in query_lower for word in ["policy", "rule", "compliance", "approval"]
        ):
            return self.agents["policy"].analyze(org_id, query)

        else:
            # Use LLM to determine best agent
            return self._smart_route(query, org_id)

    def _smart_route(self, query: str, org_id: str):
        """Use AI to determine best agent"""
        prompt = f"""
        User query: {query}
        
        Available agents:
        1. Cashflow - for cash flow, forecasting, runway
        2. Spending - for expenses, transactions, costs
        3. Alert - for warnings, risks, anomalies
        4. Budget - for budget planning, variance
        5. Policy - for rules, compliance, approvals
        
        Which agent should handle this? Return only the agent name.
        """

        response = self.llm.invoke(prompt)
        agent_name = response.content.strip().lower()

        if agent_name in self.agents:
            return self.agents[agent_name].analyze(org_id, query)
        else:
            # Default to spending agent
            return self.agents["spending"].analyze(org_id, query)

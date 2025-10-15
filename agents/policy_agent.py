# agents/policy_agent.py
from agents.base_agent import BaseAgent

class PolicyAgent(BaseAgent):
    """📚 Policy & Compliance Agent - handles rules and compliance"""
    
    def __init__(self):
        super().__init__(
            name="Policy & Compliance Agent",
            description="Policy interpretation and compliance checking"
        )
    
    def analyze(self, org_id: str, query: str):
        """Answer policy-related questions"""
        # Get policies
        policies = self._get_policies(org_id)
        
        # Search relevant policies
        relevant = self._search_policies(policies, query)
        
        # Generate response
        prompt = f"""
        Company policies:
        {self._format_policies(relevant)}
        
        User question: {query}
        
        Provide clear guidance based on company policies.
        If no specific policy exists, suggest best practices.
        """
        
        response = self.llm.invoke(prompt)
        return response.content
    
    def _get_policies(self, org_id):
        """Get policy documents"""
        result = self.db.table('policy_documents')\
            .select("*")\
            .eq('organization_id', org_id)\
            .execute()
        return result.data
    
    def _search_policies(self, policies, query):
        """Search for relevant policies"""
        query_lower = query.lower()
        relevant = []
        
        for policy in policies:
            if any(word in policy['content'].lower() for word in query_lower.split()):
                relevant.append(policy)
        
        return relevant[:3]  # Top 3 most relevant
    
    def _format_policies(self, policies):
        """Format policies for display"""
        if not policies:
            return "No specific policies found"
        
        formatted = []
        for policy in policies:
            formatted.append(f"[{policy['category']}]: {policy['content']}")
        
        return "\n".join(formatted)
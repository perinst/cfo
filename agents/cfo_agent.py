# agents/cfo_agent.py
from agents.base_agent import BaseAgent
from config.llm_config import get_deepseek_llm
from services.data_service import DataService
from langchain.agents import Tool
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import json

class CFOAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="CFO Assistant",
            description="Financial analysis and insights"
        )
        self.llm = get_deepseek_llm(temperature=0.1)
        self.data_service = DataService()
        
    def analyze_spending(self, query: str) -> str:
        """Analyze spending patterns with LLM insights"""
        # Get data
        data = self.data_service.get_spending_summary(30)
        
        # Create prompt
        prompt = PromptTemplate(
            input_variables=["data", "query"],
            template="""
            As a CFO, analyze this spending data and answer the question.
            
            Data: {data}
            Question: {query}
            
            Provide:
            1. Key findings
            2. Concerns or risks
            3. Recommendations
            
            Be specific with numbers and percentages.
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        response = chain.run(data=json.dumps(data), query=query)
        
        return response
    
    def analyze_budget(self, query: str) -> str:
        """Analyze budget variance"""
        budgets = self.data_service.get_budget_analysis()
        
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
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        response = chain.run(budgets=json.dumps(budgets[:10]), query=query)
        
        return response
    
    def forecast_cashflow(self, query: str) -> str:
        """Cashflow forecasting"""
        forecast = self.data_service.get_cashflow_forecast()
        
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
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        response = chain.run(forecast=json.dumps(forecast), query=query)
        
        return response
    
    def chat(self, message: str) -> str:
        """Main chat interface - routes to appropriate function"""
        message_lower = message.lower()
        
        try:
            if any(word in message_lower for word in ['spend', 'expense', 'cost', 'purchase']):
                response = self.analyze_spending(message)
            elif any(word in message_lower for word in ['budget', 'variance', 'over', 'under']):
                response = self.analyze_budget(message)
            elif any(word in message_lower for word in ['cash', 'flow', 'forecast', 'runway']):
                response = self.forecast_cashflow(message)
            else:
                # General query
                response = self.analyze_spending(message)
            
            # Save to history
            self.save_chat_history(message, response)
            
            return response
            
        except Exception as e:
            return f"I encountered an error analyzing your request: {str(e)}"
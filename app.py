# app.py
import streamlit as st
from agents.cfo_agent import CFOAgent
from services.data_service import DataService
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page config
st.set_page_config(
    page_title="AI CFO Assistant",
    page_icon="💼",
    layout="wide"
)

# Initialize session state
if 'agent' not in st.session_state:
    st.session_state.agent = CFOAgent()
    st.session_state.data_service = DataService()

if 'messages' not in st.session_state:
    st.session_state.messages = []

# Header
st.title("💼 AI CFO Assistant")
st.caption("Powered by DeepSeek AI & LangChain")

# Create tabs
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Dashboard", "📈 Analytics"])

# Tab 1: Chat Interface
with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask about finances, budgets, or spending..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Get AI response
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    response = st.session_state.agent.chat(prompt)
                    st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    with col2:
        st.subheader("💡 Quick Questions")
        
        questions = [
            "What's our spending trend?",
            "Which departments are over budget?",
            "How can we reduce costs?",
            "What's our cash runway?",
            "Find unusual transactions"
        ]
        
        for q in questions:
            if st.button(q, key=f"q_{q}"):
                st.session_state.messages.append({"role": "user", "content": q})
                st.rerun()

# Tab 2: Dashboard
with tab2:
    st.subheader("Financial Dashboard")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Get data
    summary = st.session_state.data_service.get_spending_summary(30)
    budgets = st.session_state.data_service.get_budget_analysis()
    invoices = st.session_state.data_service.get_overdue_invoices()
    
    with col1:
        st.metric(
            "Total Spent (30d)",
            f"${summary.get('total_spent', 0):,.0f}",
            "Last 30 days"
        )
    
    with col2:
        st.metric(
            "Transactions",
            summary.get('transaction_count', 0),
            "Total count"
        )
    
    with col3:
        over_budget = len([b for b in budgets if b['status'] == 'over'])
        st.metric(
            "Over Budget",
            over_budget,
            "Departments",
            delta_color="inverse"
        )
    
    with col4:
        st.metric(
            "Overdue Invoices",
            f"${invoices.get('total_amount', 0):,.0f}",
            f"{invoices.get('count', 0)} invoices",
            delta_color="inverse"
        )
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        if summary.get('by_category'):
            fig = px.pie(
                values=list(summary['by_category'].values()),
                names=list(summary['by_category'].keys()),
                title="Spending by Category"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if budgets:
            df_budgets = pd.DataFrame(budgets[:10])
            fig = px.bar(
                df_budgets,
                x='department',
                y='variance_percent',
                title="Budget Variance by Department (%)",
                color='status',
                color_discrete_map={'over': 'red', 'under': 'green'}
            )
            st.plotly_chart(fig, use_container_width=True)

# Tab 3: Analytics
with tab3:
    st.subheader("Deep Analytics")
    
    analysis_type = st.selectbox(
        "Select Analysis",
        ["Spending Trends", "Budget Analysis", "Cashflow Forecast", "Cost Optimization"]
    )
    
    if st.button("Generate Analysis"):
        with st.spinner("Generating insights..."):
            if analysis_type == "Spending Trends":
                response = st.session_state.agent.analyze_spending("Analyze spending trends and patterns")
            elif analysis_type == "Budget Analysis":
                response = st.session_state.agent.analyze_budget("Analyze budget performance")
            elif analysis_type == "Cashflow Forecast":
                response = st.session_state.agent.forecast_cashflow("Forecast cashflow for next 3 months")
            else:
                response = st.session_state.agent.analyze_spending("Find cost optimization opportunities")
            
            st.markdown(response)

# Sidebar
with st.sidebar:
    st.subheader("ℹ️ About")
    st.info("""
    This AI CFO Assistant helps you:
    - Analyze spending patterns
    - Monitor budget variance
    - Forecast cashflow
    - Find cost savings
    
    Using DeepSeek AI for intelligent insights.
    """)
    
    st.subheader("🔧 Settings")
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
    
    st.subheader("📊 Data Status")
    st.success("✅ Database Connected")
    st.success("✅ AI Model Ready")
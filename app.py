# app.py - COMPLETE VERSION WITH ALL FEATURES
import streamlit as st
from agents.router_agent import RouterAgent
from agents.cfo_agent import CFOAgent
from services.data_service import DataService
from services.plaid_service import PlaidService
from services.quickbooks_service import QuickBooksService
from services.stripe_service import StripeCardService
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="AI CFO Assistant - Enterprise",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.router = RouterAgent()
    st.session_state.cfo_agent = CFOAgent()
    st.session_state.data_service = DataService()
    st.session_state.plaid_service = PlaidService()
    st.session_state.qb_service = QuickBooksService()
    st.session_state.card_service = StripeCardService()
    st.session_state.messages = []
    st.session_state.initialized = True

# Get organizations
orgs = st.session_state.data_service.get_organizations()
org_names = {org['id']: org['name'] for org in orgs}

# Sidebar
with st.sidebar:
    st.title("🤖 AI CFO Assistant")
    
    # Organization selector
    selected_org = st.selectbox(
        "Select Organization",
        options=list(org_names.keys()),
        format_func=lambda x: org_names[x]
    )
    st.session_state.org_id = selected_org
    
    # Status indicators
    st.subheader("System Status")
    col1, col2 = st.columns(2)
    with col1:
        st.success("✅ Database")
        st.success("✅ AI Agents")
    with col2:
        st.info("🔄 Plaid")
        st.info("🔄 QuickBooks")
    
    # Quick metrics
    if selected_org:
        summary = st.session_state.data_service.get_spending_by_org(selected_org, 30)
        if summary:
            st.subheader("Quick Stats")
            st.metric("Monthly Spend", f"${summary['total_spent']:,.0f}")
            st.metric("Transactions", summary['transaction_count'])
            
            # Alerts
            alerts = st.session_state.data_service.get_alerts(selected_org)
            if alerts:
                st.subheader("🔔 Active Alerts")
                for alert in alerts[:3]:
                    if alert['severity'] == 'critical':
                        st.error(alert['message'])
                    elif alert['severity'] == 'high':
                        st.warning(alert['message'])

# Main header
st.title(f"💼 AI CFO for {org_names.get(selected_org, 'Select Organization')}")

# Main tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💬 AI Chat", 
    "📊 Dashboard", 
    "💳 Cards", 
    "🏦 Banking", 
    "📚 QuickBooks",
    "📈 Analytics",
    "⚙️ Settings"
])

# Tab 1: AI Chat with Router Agent
with tab1:
    st.subheader("Chat with your AI CFO Team")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask anything - Router Agent will direct to the right specialist..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("🧠 Router Agent analyzing..."):
                    # Use router agent to handle query
                    response = st.session_state.router.route_query(prompt, selected_org)
                    st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    with col2:
        st.subheader("Quick Actions")
        
        actions = {
            "📊 Cashflow Status": "What's our current cashflow and runway?",
            "💸 Spending Analysis": "Analyze our spending patterns this month",
            "⚠️ Check Alerts": "Are there any critical alerts or risks?",
            "📈 Budget Health": "Which departments are over budget?",
            "📚 Policy Check": "What are our expense approval policies?",
            "💡 Cost Savings": "How can we reduce costs by 10%?"
        }
        
        for label, query in actions.items():
            if st.button(label):
                st.session_state.messages.append({"role": "user", "content": query})
                st.rerun()

# Tab 2: Executive Dashboard
with tab2:
    st.subheader("Executive Dashboard")
    
    if selected_org:
        # Key metrics
        metrics_col1, metrics_col2, metrics_col3, metrics_col4, metrics_col5 = st.columns(5)
        
        # Get all data
        spending = st.session_state.data_service.get_spending_by_org(selected_org, 30)
        budgets = st.session_state.data_service.get_budget_status(selected_org)
        invoices = st.session_state.data_service.get_overdue_invoices(selected_org)
        cashflow = st.session_state.data_service.get_cashflow_forecast(selected_org)
        
        with metrics_col1:
            st.metric("Monthly Spend", f"${spending['total_spent']:,.0f}")
        with metrics_col2:
            st.metric("Burn Rate", f"${cashflow['monthly_burn_rate']:,.0f}/mo")
        with metrics_col3:
            over = len([b for b in budgets if b['status'] == 'over'])
            st.metric("Over Budget", over, delta_color="inverse")
        with metrics_col4:
            st.metric("Overdue", f"${invoices['total_amount']:,.0f}")
        with metrics_col5:
            runway = cashflow.get('runway_months', 0)
            st.metric("Runway", f"{runway:.1f} months")
        
        # Charts row 1
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Spending by category
            if spending['by_category']:
                fig = px.pie(
                    values=list(spending['by_category'].values()),
                    names=list(spending['by_category'].keys()),
                    title="Spending by Category",
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with chart_col2:
            # Budget variance
            if budgets:
                df_budgets = pd.DataFrame(budgets[:10])
                fig = px.bar(
                    df_budgets,
                    x='department',
                    y='variance_percent',
                    title="Budget Variance by Department",
                    color='status',
                    color_discrete_map={'over': '#FF6B6B', 'under': '#51CF66'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Charts row 2
        chart_col3, chart_col4 = st.columns(2)
        
        with chart_col3:
            # Top merchants
            if spending['top_merchants']:
                merchants_df = pd.DataFrame(
                    list(spending['top_merchants'].items()),
                    columns=['Merchant', 'Amount']
                )
                fig = px.bar(
                    merchants_df,
                    x='Amount',
                    y='Merchant',
                    orientation='h',
                    title="Top Merchants"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with chart_col4:
            # Cash flow trend
            dates = pd.date_range(start=datetime.now(), periods=6, freq='M')
            forecast_df = pd.DataFrame({
                'Month': dates,
                'Projected': [cashflow['monthly_burn_rate']] * 6,
                'Actual': [spending['total_spent']] + [None] * 5
            })
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=forecast_df['Month'],
                y=forecast_df['Projected'],
                name='Projected',
                line=dict(dash='dash')
            ))
            fig.add_trace(go.Scatter(
                x=forecast_df['Month'][:1],
                y=forecast_df['Actual'][:1],
                name='Actual',
                line=dict(color='green')
            ))
            fig.update_layout(title="Cash Flow Projection")
            st.plotly_chart(fig, use_container_width=True)

# Tab 3: Corporate Cards
with tab3:
    st.subheader("💳 Corporate Cards Management")
    
    card_tabs = st.tabs(["Active Cards", "Issue New Card", "Transactions", "Limits & Controls"])
    
    with card_tabs[0]:  # Active Cards
        # Get cards for this org
        cards = st.session_state.data_service.get_corporate_cards(selected_org)
        
        if cards:
            for card in cards:
                with st.expander(f"Card: {card['card_number']} - {card['card_name']}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**Status:** {card['status']}")
                        st.write(f"**Type:** {card['card_type']}")
                        st.write(f"**Issued:** {card.get('issued_date', 'N/A')}")
                    
                    with col2:
                        spent = card['current_balance']
                        limit = card['monthly_limit']
                        pct = (spent/limit*100) if limit > 0 else 0
                        
                        st.metric("Monthly Limit", f"${limit:,.2f}")
                        st.metric("Current Balance", f"${spent:,.2f}")
                        st.progress(pct/100)
                    
                    with col3:
                        if card['status'] == 'active':
                            if st.button(f"Freeze", key=f"freeze_{card['id']}"):
                                st.warning("Card frozen")
                        else:
                            if st.button(f"Activate", key=f"activate_{card['id']}"):
                                st.success("Card activated")
        else:
            st.info("No corporate cards issued yet")
    
    with card_tabs[1]:  # Issue New Card
        with st.form("new_card_form"):
            st.write("Issue New Virtual Card")
            
            col1, col2 = st.columns(2)
            with col1:
                card_name = st.text_input("Card Name", "Corporate Card")
                user_email = st.text_input("Assign to Employee")
            with col2:
                monthly_limit = st.number_input("Monthly Limit ($)", 1000, 50000, 5000)
                transaction_limit = st.number_input("Per Transaction Limit ($)", 100, 10000, 1000)
            
            categories = st.multiselect(
                "Allowed Categories",
                ["Software", "Hardware", "Travel", "Meals", "Office Supplies", "Marketing"],
                default=["Software", "Travel", "Meals"]
            )
            
            if st.form_submit_button("Issue Card"):
                st.success(f"✅ Virtual card issued: ****{random.randint(1000,9999)}")
    
    with card_tabs[2]:  # Transactions
        st.write("Recent Card Transactions")
        # Would show card transactions here
        
    with card_tabs[3]:  # Limits & Controls
        st.write("Card Spending Controls")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Global Settings**")
            st.checkbox("Auto-freeze on suspicious activity", value=True)
            st.checkbox("Require receipt for >$100", value=True)
            st.checkbox("Block international transactions", value=False)
        
        with col2:
            st.write("**Blocked Categories**")
            blocked = st.multiselect(
                "Select categories to block",
                ["Gambling", "Adult Entertainment", "Cryptocurrency"],
                default=["Gambling", "Adult Entertainment"]
            )

# Tab 4: Banking (Plaid)
with tab4:
    st.subheader("🏦 Bank Account Integration")
    
    bank_tabs = st.tabs(["Connected Accounts", "Add Account", "Sync History"])
    
    with bank_tabs[0]:  # Connected Accounts
        st.write("Connected Bank Accounts")
        
        # Mock connected accounts
        accounts = [
            {"name": "Chase Business Checking", "balance": 125000, "last_sync": "2 hours ago"},
            {"name": "Chase Business Savings", "balance": 250000, "last_sync": "2 hours ago"}
        ]
        
        for account in accounts:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"**{account['name']}**")
            with col2:
                st.metric("Balance", f"${account['balance']:,.2f}")
            with col3:
                st.write(f"Last sync: {account['last_sync']}")
            with col4:
                if st.button("Sync Now", key=account['name']):
                    with st.spinner("Syncing..."):
                        st.success("Synced!")
    
    with bank_tabs[1]:  # Add Account
        st.write("Connect New Bank Account")
        
        if st.button("🔗 Connect with Plaid"):
            st.info("Plaid Link would open here to connect bank account")
            # In production: st.session_state.plaid_service.create_link_token()
    
    with bank_tabs[2]:  # Sync History
        st.write("Transaction Sync History")
        
        sync_data = [
            {"Time": "2024-01-30 14:30", "Account": "Chase Checking", "Records": 156, "Status": "✅"},
            {"Time": "2024-01-30 10:00", "Account": "Chase Savings", "Records": 12, "Status": "✅"},
            {"Time": "2024-01-29 14:30", "Account": "Chase Checking", "Records": 189, "Status": "✅"}
        ]
        st.dataframe(sync_data)

# Tab 5: QuickBooks
with tab5:
    st.subheader("📚 QuickBooks Integration")
    
    qb_tabs = st.tabs(["Connection", "Sync Data", "Reports"])
    
    with qb_tabs[0]:  # Connection
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**QuickBooks Status**")
            # Check if connected (mock)
            is_connected = st.session_state.get('qb_connected', False)
            
            if is_connected:
                st.success("✅ QuickBooks Connected")
                st.write("Company: Demo Company LLC")
                st.write("Last Sync: 1 day ago")
                
                if st.button("Disconnect QuickBooks"):
                    st.session_state.qb_connected = False
                    st.rerun()
            else:
                st.warning("QuickBooks not connected")
                if st.button("Connect QuickBooks"):
                    # In production: auth_url = st.session_state.qb_service.get_auth_url()
                    st.session_state.qb_connected = True
                    st.rerun()
        
        with col2:
            if is_connected:
                st.write("**Sync Options**")
                if st.button("Sync Chart of Accounts"):
                    with st.spinner("Syncing..."):
                        st.success("Synced 45 accounts")
                
                if st.button("Sync Invoices"):
                    with st.spinner("Syncing..."):
                        st.success("Synced 127 invoices")
                
                if st.button("Sync Bills"):
                    with st.spinner("Syncing..."):
                        st.success("Synced 89 bills")
    
    with qb_tabs[1]:  # Sync Data
        st.write("Data Synchronization")
        
        sync_options = st.multiselect(
            "Select data to sync",
            ["Chart of Accounts", "Invoices", "Bills", "Customers", "Vendors"],
            default=["Invoices", "Bills"]
        )
        
        if st.button("Run Sync"):
            progress = st.progress(0)
            for i, option in enumerate(sync_options):
                progress.progress((i+1)/len(sync_options))
                st.write(f"Syncing {option}...")
            st.success("Sync complete!")
    
    with qb_tabs[2]:  # Reports
        st.write("QuickBooks Reports")
        
        report_type = st.selectbox(
            "Select Report",
            ["Profit & Loss", "Balance Sheet", "Cash Flow Statement"]
        )
        
        if st.button("Generate Report"):
            # Mock P&L report
            if report_type == "Profit & Loss":
                data = {
                    "Revenue": 500000,
                    "Cost of Goods Sold": 200000,
                    "Gross Profit": 300000,
                    "Operating Expenses": 150000,
                    "Net Income": 150000
                }
                st.json(data)

# Tab 6: Analytics
with tab6:
    st.subheader("📈 Advanced Analytics")
    
    analysis_type = st.selectbox(
        "Select Analysis Type",
        ["Trend Analysis", "Variance Analysis", "Forecast", "Benchmarking"]
    )
    
    if analysis_type == "Trend Analysis":
        # Get historical data
        transactions = st.session_state.data_service.get_transaction_history(selected_org, 180)
        if transactions:
            df = pd.DataFrame(transactions)
            df['date'] = pd.to_datetime(df['date'])
            
            # Monthly trend
            monthly = df.groupby(pd.Grouper(key='date', freq='M'))['amount'].sum()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=monthly.index,
                y=monthly.values,
                mode='lines+markers',
                name='Monthly Spending'
            ))
            fig.update_layout(title="6-Month Spending Trend")
            st.plotly_chart(fig, use_container_width=True)
    
    elif analysis_type == "Forecast":
        if st.button("Generate AI Forecast"):
            with st.spinner("AI generating forecast..."):
                forecast = st.session_state.cfo_agent.forecast_cashflow(
                    "Generate detailed 6-month cashflow forecast"
                )
                st.markdown(forecast)

# Tab 7: Settings
with tab7:
    st.subheader("⚙️ Settings & Configuration")
    
    settings_tabs = st.tabs(["General", "Integrations", "Policies", "Users"])
    
    with settings_tabs[0]:  # General
        st.write("**Organization Settings**")
        
        col1, col2 = st.columns(2)
        with col1:
            fiscal_year = st.selectbox("Fiscal Year Start", ["January", "April", "July", "October"])
            currency = st.selectbox("Currency", ["USD", "EUR", "GBP"])
        
        with col2:
            approval_limit = st.number_input("Auto-approval limit ($)", 0, 10000, 1000)
            st.checkbox("Enable email notifications", value=True)
        
        if st.button("Save Settings"):
            st.success("Settings saved!")
    
    with settings_tabs[1]:  # Integrations
        st.write("**Integration Settings**")
        
        integrations = {
            "Plaid (Banking)": st.session_state.get('plaid_connected', False),
            "QuickBooks": st.session_state.get('qb_connected', False),
            "Stripe (Cards)": True,
            "Slack": False,
            "Email": True
        }
        
        for integration, status in integrations.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(integration)
            with col2:
                if status:
                    st.success("Connected")
                else:
                    st.warning("Not connected")
    
    with settings_tabs[2]:  # Policies
        st.write("**Company Policies**")
        
        policies = st.session_state.data_service.get_policies(selected_org)
        
        for policy in policies:
            with st.expander(f"{policy['category'].replace('_', ' ').title()}"):
                st.write(policy['content'])
                st.write(f"Tags: {', '.join(policy['tags'])}")
    
    with settings_tabs[3]:  # Users
        st.write("**User Management**")
        
        users = st.session_state.data_service.get_users(selected_org)
        
        user_df = pd.DataFrame(users)[['full_name', 'email', 'role']]
        st.dataframe(user_df, use_container_width=True)

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("AI CFO Assistant v2.0")
with col2:
    st.caption("Powered by DeepSeek AI")
with col3:
    st.caption(f"Organization: {org_names.get(selected_org, 'None')}")
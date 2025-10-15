# app.py
import streamlit as st
from agents.cfo_agent import CFOAgent
from services.data_service import DataService
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
from auth.roles import is_admin, is_manager, is_employee


if "auth_user" not in st.session_state or not st.session_state["auth_user"]:
    st.info("Please sign in to continue.")
    # Use direct navigation to avoid KeyError in st.page_link on some Streamlit versions
    try:
        st.switch_page("pages/Login.py")
    except Exception:
        # Fallback: stop execution and let user select Login from sidebar/pages
        st.stop()

current_user = st.session_state["auth_user"]

# Page config
st.set_page_config(page_title="AI CFO Assistant", page_icon="💼", layout="wide")

# Initialize session state
if "agent" not in st.session_state:
    st.session_state.agent = CFOAgent()
    st.session_state.data_service = DataService()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Header
st.title("💼 AI CFO Assistant")
st.caption("Powered by DeepSeek AI & LangChain")


tab_labels = [
    "💬 Chat",
    "📊 Dashboard",
    "📈 Analytics",
    "� Transactions",
    "�💰 Budget Management",
]
tabs = st.tabs(tab_labels)
tab1, tab2, tab3, tab_tx, tab4 = tabs[0], tabs[1], tabs[2], tabs[3], tabs[4]

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
            "Find unusual transactions",
        ]

        for q in questions:
            if st.button(q, key=f"q_{q}"):
                st.session_state.messages.append({"role": "user", "content": q})
                st.rerun()

# Tab 2: Dashboard
with tab2:
    st.subheader("Financial Dashboard")

    # Budget Alerts Section
    all_budgets = st.session_state.data_service.get_all_budgets()

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    # Get data
    summary = st.session_state.data_service.get_spending_summary(30)
    budgets = st.session_state.data_service.get_budget_analysis()
    invoices = st.session_state.data_service.get_overdue_invoices()
    # budget_usage = st.session_state.data_service.calculate_budget_usage()

    with col1:
        st.metric(
            "Total Spent (30d)",
            f"${summary.get('total_spent', 0):,.0f}",
            "Last 30 days",
        )

    with col2:
        st.metric("Transactions", summary.get("transaction_count", 0), "Total count")

    with col3:
        over_budget = len([b for b in budgets if b["status"] == "over"])
        st.metric("Over Budget", over_budget, "Departments", delta_color="inverse")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        if summary.get("by_category"):
            fig = px.pie(
                values=list(summary["by_category"].values()),
                names=list(summary["by_category"].keys()),
                title="Spending by Category",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if budgets:
            df_budgets = pd.DataFrame(budgets[:10])
            fig = px.bar(
                df_budgets,
                x="department",
                y="variance_percent",
                title="Budget Variance by Department (%)",
                color="status",
                color_discrete_map={"over": "red", "under": "green"},
            )
            st.plotly_chart(fig, use_container_width=True)

    # Budget Status Table with filter dropdowns
    options = st.session_state.data_service.get_budget_filter_options(
        current_user=current_user
    )
    dept_options = ["All"] + options.get("departments", [])
    proj_options = ["All"] + options.get("project_ids", [])
    quarter_options = ["All"] + (
        options.get("quarters", []) or ["Q1", "Q2", "Q3", "Q4"]
    )
    year_options = ["All"] + [str(y) for y in options.get("years", [])]

    st.subheader("📋 Budget Status Overview")
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        filter_dept = st.selectbox("Department", dept_options, index=0, key="dash_dept")
    with fcol2:
        filter_project = st.selectbox(
            "Project ID", proj_options, index=0, key="dash_project"
        )
    with fcol3:
        filter_quarter = st.selectbox(
            "Quarter", quarter_options, index=0, key="dash_quarter"
        )
    with fcol4:
        filter_year_str = st.selectbox("Year", year_options, index=0, key="dash_year")
    filter_year = None if filter_year_str == "All" else int(filter_year_str)

    filtered_budgets = st.session_state.data_service.get_all_budgets(
        dept=(None if filter_dept == "All" else filter_dept),
        project_id=(None if filter_project == "All" else filter_project),
        quarter=(None if filter_quarter == "All" else filter_quarter),
        year=filter_year,
        current_user=current_user,
    )

    if filtered_budgets:
        df_budget_status = pd.DataFrame(filtered_budgets)

        # Format the dataframe for display
        display_df = df_budget_status[
            [
                "department",
                "category",
                "approved_amount",
                "actual_spent",
                "remaining",
                "usage_percent",
                "quarter",
                "year",
            ]
        ].copy()

        display_df.columns = [
            "Department",
            "Category",
            "Approved ($)",
            "Spent ($)",
            "Remaining ($)",
            "Usage (%)",
            "Quarter",
            "Year",
        ]

        # Style the dataframe
        def highlight_usage(row):
            if row["Usage (%)"] >= 100:
                return ["background-color: #ffcccc"] * len(row)
            elif row["Usage (%)"] >= 90:
                return ["background-color: #fff4cc"] * len(row)
            else:
                return [""] * len(row)

        styled_df = display_df.style.apply(highlight_usage, axis=1).format(
            {
                "Approved ($)": "${:,.2f}",
                "Spent ($)": "${:,.2f}",
                "Remaining ($)": "${:,.2f}",
                "Usage (%)": "{:.1f}%",
            }
        )

        st.dataframe(styled_df, use_container_width=True, height=400)
    else:
        st.info("No budgets match your filters.")

# Tab 3: Analytics
with tab3:
    st.subheader("Deep Analytics")

    analysis_type = st.selectbox(
        "Select Analysis",
        [
            "Spending Trends",
            "Budget Analysis",
            "Cashflow Forecast",
            "Cost Optimization",
        ],
    )

    if st.button("Generate Analysis"):
        with st.spinner("Generating insights..."):
            if analysis_type == "Spending Trends":
                response = st.session_state.agent.analyze_spending(
                    "Analyze spending trends and patterns"
                )
            elif analysis_type == "Budget Analysis":
                response = st.session_state.agent.analyze_budget(
                    "Analyze budget performance"
                )
            elif analysis_type == "Cashflow Forecast":
                response = st.session_state.agent.forecast_cashflow(
                    "Forecast cashflow for next 3 months"
                )
            else:
                response = st.session_state.agent.analyze_spending(
                    "Find cost optimization opportunities"
                )

            st.markdown(response)

# Tab: Transactions
with tab_tx:
    st.subheader("💳 Transaction Management")
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.markdown("#### Filters")
        c1, c2, c3 = st.columns(3)
        with c1:
            start_date = st.date_input(
                "Start", value=(datetime.now().date() - timedelta(days=30))
            )
        with c2:
            end_date = st.date_input("End", value=datetime.now().date())
        with c3:
            status = st.selectbox(
                "Status", ["", "pending", "succeeded", "paid", "refunded"], index=0
            )
        c4, c5, c6 = st.columns(3)
        with c4:
            category = st.text_input("Category (e.g., expense/income)")
        with c5:
            project = st.text_input("Project ID")
        with c6:
            merchant = st.text_input("Merchant")

        rows = st.session_state.data_service.list_transactions(
            current_user=current_user,
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            project_id=project or None,
            category=category or None,
            status=status or None,
            merchant=merchant or None,
        )
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("No transactions found for filters.")

    with col_b:
        st.markdown("#### Create Manual Transaction")
        with st.form("create_manual_tx"):
            tx_amount = st.number_input("Amount", step=10.0, min_value=0.0)
            tx_date = st.date_input("Date", value=datetime.now().date())
            tx_category = st.text_input("Category *", placeholder="expense/income")
            tx_merchant = st.text_input("Merchant")
            tx_desc = st.text_area("Description")
            tx_project = st.text_input("Project ID")
            tx_status = st.selectbox(
                "Status", ["pending", "succeeded", "paid", "refunded"], index=0
            )
            tx_currency = st.text_input("Currency", value="USD")
            tx_payment = st.text_input("Payment Method", placeholder="manual/card/bank")
            tx_invoice = st.text_input("Invoice ID (optional)")
            tx_card_id = st.text_input("Card ID (optional)")
            submit_tx = st.form_submit_button("Create")
            if submit_tx:
                res = st.session_state.data_service.create_transaction_manual(
                    current_user=current_user,
                    amount=float(tx_amount),
                    date=tx_date.isoformat(),
                    category=tx_category,
                    merchant=tx_merchant or None,
                    description=tx_desc or None,
                    project_id=tx_project or None,
                    status=tx_status,
                    currency=tx_currency or "USD",
                    payment_method=tx_payment or None,
                    invoice_id=tx_invoice or None,
                    card_id=tx_card_id or None,
                )
                if res.get("success"):
                    st.success("Transaction created")
                    st.rerun()
                else:
                    st.error(res.get("error", "Failed to create"))

        if is_admin(current_user):
            st.markdown("#### Stripe Sync")
            days = st.number_input("Days to sync", min_value=1, max_value=90, value=7)
            if st.button("Sync Stripe Now"):
                res = st.session_state.data_service.sync_transactions_from_stripe(
                    current_user, int(days)
                )
                if res.get("success"):
                    st.success(f"Synced {res.get('synced', 0)} items")
                    st.rerun()
                else:
                    st.error(res.get("error", "Sync failed"))

    # Pending Approvals for managers/admins
    if is_admin(current_user) or is_manager(current_user):
        st.markdown("### Pending Approvals")
        pending = st.session_state.data_service.list_pending_transactions_for_manager(
            current_user
        )
        if not pending:
            st.info("No pending transactions")
        else:
            for tx in pending:
                with st.expander(
                    f"{tx.get('date')} • {tx.get('category')} • ${float(tx.get('amount',0)):,.2f}"
                ):
                    st.write(tx.get("description") or "")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Approve", key=f"approve_tx_{tx['id']}"):
                            r = st.session_state.data_service.approve_transaction(
                                current_user, tx["id"], "approve"
                            )
                            if r.get("success"):
                                st.rerun()
                            else:
                                st.error(r.get("error", "Error"))
                    with c2:
                        if st.button("Reject", key=f"reject_tx_{tx['id']}"):
                            r = st.session_state.data_service.approve_transaction(
                                current_user, tx["id"], "reject"
                            )
                            if r.get("success"):
                                st.rerun()
                            else:
                                st.error(r.get("error", "Error"))
if tab4 is not None:
    with tab4:
        # Employees: simple proposal submission form
        if is_employee(current_user) and not (
            is_admin(current_user) or is_manager(current_user)
        ):
            st.subheader("📝 Submit Expense Request")
            with st.form("proposal_form_employee"):
                p_project = st.text_input("Project ID *")
                p_dept = st.text_input("Department")
                p_amount = st.number_input("Amount ($) *", min_value=0.0, step=50.0)
                p_desc = st.text_area("Reason / Description *")
                doc = st.file_uploader(
                    "Attach documentation (optional)",
                    type=["pdf", "png", "jpg", "jpeg", "doc", "docx"],
                )
                submitted = st.form_submit_button("Submit Request")
                if submitted:
                    doc_url = None
                    if doc is not None:
                        upload = st.session_state.data_service.upload_proposal_document(
                            current_user, doc.getvalue(), doc.name
                        )
                        if upload.get("success"):
                            doc_url = upload.get("url")
                        else:
                            st.warning(
                                "Document upload failed; submitting without attachment."
                            )
                    res = st.session_state.data_service.submit_spending_proposal(
                        current_user=current_user,
                        project_id=p_project,
                        dept=p_dept,
                        amount=p_amount,
                        description=p_desc
                        + (f"\nAttachment: {doc_url}" if doc_url else ""),
                    )
                    if res.get("success"):
                        st.success("Expense request submitted for manager approval")
                    else:
                        st.error(res.get("error", "Submission failed"))
        else:
            # Managers/Admins: two subtabs
            t_manage, t_approvals = st.tabs(
                ["🔧 Manage Budgets", "✅ Approvals & History"]
            )

            # Manage Budgets tab
            with t_manage:
                st.subheader("💰 Budget Management")
                options = st.session_state.data_service.get_budget_filter_options(
                    current_user=current_user
                )
                dept_options = ["All"] + options.get("departments", [])
                proj_options = ["All"] + options.get("project_ids", [])
                quarter_options = ["All"] + (
                    options.get("quarters", []) or ["Q1", "Q2", "Q3", "Q4"]
                )
                year_options = ["All"] + [str(y) for y in options.get("years", [])]
                st.subheader("📋 Budget Status Overview")
                fcol1, fcol2, fcol3, fcol4 = st.columns(4)
                with fcol1:
                    filter_dept = st.selectbox(
                        "Department", dept_options, index=0, key="mgmt_dept_sel"
                    )
                with fcol2:
                    filter_project = st.selectbox(
                        "Project ID", proj_options, index=0, key="mgmt_project_sel"
                    )
                with fcol3:
                    filter_quarter = st.selectbox(
                        "Quarter", quarter_options, index=0, key="mgmt_quarter_sel"
                    )
                with fcol4:
                    filter_year_str = st.selectbox(
                        "Year", year_options, index=0, key="mgmt_year_sel"
                    )
                filter_year = None if filter_year_str == "All" else int(filter_year_str)
                filtered_budgets = st.session_state.data_service.get_all_budgets(
                    dept=(None if filter_dept == "All" else filter_dept),
                    project_id=(None if filter_project == "All" else filter_project),
                    quarter=(None if filter_quarter == "All" else filter_quarter),
                    year=filter_year,
                    current_user=current_user,
                )
                actions = [
                    "View All Budgets",
                    "Create New Budget",
                    "Edit Budget",
                    "Delete Budget",
                ]
                budget_action = st.selectbox("Action", actions, key="budget_action")
                if budget_action == "Create New Budget":
                    with st.form("create_budget_form"):
                        st.write("**Create New Budget**")
                        dept = st.text_input(
                            "Department *", placeholder="e.g., Marketing, Operations"
                        )
                        category = st.text_input(
                            "Category", placeholder="e.g., Ads, Cloud, Office"
                        )
                        project_id = st.text_input(
                            "Project ID", placeholder="optional project identifier"
                        )
                        approved = st.number_input(
                            "Approved Amount ($) *", min_value=0.0, step=100.0
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            create_quarter_options = [
                                q for q in quarter_options if q != "All"
                            ]
                            quarter = st.selectbox(
                                "Quarter",
                                create_quarter_options,
                                index=0,
                                key="create_quarter",
                            )
                        with col2:
                            year = st.number_input(
                                "Year",
                                min_value=2020,
                                max_value=2030,
                                value=datetime.now().year,
                            )
                        submitted = st.form_submit_button("Create Budget")
                        if submitted:
                            if dept and approved > 0:
                                result = st.session_state.data_service.create_budget(
                                    department=dept,
                                    approved_amount=approved,
                                    category=category if category else "General",
                                    project_id=project_id or None,
                                    quarter=quarter,
                                    year=year,
                                    current_user=current_user,
                                )
                                if result.get("success"):
                                    st.success(f"✅ Budget created for {dept}!")
                                    st.rerun()
                                else:
                                    st.error(
                                        f"❌ Error: {result.get('error', 'Unknown error')}"
                                    )
                            else:
                                st.error("Please fill in required fields (*)")
                elif budget_action == "View All Budgets":
                    budgets = st.session_state.data_service.get_all_budgets(
                        dept=(None if filter_dept == "All" else filter_dept),
                        project_id=(
                            None if filter_project == "All" else filter_project
                        ),
                        quarter=(None if filter_quarter == "All" else filter_quarter),
                        year=filter_year,
                        current_user=current_user,
                    )
                    if budgets:
                        st.write(f"**Total Budgets: {len(budgets)}**")
                        for budget in budgets:
                            with st.expander(
                                f"{budget['department']} - {budget['category']} ({budget['quarter']} {budget['year']})"
                            ):
                                st.write(
                                    f"**Approved:** ${budget['approved_amount']:,.2f}"
                                )
                                st.write(f"**Spent:** ${budget['actual_spent']:,.2f}")
                                st.write(f"**Remaining:** ${budget['remaining']:,.2f}")
                                st.progress(min(budget["usage_percent"] / 100, 1.0))
                                st.write(f"**Usage:** {budget['usage_percent']:.1f}%")
                                if budget["is_over_budget"]:
                                    st.error("🚨 OVER BUDGET!")
                                elif budget["is_near_limit"]:
                                    st.warning("⚠️ Near limit (90%+)")
                    else:
                        st.info("No budgets found. Create one to get started!")
                elif budget_action == "Edit Budget":
                    budgets = st.session_state.data_service.get_all_budgets(
                        dept=(None if filter_dept == "All" else filter_dept),
                        project_id=(
                            None if filter_project == "All" else filter_project
                        ),
                        quarter=(None if filter_quarter == "All" else filter_quarter),
                        year=filter_year,
                        current_user=current_user,
                    )
                    if not budgets:
                        st.info("No budgets available to edit.")
                    else:
                        budget_options = {
                            f"{b['department']} - {b['category']} ({b['quarter']} {b['year']})": b[
                                "id"
                            ]
                            for b in budgets
                        }
                        selected = st.selectbox(
                            "Select Budget to Edit", list(budget_options.keys())
                        )
                        budget_id = budget_options[selected]
                        current = next(b for b in budgets if b["id"] == budget_id)
                        with st.form("edit_budget_form"):
                            st.write("**Edit Budget**")
                            dept = st.text_input(
                                "Department", value=current["department"]
                            )
                            category = st.text_input(
                                "Category", value=current["category"]
                            )
                            project_id = st.text_input(
                                "Project ID", value=str(current.get("project_id", ""))
                            )
                            approved = st.number_input(
                                "Approved Amount ($)",
                                min_value=0.0,
                                step=100.0,
                                value=float(current["approved_amount"]),
                            )
                            actual = st.number_input(
                                "Actual Spent ($)",
                                min_value=0.0,
                                step=10.0,
                                value=float(current["actual_spent"]),
                            )
                            col1, col2 = st.columns(2)
                            with col1:
                                quarter = st.selectbox(
                                    "Quarter",
                                    ["Q1", "Q2", "Q3", "Q4"],
                                    index=(
                                        ["Q1", "Q2", "Q3", "Q4"].index(
                                            current["quarter"]
                                        )
                                        if current["quarter"]
                                        in ["Q1", "Q2", "Q3", "Q4"]
                                        else 0
                                    ),
                                )
                            with col2:
                                year = st.number_input(
                                    "Year",
                                    min_value=2010,
                                    max_value=2100,
                                    value=int(current["year"]),
                                )
                            submitted = st.form_submit_button("Update Budget")
                            if submitted:
                                result = st.session_state.data_service.update_budget(
                                    budget_id=budget_id,
                                    department=dept,
                                    approved_amount=approved,
                                    actual_spent=actual,
                                    category=category,
                                    project_id=project_id or None,
                                    quarter=quarter,
                                    year=year,
                                    current_user=current_user,
                                )
                                if result.get("success"):
                                    st.success("✅ Budget updated!")
                                    st.rerun()
                                else:
                                    st.error(
                                        f"❌ Error: {result.get('error', 'Unknown error')}"
                                    )
                elif budget_action == "Delete Budget":
                    budgets = st.session_state.data_service.get_all_budgets(
                        dept=(None if filter_dept == "All" else filter_dept),
                        project_id=(
                            None if filter_project == "All" else filter_project
                        ),
                        quarter=(None if filter_quarter == "All" else filter_quarter),
                        year=filter_year,
                        current_user=current_user,
                    )
                    if budgets:
                        budget_options = {
                            f"{b['department']} - {b['category']} ({b['quarter']} {b['year']})": b[
                                "id"
                            ]
                            for b in budgets
                        }
                        selected = st.selectbox(
                            "Select Budget to Delete", list(budget_options.keys())
                        )
                        budget_id = budget_options[selected]
                        if st.button("🗑️ Delete Budget", type="primary"):
                            result = st.session_state.data_service.delete_budget(
                                budget_id, current_user=current_user
                            )
                            if result.get("success"):
                                st.success("✅ Budget deleted!")
                                st.rerun()
                            else:
                                st.error(
                                    f"❌ Error: {result.get('error', 'Unknown error')}"
                                )
                    else:
                        st.info("No budgets available to delete.")
                    st.divider()

            # Approvals & History tab
            with t_approvals:
                st.subheader("✅ Approvals & History")
                pending = (
                    st.session_state.data_service.get_pending_proposals_for_manager(
                        current_user
                    )
                )
                history = (
                    st.session_state.data_service.get_proposals_history_for_manager(
                        current_user
                    )
                )
                st.markdown("### Pending Requests")
                if not pending:
                    st.info("No pending proposals")
                else:
                    for pr in pending:
                        with st.expander(
                            f"{pr['project_id']} • ${pr['amount']:,.2f} • {pr['status']}"
                        ):
                            st.write(pr.get("description") or "")
                            colA, colB = st.columns(2)
                            with colA:
                                if st.button("Approve", key=f"appr_{pr['id']}"):
                                    r = st.session_state.data_service.decide_proposal(
                                        current_user, pr["id"], "approve"
                                    )
                                    if r.get("success"):
                                        st.rerun()
                                    else:
                                        st.error(r.get("error", "Error"))
                            with colB:
                                if st.button("Reject", key=f"rej_{pr['id']}"):
                                    r = st.session_state.data_service.decide_proposal(
                                        current_user, pr["id"], "reject"
                                    )
                                    if r.get("success"):
                                        st.rerun()
                                    else:
                                        st.error(r.get("error", "Error"))
                st.markdown("### History")
                if not history:
                    st.info("No historical records yet")
                else:
                    for pr in history:
                        with st.expander(
                            f"{pr['project_id']} • ${pr['amount']:,.2f} • {pr['status']}"
                        ):
                            st.write(pr.get("description") or "")
                            steps = (
                                st.session_state.data_service.get_approval_history(
                                    pr["id"]
                                )
                                or []
                            )
                            for step in steps:
                                st.write(
                                    f"- {step.get('approval_level','manager')} • {step.get('status')} • {step.get('comments') or ''} • {step.get('approved_at') or step.get('created_at')}"
                                )


# Sidebar
with st.sidebar:
    st.subheader("👤 Account")
    st.write(f"Role: {current_user.get('role','unknown')}")
    st.write(f"Org: {current_user.get('organization_id') or 'N/A'}")

    if st.button("Sign out"):
        st.session_state.pop("auth_user", None)
        st.rerun()

    st.info(
        """
    This AI CFO Assistant helps you:
    - Analyze spending patterns
    - Monitor budget variance
    - Forecast cashflow
    - Find cost savings
    
    Using DeepSeek AI for intelligent insights.
    """
    )

    st.subheader("🔧 Settings")
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    st.subheader("📊 Data Status")
    st.success("✅ Database Connected")
    st.success("✅ AI Model Ready")

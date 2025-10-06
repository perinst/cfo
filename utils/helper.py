# utils/helpers.py
import pandas as pd
from datetime import datetime, timedelta

def format_currency(amount: float) -> str:
    """Format number as currency"""
    return f"${amount:,.2f}"

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change"""
    if old_value == 0:
        return 0
    return ((new_value - old_value) / old_value) * 100

def get_date_range(days: int):
    """Get date range for queries"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date
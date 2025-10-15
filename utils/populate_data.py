# populate_database_final.py
import os
from supabase import create_client
from datetime import datetime, timedelta
import random
from faker import Faker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabasePopulator:
    def __init__(self):
        self.url = "https://wfoigedwujyibqvdtnjk.supabase.co"
        self.key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indmb2lnZWR3dWp5aWJxdmR0bmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTkyMzM1MjAsImV4cCI6MjA3NDgwOTUyMH0.RJSJTq7e51hekJ32QwnTjQZRT8eiEZTMHrZh-5QBIf8"
        
        print(f"Connecting to Supabase...")
        self.client = create_client(self.url, self.key)
        self.fake = Faker()
        
        # Test connection
        try:
            result = self.client.table('organizations').select("count", count='exact').execute()
            print(f"✅ Connected! Current organizations: {result.count}")
        except Exception as e:
            print(f"❌ Connection error: {e}")
            raise
    
    def create_complete_dataset(self):
        """Create complete dataset for AI CFO"""
        print("\n" + "="*60)
        print("POPULATING AI CFO DATABASE")
        print("="*60)
        
        # Create 3 companies
        companies = [
            "TechCorp Solutions Inc",
            "Digital Marketing Agency",
            "E-commerce Platform Ltd"
        ]
        
        for company_name in companies:
            print(f"\n📦 Creating {company_name}...")
            
            # 1. Create Organization
            org = self.client.table('organizations').insert({
                'name': company_name,
                'settings': {
                    'fiscal_year': 2024,
                    'currency': 'USD',
                    'employee_count': random.randint(20, 100)
                }
            }).execute()
            org_id = org.data[0]['id']
            print(f"  ✓ Organization created: {org_id[:8]}...")
            
            # 2. Create Users
            users_data = []
            roles = [
                ('ceo', 'admin', 'Chief Executive Officer'),
                ('cfo', 'admin', 'Chief Financial Officer'),
                ('manager_sales', 'manager', 'Sales Manager'),
                ('manager_eng', 'manager', 'Engineering Manager'),
                ('employee1', 'employee', 'Employee'),
                ('employee2', 'employee', 'Employee'),
                ('employee3', 'employee', 'Employee')
            ]
            
            for username, role, title in roles:
                users_data.append({
                    'email': f'{username}_{org_id[:8]}@{company_name.lower().replace(" ", "")}.com',
                    'full_name': f'{self.fake.name()} - {title}',
                    'role': role,
                    'organization_id': org_id
                })
            
            users = self.client.table('users').insert(users_data).execute()
            user_ids = [u['id'] for u in users.data]
            print(f"  ✓ Created {len(user_ids)} users")
            
            # 3. Create Transactions (150 per company)
            transactions = []
            categories = ['software', 'hardware', 'travel', 'marketing', 'office_supplies', 'consulting', 'utilities', 'meals']
            merchants = {
                'software': ['AWS', 'Google Cloud', 'Microsoft 365', 'Slack', 'Zoom'],
                'hardware': ['Apple Store', 'Dell', 'Best Buy'],
                'travel': ['United Airlines', 'Marriott', 'Uber'],
                'marketing': ['Google Ads', 'Facebook Ads', 'LinkedIn'],
                'office_supplies': ['Staples', 'Amazon Business'],
                'consulting': ['McKinsey', 'Deloitte'],
                'utilities': ['AT&T', 'Electric Company'],
                'meals': ['Starbucks', 'DoorDash', 'Restaurant']
            }
            
            for i in range(150):
                category = random.choice(categories)
                merchant_list = merchants.get(category, ['Generic Vendor'])
                
                amount = random.uniform(50, 15000)
                if category == 'consulting':
                    amount = random.uniform(5000, 50000)
                
                trans_date = datetime.now() - timedelta(days=random.randint(0, 180))
                
                transactions.append({
                    'transaction_id': f'TXN_{company_name[:3].upper()}_{i+1:05d}',
                    'amount': round(amount, 2),
                    'date': trans_date.date().isoformat(),
                    'category': category,
                    'merchant': random.choice(merchant_list),
                    'employee_id': f'EMP_{random.randint(1, 100):03d}',
                    'description': f'Payment for {category}',
                    'payment_method': random.choice(['credit_card', 'ach', 'wire']),
                    'status': random.choice(['completed', 'pending', 'approved']),
                    'approval_required': 1 if amount > 5000 else 0,
                    'fraud_flag': 1 if random.random() < 0.02 else 0,
                    'organization_id': org_id,
                    'created_by': random.choice(user_ids) if user_ids else None
                })
            
            # Batch insert transactions
            for j in range(0, len(transactions), 50):
                batch = transactions[j:j+50]
                self.client.table('transactions').insert(batch).execute()
            print(f"  ✓ Created {len(transactions)} transactions")
            
            # 4. Create Budgets
            departments = ['Engineering', 'Sales', 'Marketing', 'Operations', 'HR']
            quarters = ['Q1', 'Q2', 'Q3', 'Q4']
            budgets = []
            
            for dept in departments:
                for quarter in quarters:
                    approved = random.uniform(50000, 200000)
                    spent = approved * random.uniform(0.7, 1.2)
                    
                    budgets.append({
                        'dept': dept,
                        'project_id': f'PROJ_{dept[:3]}_{quarter}_2024',
                        'quarter': quarter,
                        'year': 2024,
                        'approved_amount': round(approved, 2),
                        'actual_spent': round(spent, 2),
                        'category': random.choice(['operations', 'growth', 'maintenance']),
                        'organization_id': org_id
                    })
            
            self.client.table('budgets').insert(budgets).execute()
            print(f"  ✓ Created {len(budgets)} budgets")
            
            # 5. Create Invoices
            vendors = ['AWS', 'Google', 'Microsoft', 'Adobe', 'Salesforce', 'Office Depot']
            invoices = []
            
            for i in range(30):
                invoice_date = datetime.now() - timedelta(days=random.randint(0, 90))
                due_date = invoice_date + timedelta(days=30)
                
                invoices.append({
                    'invoice_id': f'INV_{company_name[:3].upper()}_{i+1:04d}',
                    'vendor': random.choice(vendors),
                    'invoice_date': invoice_date.date().isoformat(),
                    'due_date': due_date.date().isoformat(),
                    'amount': round(random.uniform(1000, 25000), 2),
                    'invoice_type': random.choice(['standard', 'recurring']),
                    'payment_terms': 'Net 30',
                    'status': random.choice(['pending', 'paid', 'overdue']),
                    'is_overdue': due_date.date() < datetime.now().date(),
                    'description': self.fake.sentence(),
                    'po_number': f'PO{random.randint(10000, 99999)}',
                    'organization_id': org_id
                })
            
            self.client.table('invoices').insert(invoices).execute()
            print(f"  ✓ Created {len(invoices)} invoices")
            
            # 6. Create Policy Documents
            policies = [
                {
                    'content': 'All expenses over $5,000 require manager approval',
                    'category': 'expense_policy',
                    'tags': ['approval', 'expense'],
                    'organization_id': org_id
                },
                {
                    'content': 'Travel budget is limited to $3,000 per employee per month',
                    'category': 'travel_policy', 
                    'tags': ['travel', 'budget'],
                    'organization_id': org_id
                },
                {
                    'content': 'Software subscriptions must be reviewed quarterly',
                    'category': 'software_policy',
                    'tags': ['software', 'review'],
                    'organization_id': org_id
                }
            ]
            
            self.client.table('policy_documents').insert(policies).execute()
            print(f"  ✓ Created {len(policies)} policies")
            
            # 7. Create Sample Alerts
            alerts = [
                {
                    'alert_type': 'budget_exceeded',
                    'severity': 'high',
                    'message': f'{random.choice(departments)} dept is over budget',
                    'data': {'dept': random.choice(departments)},
                    'organization_id': org_id
                },
                {
                    'alert_type': 'large_transaction',
                    'severity': 'medium',
                    'message': 'Large transaction detected',
                    'data': {'amount': 25000},
                    'organization_id': org_id
                }
            ]
            
            self.client.table('alerts').insert(alerts).execute()
            print(f"  ✓ Created {len(alerts)} alerts")
            
            # 8. Create Corporate Cards
            cards = []
            for i in range(3):
                cards.append({
                    'card_number': f'****{random.randint(1000, 9999)}',
                    'card_name': f'Corporate Card {i+1}',
                    'user_id': user_ids[i] if i < len(user_ids) else user_ids[0],
                    'organization_id': org_id,
                    'monthly_limit': random.choice([5000, 10000, 15000]),
                    'transaction_limit': random.choice([1000, 2500]),
                    'current_balance': round(random.uniform(0, 3000), 2),
                    'status': 'active',
                    'card_type': 'virtual'
                })
            
            self.client.table('corporate_cards').insert(cards).execute()
            print(f"  ✓ Created {len(cards)} corporate cards")
        
        print("\n" + "="*60)
        print("✅ DATABASE POPULATION COMPLETE!")
        print("="*60)
        self.show_summary()
    
    def show_summary(self):
        """Show database summary"""
        print("\nDATABASE SUMMARY:")
        print("-"*40)
        
        tables = [
            'organizations', 'users', 'transactions', 
            'budgets', 'invoices', 'policy_documents',
            'corporate_cards', 'alerts'
        ]
        
        for table in tables:
            try:
                result = self.client.table(table).select("count", count='exact').execute()
                print(f"{table:20} : {result.count:,} records")
            except:
                print(f"{table:20} : Table not found or empty")

if __name__ == "__main__":
    populator = DatabasePopulator()
    populator.create_complete_dataset()
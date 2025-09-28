import pandas as pd
import json
import os
from datetime import datetime
import random
import hashlib

class BankDatabase:
    def __init__(self, db_file, transactions_file):
        self.db_file = db_file
        self.transactions_file = transactions_file
        self.ensure_files_exist()
    
    def hash_password(self, password):
        """Hash a password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password, hashed_password):
        """Verify a password against its hash"""
        hashed = self.hash_password(password)
        print(f"[DEBUG] Input password hash: {hashed}")
        print(f"[DEBUG] Stored password hash: {hashed_password}")
        return hashed == hashed_password
    
    def ensure_files_exist(self):
        """Create database files if they don't exist"""
        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w', newline='') as f:
                import csv
                writer = csv.writer(f)
                writer.writerow(['unique_id', 'account_number', 'name', 'bank', 'password', 'account_balance', 'created_at', 'last_login'])
        
        if not os.path.exists(self.transactions_file):
            with open(self.transactions_file, 'w', newline='') as f:
                import csv
                writer = csv.writer(f)
                writer.writerow(['transaction_id', 'user_id', 'type', 'amount', 'description', 'timestamp', 'status'])
    
    def get_user_by_id(self, unique_id):
        """Get user by unique ID"""
        try:
            # Ensure unique_id is an integer
            unique_id = int(unique_id)
            print(f"[DEBUG] Getting user by ID: {unique_id}, type: {type(unique_id)}")
            
            data = pd.read_csv(self.db_file)
            # Convert unique_id column to integers for comparison
            data['unique_id'] = data['unique_id'].astype(int)
            user = data[data['unique_id'] == unique_id]
            
            if not user.empty:
                print(f"[DEBUG] User found: {user.iloc[0]['name']}")
                return user.iloc[0].to_dict()
            print(f"[DEBUG] User not found for ID: {unique_id}")
            return None
        except Exception as e:
            print(f"[ERROR] Error getting user: {e}")
            return None
    
    def get_user_by_account(self, account_number):
        """Get user by account number"""
        try:
            data = pd.read_csv(self.db_file)
            user = data[data['account_number'] == int(account_number)]
            if not user.empty:
                return user.iloc[0].to_dict()
            return None
        except Exception as e:
            print(f"Error getting user by account: {e}")
            return None
            
    def get_user_by_name(self, name):
        """Get user by name"""
        try:
            data = pd.read_csv(self.db_file)
            # Case-insensitive name comparison
            user = data[data['name'].str.lower() == name.lower()]
            if not user.empty:
                return user.iloc[0].to_dict()
            return None
        except Exception as e:
            print(f"[ERROR] Error getting user by name: {e}")
            return None
    
    def authenticate_user(self, user_id, password):
        """Authenticate user with password"""
        try:
            print(f"[DEBUG] Authenticating user_id: {user_id}, type: {type(user_id)}")
            user = self.get_user_by_id(user_id)
            if user:
                print(f"[DEBUG] User found for authentication: {user['name']}")
                # For backward compatibility, check if password is already hashed
                if len(user['password']) == 64:  # SHA-256 hash length
                    result = self.verify_password(password, user['password'])
                    print(f"[DEBUG] Password verification result (hashed): {result}")
                    return result
                else:
                    # Plain text password (old data), hash it and update
                    if user['password'] == password:
                        # Update to hashed password
                        hashed_password = self.hash_password(password)
                        self.update_password(user_id, hashed_password)
                        print(f"[DEBUG] Password verification result (plain): True")
                        return True
                    print(f"[DEBUG] Password verification result (plain): False")
                    return False
            print(f"[DEBUG] User not found for authentication")
            return False
        except Exception as e:
            print(f"[ERROR] Error authenticating user: {e}")
            return False
    
    def update_password(self, unique_id, hashed_password):
        """Update user password with hashed version"""
        try:
            data = pd.read_csv(self.db_file)
            data.loc[data['unique_id'] == int(unique_id), 'password'] = hashed_password
            data.to_csv(self.db_file, index=False)
            return True
        except Exception as e:
            print(f"Error updating password: {e}")
            return False
    
    def create_user(self, name, password, bank="CENT"):
        """Create a new user"""
        try:
            # Generate unique IDs
            unique_id = random.randint(10000, 99999)
            account_number = random.randint(1000000000, 9999999999)
            
            # Check if IDs already exist
            try:
                data = pd.read_csv(self.db_file)
                while unique_id in data['unique_id'].values:
                    unique_id = random.randint(10000, 99999)
                while account_number in data['account_number'].values:
                    account_number = random.randint(1000000000, 9999999999)
            except (pd.errors.EmptyDataError, FileNotFoundError):
                # File doesn't exist or is empty, no need to check for duplicates
                pass
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Hash the password
            hashed_password = self.hash_password(password)
            
            new_user = {
                'unique_id': unique_id,
                'account_number': account_number,
                'name': name,
                'bank': bank,
                'password': hashed_password,  # Store hashed password
                'account_balance': 0,
                'created_at': current_time,
                'last_login': None
            }
            
            # Append to CSV
            with open(self.db_file, 'a', newline='') as f:
                import csv
                writer = csv.writer(f)
                writer.writerow([unique_id, account_number, name, bank, hashed_password, 0, current_time, None])
            
            return new_user
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def update_balance(self, unique_id, new_balance):
        """Update user balance"""
        try:
            data = pd.read_csv(self.db_file)
            data.loc[data['unique_id'] == int(unique_id), 'account_balance'] = new_balance
            data.to_csv(self.db_file, index=False)
            return True
        except Exception as e:
            print(f"Error updating balance: {e}")
            return False
    
    def update_last_login(self, unique_id):
        """Update last login time"""
        try:
            data = pd.read_csv(self.db_file)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # Convert the column to object type to avoid dtype warnings
            data['last_login'] = data['last_login'].astype('object')
            data.loc[data['unique_id'] == int(unique_id), 'last_login'] = current_time
            data.to_csv(self.db_file, index=False)
            return True
        except Exception as e:
            print(f"Error updating last login: {e}")
            return False
    
    def transfer_money(self, from_id, to_account, amount, description="Transfer"):
        """Transfer money between accounts"""
        try:
            data = pd.read_csv(self.db_file)
            
            # Get sender and receiver
            sender = data[data['unique_id'] == int(from_id)]
            receiver = data[data['account_number'] == int(to_account)]
            
            if sender.empty or receiver.empty:
                return False, "Invalid account"
            
            sender_balance = sender.iloc[0]['account_balance']
            if sender_balance < amount:
                return False, "Insufficient funds"
            
            # Update balances
            data.loc[data['unique_id'] == int(from_id), 'account_balance'] -= amount
            data.loc[data['account_number'] == int(to_account), 'account_balance'] += amount
            
            data.to_csv(self.db_file, index=False)
            
            # Log transaction
            self.log_transaction(from_id, 'transfer', amount, f"{description} to {to_account}")
            self.log_transaction(receiver.iloc[0]['unique_id'], 'deposit', amount, f"Received from {from_id}")
            
            return True, "Transfer successful"
        except Exception as e:
            print(f"Error transferring money: {e}")
            return False, "Transfer failed"
    
    def deposit_money(self, unique_id, amount, description="Deposit"):
        """Deposit money to account"""
        try:
            data = pd.read_csv(self.db_file)
            current_balance = data[data['unique_id'] == int(unique_id)]['account_balance'].iloc[0]
            new_balance = current_balance + amount
            
            data.loc[data['unique_id'] == int(unique_id), 'account_balance'] = new_balance
            data.to_csv(self.db_file, index=False)
            
            # Log transaction
            self.log_transaction(unique_id, 'deposit', amount, description)
            
            return True, new_balance
        except Exception as e:
            print(f"Error depositing money: {e}")
            return False, 0
    
    def withdraw_money(self, unique_id, amount, description="Withdrawal"):
        """Withdraw money from account"""
        try:
            data = pd.read_csv(self.db_file)
            current_balance = data[data['unique_id'] == int(unique_id)]['account_balance'].iloc[0]
            
            if current_balance < amount:
                return False, "Insufficient funds", 0
            
            new_balance = current_balance - amount
            data.loc[data['unique_id'] == int(unique_id), 'account_balance'] = new_balance
            data.to_csv(self.db_file, index=False)
            
            # Log transaction
            self.log_transaction(unique_id, 'withdraw', amount, description)
            
            return True, "Withdrawal successful", new_balance
        except Exception as e:
            print(f"Error withdrawing money: {e}")
            return False, "Withdrawal failed", 0
    
    def log_transaction(self, user_id, transaction_type, amount, description):
        """Log a transaction"""
        try:
            transaction_id = random.randint(100000, 999999)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(self.transactions_file, 'a', newline='') as f:
                import csv
                writer = csv.writer(f)
                writer.writerow([transaction_id, user_id, transaction_type, amount, description, timestamp, 'completed'])
        except Exception as e:
            print(f"Error logging transaction: {e}")
    
    def get_transaction_history(self, user_id, limit=50):
        """Get transaction history for a user"""
        try:
            data = pd.read_csv(self.transactions_file)
            user_transactions = data[data['user_id'] == int(user_id)].tail(limit)
            return user_transactions.to_dict('records')
        except Exception as e:
            print(f"Error getting transaction history: {e}")
            return []
    
    def get_all_users(self):
        """Get all users for admin panel"""
        try:
            data = pd.read_csv(self.db_file)
            return data[['unique_id', 'account_number', 'name', 'bank', 'account_balance', 'created_at', 'last_login']].to_dict('records')
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []
    
    def update_user_profile(self, unique_id, name):
        """Update user profile"""
        try:
            data = pd.read_csv(self.db_file)
            data.loc[data['unique_id'] == int(unique_id), 'name'] = name
            data.to_csv(self.db_file, index=False)
            return True
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False
    
    def change_password(self, unique_id, new_password):
        """Change user password"""
        try:
            data = pd.read_csv(self.db_file)
            hashed_password = self.hash_password(new_password)
            data.loc[data['unique_id'] == int(unique_id), 'password'] = hashed_password
            data.to_csv(self.db_file, index=False)
            return True
        except Exception as e:
            print(f"Error changing password: {e}")
            return False


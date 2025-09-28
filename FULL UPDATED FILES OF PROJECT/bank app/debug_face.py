#!/usr/bin/env python3

import sys
import os
sys.path.append('backend')
sys.path.append('models')

from database import BankDatabase
import pandas as pd

# Initialize
db = BankDatabase('bank_details.csv', 'transactions.csv')

print("=== FACE RECOGNITION DEBUG ===")
print("\n1. Current trained users in dataset:")
try:
    dataset_dirs = [d for d in os.listdir('dataset') if os.path.isdir(f"dataset/{d}") and d.isdigit()]
    for user_id in sorted(dataset_dirs):
        user = db.get_user_by_id(int(user_id))
        if user:
            print(f"   User {user_id}: {user['name']}")
        else:
            print(f"   User {user_id}: NOT FOUND IN DATABASE")
except Exception as e:
    print(f"   Error reading dataset: {e}")

print("\n2. Current users in database:")
users_df = pd.read_csv('bank_details.csv')
for _, row in users_df.iterrows():
    password_type = "HASHED" if len(str(row['password'])) == 64 else "PLAIN"
    print(f"   {row['unique_id']}: {row['name']} - {password_type}")

print("\n3. Dataset directories:")
try:
    import os
    dirs = [d for d in os.listdir('dataset') if os.path.isdir(f"dataset/{d}")]
    print(f"   Found directories: {sorted(dirs)}")
except:
    print("   No dataset directory found")

print("\n4. Password verification test:")
test_passwords = {
    11111: "12345678",
    28507: "parth2004", 
    81694: "Surya@2003",
    50914: "123456789",
    94519: "Dhruv@2004"
}

for user_id, password in test_passwords.items():
    result = db.authenticate_user(user_id, password)
    user = db.get_user_by_id(user_id)
    if user:
        print(f"   User {user_id} ({user['name']}): {'✅ PASS' if result else '❌ FAIL'} with '{password}'")

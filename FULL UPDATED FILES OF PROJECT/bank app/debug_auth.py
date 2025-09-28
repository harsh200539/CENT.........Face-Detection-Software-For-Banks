#!/usr/bin/env python3

import sys
sys.path.append('backend')
from database import BankDatabase
import hashlib

# Initialize database
db = BankDatabase('bank_details.csv', 'transactions.csv')

# Test authentication for existing users
print("=== Testing Authentication ===")

# Get user 11111 (Harshvardhan Patil) 
user = db.get_user_by_id(11111)
if user:
    print(f"User 11111: {user['name']}")
    print(f"Stored password: {user['password']}")
    print(f"Password length: {len(user['password'])}")
    
    # Test password authentication
    test_password = "12345678"
    print(f"Testing password: {test_password}")
    
    # Test direct comparison (old method)
    if user['password'] == test_password:
        print("✓ Direct comparison works")
    else:
        print("✗ Direct comparison failed")
    
    # Test hashed comparison
    hashed = hashlib.sha256(test_password.encode()).hexdigest()
    print(f"Hashed version: {hashed}")
    
    if user['password'] == hashed:
        print("✓ Hashed comparison works")
    else:
        print("✗ Hashed comparison failed")
    
    # Test authenticate_user method
    auth_result = db.authenticate_user(11111, test_password)
    print(f"authenticate_user result: {auth_result}")

print("\n=== Testing User 94519 ===")
user2 = db.get_user_by_id(94519)
if user2:
    print(f"User 94519: {user2['name']}")
    print(f"Stored password: {user2['password']}")
    print(f"Password length: {len(user2['password'])}")
    
    test_password2 = "Dhruv@2004"
    auth_result2 = db.authenticate_user(94519, test_password2)
    print(f"authenticate_user result for {test_password2}: {auth_result2}")

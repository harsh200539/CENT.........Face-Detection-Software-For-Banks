# CENT Face Banking System - Backend Server
# This file contains the Flask application that powers the banking system
# including face recognition, user authentication, and banking operations

# Flask and web-related imports
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_from_directory
from flask_cors import CORS  # Cross-Origin Resource Sharing support

# Data processing and storage
import pandas as pd
import csv
import json

# System and file handling
import os
import sys
import io
from datetime import datetime
import random

# Image processing and face recognition
import cv2
import numpy as np
import pickle
import base64
from PIL import Image
import imutils

# Machine learning
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC

# Initialize Flask application with frontend directories
app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
app.secret_key = 'your-secret-key-here-change-in-production'  # SECURITY: Change this in production
CORS(app, supports_credentials=True)  # Enable CORS for API access

# Configure session security and behavior
app.config['SESSION_COOKIE_SECURE'] = False  # For development (set to True in production with HTTPS)
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access for security
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Mitigate CSRF attacks
app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow localhost
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session expires after 1 hour

# Import custom modules for face recognition and database operations
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models.face_recognition import FaceRecognition  # Custom face recognition implementation
from database import BankDatabase  # Custom database handler

# Initialize face recognition system
face_recognition = FaceRecognition()

# Define database file paths
DB_FILE = '../bank_details.csv'  # User account information
TRANSACTIONS_FILE = '../transactions.csv'  # Transaction history

# Initialize database connection
db = BankDatabase(DB_FILE, TRANSACTIONS_FILE)

# Routes

@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user account
    
    Accepts JSON with name and password fields
    Creates a new user in the database and establishes a session
    
    Returns:
        JSON response with success status and user information
    """
    try:
        # Parse request data
        data = request.get_json()
        name = data.get('name')
        password = data.get('password')
        
        # Validate required fields
        if not name or not password:
            return jsonify({'success': False, 'message': 'Name and password are required'})
        
        # Validate password strength
        if len(password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters'})
        
        # Check if user already exists
        existing_user = db.get_user_by_name(name)
        if existing_user:
            return jsonify({'success': False, 'message': 'User already exists'})
            
        # Create user in database
        user = db.create_user(name, password)
        if user:
            # Set session for the new user
            session['user_id'] = int(user['unique_id'])
            session['user_name'] = str(user['name'])
            session['logged_in'] = True
            session['account_number'] = int(user['account_number'])
            session.permanent = True
            print(f"[DEBUG] Session set for user {user['unique_id']}: {dict(session)}")
            
            # Remove password from response for security
            user_response = {k: v for k, v in user.items() if k != 'password'}
            
            return jsonify({
                'success': True,
                'message': 'User registered successfully',
                'user': user_response,
                'session_id': session.get('user_id')
            })
        else:
            return jsonify({'success': False, 'message': 'Registration failed'})
    except Exception as e:
        # Log error and return failure response
        print(f"[ERROR] Registration error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/face-verify', methods=['POST'])
def face_verify():
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'No image provided'})
        
        # Decode base64 image
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]  # Remove data:image/jpeg;base64, prefix
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Perform face recognition
        result = face_recognition.recognize_face(image)
        print(f"[DEBUG] Face recognition result: {result}")
        
        if result['success']:
            user = db.get_user_by_id(result['user_id'])
            if user:
                # Set session explicitly with proper type conversion
                session.clear()  # Clear any existing session
                session['user_id'] = int(result['user_id'])  # Ensure Python int
                session['user_name'] = str(user['name'])  # Ensure Python str
                session['logged_in'] = True
                session['account_number'] = int(user['account_number'])
                session.permanent = True
                # Force session save
                session.modified = True
                # Update last login
                db.update_last_login(result['user_id'])
                print(f"[DEBUG] Face verification session set for user {result['user_id']}: {dict(session)}")
                
                # Remove password from user response
                user_response = {k: v for k, v in user.items() if k != 'password'}
                
                return jsonify({
                    'success': True,
                    'message': f'Face recognized as {user["name"]} (ID: {result["user_id"]})',
                    'user': user_response,
                    'session_id': session.get('user_id'),
                    'recognized_user': {
                        'id': result['user_id'],
                        'name': user['name'],
                        'account_number': user['account_number']
                    }
                })
            else:
                return jsonify({'success': False, 'message': 'User not found in database'})
        
        return jsonify({'success': False, 'message': result.get('message', 'Face not recognized')})
    except Exception as e:
        print(f"[ERROR] Face verification error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/verify-password', methods=['POST'])
def verify_password():
    try:
        data = request.get_json()
        password = data.get('password')
        user_id = session.get('user_id')
        
        print(f"[DEBUG] Password verification - Session: {dict(session)}")
        print(f"[DEBUG] User ID from session: {user_id}")
        print(f"[DEBUG] Password received: {password}")
        
        if not user_id:
            print(f"[ERROR] No user session found")
            return jsonify({'success': False, 'message': 'No user session'})
        
        # Get user details for debugging
        user = db.get_user_by_id(user_id)
        if user:
            print(f"[DEBUG] User found: {user['name']} (ID: {user_id})")
            print(f"[DEBUG] Stored password: {user['password']}")
            print(f"[DEBUG] Password length: {len(user['password'])}")
        else:
            print(f"[ERROR] User not found in database: {user_id}")
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Fix: Ensure user_id is an integer for authentication
        user_id = int(user_id)
        auth_result = db.authenticate_user(user_id, password)
        print(f"[DEBUG] Authentication result: {auth_result}")
        
        if auth_result:
            print(f"[SUCCESS] Password verified for user {user_id}")
            # Set session data explicitly
            session.permanent = True
            session['user_id'] = int(user_id)
            session['user_name'] = str(user['name'])
            session['logged_in'] = True
            session['account_number'] = int(user['account_number'])
            # Force session save
            session.modified = True
            # Update last login time on successful password verification
            db.update_last_login(user_id)
            return jsonify({
                'success': True, 
                'message': 'Password verified',
                'user': {
                    'unique_id': int(user['unique_id']),
                    'name': str(user['name']),
                    'account_number': int(user['account_number']),
                    'account_balance': float(user['account_balance'])
                }
            })
        else:
            print(f"[ERROR] Password verification failed for user {user_id}")
            return jsonify({'success': False, 'message': 'Invalid password'})
    except Exception as e:
        print(f"[ERROR] Exception in verify_password: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/login-direct', methods=['POST'])
def login_direct():
    """Direct login with username and password (bypass face recognition)"""
    try:
        data = request.get_json()
        name = data.get('name')
        password = data.get('password')
        
        print(f"[DEBUG] Direct login attempt - Name: {name}")
        
        if not name or not password:
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        # Find user by name
        users_df = pd.read_csv(db.db_file)
        matching_users = users_df[users_df['name'].str.lower() == name.lower()]
        
        if matching_users.empty:
            return jsonify({'success': False, 'message': 'User not found'})
        
        user_row = matching_users.iloc[0]
        user_id = user_row['unique_id']
        
        # Authenticate user
        if db.authenticate_user(user_id, password):
            # Set session with proper int conversion
            session.clear()
            session['user_id'] = int(user_id)  # Convert pandas int64 to Python int
            session['user_name'] = str(user_row['name'])  # Ensure string
            session['logged_in'] = True
            session['account_number'] = int(user_row['account_number'])
            session.permanent = True
            # Force session save
            session.modified = True
            
            # Update last login
            db.update_last_login(user_id)
            
            print(f"[SUCCESS] Direct login successful for user {user_id}")
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': int(user_id),  # Convert to Python int
                    'name': str(user_row['name']),  # Convert to Python str
                    'account_number': int(user_row['account_number']),  # Convert to Python int
                    'account_balance': float(user_row['account_balance'])  # Convert to Python float
                }
            })
        else:
            print(f"[WARNING] Failed login attempt for user: {name}")
            return jsonify({'success': False, 'message': 'Invalid credentials'})
            
    except Exception as e:
        print(f"[ERROR] Exception in login_direct: {e}")
        return jsonify({'success': False, 'message': f'Login failed: {str(e)}'})

@app.route('/api/balance')
def get_balance():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No user session'})
        
        user = db.get_user_by_id(user_id)
        if user:
            return jsonify({
                'success': True,
                'balance': user['account_balance']
            })
        else:
            return jsonify({'success': False, 'message': 'User not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/deposit', methods=['POST'])
def deposit():
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'No user session'})
        
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Invalid amount'})
        
        success, result = db.deposit_money(user_id, amount, "Manual deposit")
        if success:
            return jsonify({
                'success': True,
                'message': 'Deposit successful',
                'new_balance': result
            })
        else:
            return jsonify({'success': False, 'message': 'Deposit failed'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'No user session'})
        
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Invalid amount'})
        
        success, message, new_balance = db.withdraw_money(user_id, amount, "Manual withdrawal")
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'new_balance': new_balance
            })
        else:
            return jsonify({'success': False, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/transfer', methods=['POST'])
def transfer():
    try:
        data = request.get_json()
        to_account = int(data.get('to_account'))
        amount = float(data.get('amount', 0))
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'No user session'})
        
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Invalid amount'})
        
        if to_account == user_id:
            return jsonify({'success': False, 'message': 'Cannot transfer to yourself'})
        
        success, message = db.transfer_money(user_id, to_account, amount)
        if success:
            user = db.get_user_by_id(user_id)
            return jsonify({
                'success': True,
                'message': message,
                'new_balance': user['account_balance']
            })
        else:
            return jsonify({'success': False, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/logout')
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/capture-face', methods=['POST'])
def capture_face():
    try:
        data = request.get_json()
        images = data.get('images', [])
        user_id = data.get('user_id')
        
        if not user_id or not images:
            return jsonify({'success': False, 'message': 'User ID and images required'})
        
        # Save images and train model
        success = face_recognition.capture_and_train(user_id, images)
        
        if success:
            return jsonify({'success': True, 'message': 'Face captured and model trained'})
        else:
            return jsonify({'success': False, 'message': 'Face capture failed'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/transaction-history')
def get_transaction_history():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No user session'})
        
        transactions = db.get_transaction_history(user_id)
        
        # Format transactions for frontend
        formatted_transactions = []
        for tx in transactions:
            formatted_transactions.append({
                'id': tx['transaction_id'],
                'type': tx['type'],
                'amount': float(tx['amount']),
                'date': tx['timestamp'].split(' ')[0],  # Just the date part
                'description': tx['description']
            })
        
        return jsonify({'success': True, 'transactions': formatted_transactions})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/user-profile')
def get_user_profile():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No user session'})
        
        user = db.get_user_by_id(user_id)
        if user:
            # Remove password from response
            user_profile = {k: v for k, v in user.items() if k != 'password'}
            return jsonify({'success': True, 'profile': user_profile})
        else:
            return jsonify({'success': False, 'message': 'User not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No user session'})
        
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'success': False, 'message': 'Name is required'})
        
        # Update user name in database
        success = db.update_user_profile(user_id, name)
        if not success:
            return jsonify({'success': False, 'message': 'Profile update failed'})
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/change-password', methods=['POST'])
def change_password():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'No user session'})
        
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'success': False, 'message': 'Current and new password required'})
        
        if len(new_password) < 8:
            return jsonify({'success': False, 'message': 'New password must be at least 8 characters'})
        
        # Verify current password
        if not db.authenticate_user(user_id, current_password):
            return jsonify({'success': False, 'message': 'Current password is incorrect'})
        
        # Update password
        success = db.change_password(user_id, new_password)
        if not success:
            return jsonify({'success': False, 'message': 'Password change failed'})
        
        return jsonify({'success': True, 'message': 'Password changed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/admin/users')
def get_all_users():
    try:
        # Simple admin check - in production, use proper authentication
        users = db.get_all_users()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5001)

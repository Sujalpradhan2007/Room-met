import os
import sqlite3
import random
import string
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

DB_NAME = 'room_management.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            room_code TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Rooms table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            room_code TEXT PRIMARY KEY,
            room_name TEXT NOT NULL,
            rent REAL DEFAULT 0.0,
            gas REAL DEFAULT 0.0,
            electricity REAL DEFAULT 0.0,
            water REAL DEFAULT 0.0,
            other_bills REAL DEFAULT 0.0,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Expenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            item_name TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT DEFAULT 'Grocery',
            month_year TEXT NOT NULL,
            expense_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Messages / Notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            sender_name TEXT NOT NULL,
            msg_type TEXT DEFAULT 'notification',
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Settlements history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT NOT NULL,
            month_year TEXT NOT NULL,
            total_groceries REAL NOT NULL,
            total_bills REAL NOT NULL,
            total_grand REAL NOT NULL,
            per_person REAL NOT NULL,
            summary_json TEXT NOT NULL,
            settled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

init_db()

def generate_room_code():
    while True:
        code = str(random.randint(100000, 999999))
        conn = get_db()
        room = conn.execute('SELECT room_code FROM rooms WHERE room_code = ?', (code,)).fetchone()
        conn.close()
        if not room:
            return code

@app.route('/')
def index():
    return render_template('index.html')

# ================= AUTH ENDPOINTS =================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not email or not username or not password:
        return jsonify({'error': 'Please fill in all details (Email, Username, Password)'}), 400

    conn = get_db()
    existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'This email is already registered!'}), 400

    hashed_pwd = generate_password_hash(password)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)',
                   (email, username, hashed_pwd))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    session['user_id'] = user_id
    session['username'] = username
    session['email'] = email

    return jsonify({
        'message': 'Account created successfully!',
        'user': {'id': user_id, 'username': username, 'email': email, 'room_code': None}
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Please enter Email and Password!'}), 400

    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid Email or Password!'}), 400

    session['user_id'] = user['id']
    session['username'] = user['username']
    session['email'] = user['email']

    return jsonify({
        'message': 'Login successful!',
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'room_code': user['room_code']
        }
    })

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    new_password = data.get('new_password', '')

    if not email or not new_password:
        return jsonify({'error': 'Please provide email and new password!'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long!'}), 400

    conn = get_db()
    user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'No account found with this email address!'}), 404

    hashed_pwd = generate_password_hash(new_password)
    conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hashed_pwd, user['id']))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Password reset successfully! You can now log in.'})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/me', methods=['GET'])
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'authenticated': False}), 200

    conn = get_db()
    user = conn.execute('SELECT id, email, username, room_code FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()

    if not user:
        session.clear()
        return jsonify({'authenticated': False}), 200

    return jsonify({
        'authenticated': True,
        'user': dict(user)
    })


# ================= ROOM ENDPOINTS =================
@app.route('/api/room/generate-code', methods=['GET'])
def get_generated_code():
    return jsonify({'room_code': generate_room_code()})

@app.route('/api/room/create', methods=['POST'])
def create_room():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Please login first!'}), 401

    data = request.get_json() or {}
    room_name = data.get('room_name', '').strip()
    provided_code = data.get('room_code', '').strip().upper()

    conn = get_db()

    if provided_code:
        existing = conn.execute('SELECT room_code FROM rooms WHERE room_code = ?', (provided_code,)).fetchone()
        if existing:
            conn.close()
            return jsonify({'error': 'This Room Code already exists! Please generate a new one.'}), 400
        room_code = provided_code
    else:
        room_code = generate_room_code()

    if not room_name:
        user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
        username = user['username'] if user else 'User'
        room_name = f"{username}'s Room"

    rent = float(data.get('rent', 0) or 0)
    gas = float(data.get('gas', 0) or 0)
    electricity = float(data.get('electricity', 0) or 0)
    water = float(data.get('water', 0) or 0)
    other_bills = float(data.get('other_bills', 0) or 0)

    # Create room
    conn.execute('''
        INSERT INTO rooms (room_code, room_name, rent, gas, electricity, water, other_bills, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (room_code, room_name, rent, gas, electricity, water, other_bills, user_id))

    # Update user's room_code
    conn.execute('UPDATE users SET room_code = ? WHERE id = ?', (room_code, user_id))

    # Welcome message in room
    conn.execute('''
        INSERT INTO messages (room_code, user_id, sender_name, msg_type, title, message)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (room_code, 0, 'System', 'notification', 'New Room Created!', f'New room "{room_name}" has been created. Room Code: {room_code}'))

    conn.commit()
    conn.close()

    return jsonify({
        'message': f'Room "{room_name}" created successfully!',
        'room_code': room_code
    })

@app.route('/api/room/join', methods=['POST'])
def join_room():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Please login first!'}), 401

    data = request.get_json() or {}
    room_code = data.get('room_code', '').strip().upper()

    if not room_code:
        return jsonify({'error': 'Please enter a Room Code!'}), 400

    conn = get_db()
    room = conn.execute('SELECT * FROM rooms WHERE room_code = ?', (room_code,)).fetchone()
    if not room:
        conn.close()
        return jsonify({'error': 'Room Code not found! Please enter a valid Room Code.'}), 404

    user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    username = user['username'] if user else 'New Member'

    # Update user room code
    conn.execute('UPDATE users SET room_code = ? WHERE id = ?', (room_code, user_id))

    # Notify room
    conn.execute('''
        INSERT INTO messages (room_code, user_id, sender_name, msg_type, title, message)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (room_code, 0, 'System', 'notification', 'New Roommate Joined!', f'{username} has joined the room!'))

    conn.commit()
    conn.close()

    return jsonify({
        'message': f'You have joined room "{room["room_name"]}"!',
        'room_code': room_code
    })

@app.route('/api/room/leave', methods=['POST'])
def leave_room():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Please login first!'}), 401

    conn = get_db()
    conn.execute('UPDATE users SET room_code = NULL WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'You have left the room.'})

@app.route('/api/room/delete', methods=['DELETE'])
def delete_room():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Please login first!'}), 401

    conn = get_db()
    room = conn.execute('''
        SELECT r.room_code, r.created_by
        FROM rooms r
        JOIN users u ON u.room_code = r.room_code
        WHERE r.created_by = ? AND u.id = ?
    ''', (user_id, user_id)).fetchone()
    if not room:
        conn.close()
        return jsonify({'error': 'Only the room host can delete this room.'}), 403

    room_code = room['room_code']

    conn.execute('DELETE FROM expenses WHERE room_code = ?', (room_code,))
    conn.execute('DELETE FROM messages WHERE room_code = ?', (room_code,))
    conn.execute('DELETE FROM settlements WHERE room_code = ?', (room_code,))
    conn.execute('UPDATE users SET room_code = NULL WHERE room_code = ?', (room_code,))
    conn.execute('DELETE FROM rooms WHERE room_code = ?', (room_code,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Room deleted successfully.'})

@app.route('/api/room/member/remove', methods=['POST'])
def remove_room_member():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Please login first!'}), 401

    data = request.get_json() or {}
    member_id = data.get('member_id')
    if not member_id:
        return jsonify({'error': 'Please select a member to remove.'}), 400

    conn = get_db()
    room = conn.execute('''
        SELECT r.room_code, r.created_by
        FROM rooms r
        JOIN users u ON u.room_code = r.room_code
        WHERE r.created_by = ? AND u.id = ?
    ''', (user_id, user_id)).fetchone()
    if not room:
        conn.close()
        return jsonify({'error': 'Only the room host can remove members.'}), 403

    member = conn.execute('SELECT id, username, room_code FROM users WHERE id = ?', (member_id,)).fetchone()
    if not member:
        conn.close()
        return jsonify({'error': 'Member not found.'}), 404

    if int(member_id) == int(user_id):
        conn.close()
        return jsonify({'error': 'The host cannot remove themselves from the room.'}), 400

    if member['room_code'] != room['room_code']:
        conn.close()
        return jsonify({'error': 'This member is not part of your room.'}), 400

    conn.execute('UPDATE users SET room_code = NULL WHERE id = ?', (member_id,))
    conn.execute('''
        INSERT INTO messages (room_code, user_id, sender_name, msg_type, title, message)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (room['room_code'], 0, 'System', 'notification', 'Member Removed', f'{member["username"]} was removed from the room by the host.'))
    conn.commit()
    conn.close()

    return jsonify({'message': f'{member["username"]} was removed from the room.'})

@app.route('/api/room/info', methods=['GET'])
def get_room_info():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()
    user = conn.execute('SELECT room_code FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user or not user['room_code']:
        conn.close()
        return jsonify({'has_room': False}), 200

    room_code = user['room_code']
    room = conn.execute('SELECT * FROM rooms WHERE room_code = ?', (room_code,)).fetchone()
    members = conn.execute('SELECT id, username, email FROM users WHERE room_code = ?', (room_code,)).fetchall()
    conn.close()

    if not room:
        return jsonify({'has_room': False}), 200

    return jsonify({
        'has_room': True,
        'room': dict(room),
        'members': [dict(m) for m in members]
    })

@app.route('/api/room/update-bills', methods=['POST'])
def update_bills():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Please login first!'}), 401

    conn = get_db()
    user = conn.execute('SELECT room_code FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user or not user['room_code']:
        conn.close()
        return jsonify({'error': 'You are not a member of any room!'}), 400

    data = request.get_json() or {}
    rent = float(data.get('rent', 0) or 0)
    gas = float(data.get('gas', 0) or 0)
    electricity = float(data.get('electricity', 0) or 0)
    water = float(data.get('water', 0) or 0)
    other_bills = float(data.get('other_bills', 0) or 0)

    conn.execute('''
        UPDATE rooms
        SET rent = ?, gas = ?, electricity = ?, water = ?, other_bills = ?
        WHERE room_code = ?
    ''', (rent, gas, electricity, water, other_bills, user['room_code']))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Room rent and bills updated successfully!'})


# ================= EXPENSE ENDPOINTS =================
@app.route('/api/expenses', methods=['GET', 'POST'])
def handle_expenses():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Please login first!'}), 401

    conn = get_db()
    user = conn.execute('SELECT room_code, username FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user or not user['room_code']:
        conn.close()
        return jsonify({'error': 'Please join a room or create a new room first!'}), 400

    room_code = user['room_code']

    if request.method == 'POST':
        data = request.get_json() or {}
        item_name = data.get('item_name', '').strip()
        amount = float(data.get('amount', 0) or 0)
        category = data.get('category', 'Grocery').strip()
        expense_date = data.get('expense_date', datetime.now().strftime('%Y-%m-%d'))

        if not item_name or amount <= 0:
            conn.close()
            return jsonify({'error': 'Please enter item name and a valid price!'}), 400

        month_year = expense_date[:7] # 'YYYY-MM'

        conn.execute('''
            INSERT INTO expenses (room_code, user_id, user_name, item_name, amount, category, month_year, expense_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (room_code, user_id, user['username'], item_name, amount, category, month_year, expense_date))

        conn.commit()
        conn.close()

        return jsonify({'message': f'"{item_name}" (₹{amount}) added successfully!'})

    else: # GET
        month = request.args.get('month', datetime.now().strftime('%Y-%m'))
        expenses = conn.execute('''
            SELECT * FROM expenses
            WHERE room_code = ? AND month_year = ?
            ORDER BY expense_date DESC, id DESC
        ''', (room_code, month)).fetchall()
        conn.close()

        return jsonify({
            'expenses': [dict(e) for e in expenses],
            'month': month
        })

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()
    user = conn.execute('SELECT room_code FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user or not user['room_code']:
        conn.close()
        return jsonify({'error': 'Room not found'}), 400

    expense = conn.execute('SELECT * FROM expenses WHERE id = ? AND room_code = ?',
                           (expense_id, user['room_code'])).fetchone()
    if not expense:
        conn.close()
        return jsonify({'error': 'Expense not found!'}), 404

    conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Item expense record deleted successfully!'})


def get_settlement_data(conn, room_code, month):
    room = conn.execute('SELECT * FROM rooms WHERE room_code = ?', (room_code,)).fetchone()
    members = conn.execute('SELECT id, username, email FROM users WHERE room_code = ?', (room_code,)).fetchall()
    expenses = conn.execute('SELECT * FROM expenses WHERE room_code = ? AND month_year = ?', (room_code, month)).fetchall()

    if not members:
        return None

    num_members = len(members)

    rent = float(room['rent'] or 0)
    gas = float(room['gas'] or 0)
    electricity = float(room['electricity'] or 0)
    water = float(room['water'] or 0)
    other_bills = float(room['other_bills'] or 0)
    total_bills_setting = rent + gas + electricity + water + other_bills

    # Separate groceries vs bill expenses
    bill_categories = ['Room Rent', 'Gas Bill', 'Electric Bill', 'Water Bill', 'Utilities']

    total_groceries = 0.0
    total_logged_bills = 0.0
    user_paid_map = {m['id']: 0.0 for m in members}

    for e in expenses:
        amt = float(e['amount'])
        uid = e['user_id']
        if uid in user_paid_map:
            user_paid_map[uid] += amt

        if e['category'] in bill_categories or 'Rent' in e['item_name'] or 'Bill' in e['item_name']:
            total_logged_bills += amt
        else:
            total_groceries += amt

    unassigned_bills = max(0.0, total_bills_setting - total_logged_bills)
    grand_total = total_groceries + total_logged_bills + unassigned_bills
    per_head_share = round(grand_total / num_members, 2) if num_members > 0 else 0

    member_summary = []
    debtors = []
    creditors = []

    for m in members:
        uid = m['id']
        name = m['username']
        paid = user_paid_map[uid]
        net_balance = round(paid - per_head_share, 2)

        member_summary.append({
            'user_id': uid,
            'username': name,
            'paid': paid,
            'share': per_head_share,
            'net_balance': net_balance,
            'status': 'receive' if net_balance > 0 else ('pay' if net_balance < 0 else 'settled')
        })

        if net_balance < 0:
            debtors.append({'id': uid, 'name': name, 'amount': abs(net_balance)})
        elif net_balance > 0:
            creditors.append({'id': uid, 'name': name, 'amount': net_balance})

    # Minimal transaction transfers
    transactions = []
    i, j = 0, 0
    debtors_copy = [{'id': d['id'], 'name': d['name'], 'amount': d['amount']} for d in debtors]
    creditors_copy = [{'id': c['id'], 'name': c['name'], 'amount': c['amount']} for c in creditors]

    while i < len(debtors_copy) and j < len(creditors_copy):
        d = debtors_copy[i]
        c = creditors_copy[j]

        transfer = min(d['amount'], c['amount'])
        if transfer > 0.01:
            transactions.append({
                'from_id': d['id'],
                'from_name': d['name'],
                'to_id': c['id'],
                'to_name': c['name'],
                'amount': round(transfer, 2)
            })

        d['amount'] = round(d['amount'] - transfer, 2)
        c['amount'] = round(c['amount'] - transfer, 2)

        if d['amount'] <= 0.01:
            i += 1
        if c['amount'] <= 0.01:
            j += 1

    return {
        'month': month,
        'room_name': room['room_name'],
        'room_code': room_code,
        'num_members': num_members,
        'bills_breakdown': {
            'rent': rent,
            'gas': gas,
            'electricity': electricity,
            'water': water,
            'other': other_bills,
            'total_bills': total_bills_setting
        },
        'total_groceries': round(total_groceries, 2),
        'total_logged_bills': round(total_logged_bills, 2),
        'unassigned_bills': round(unassigned_bills, 2),
        'grand_total': round(grand_total, 2),
        'per_head_share': per_head_share,
        'members_summary': member_summary,
        'transactions': transactions
    }


# ================= SETTLEMENT / MONTH-END CALCULATOR =================
@app.route('/api/settlements/calculate', methods=['GET'])
def calculate_settlement():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Please login first!'}), 401

    conn = get_db()
    user = conn.execute('SELECT room_code FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user or not user['room_code']:
        conn.close()
        return jsonify({'error': 'You are not in any room!'}), 400

    room_code = user['room_code']
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))

    data = get_settlement_data(conn, room_code, month)
    conn.close()

    if not data:
        return jsonify({'error': 'Room details not found!'}), 400

    return jsonify(data)


@app.route('/api/settlements/finalize', methods=['POST'])
def finalize_settlement():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Please login first!'}), 401

    data = request.get_json() or {}
    month = data.get('month', datetime.now().strftime('%Y-%m'))

    conn = get_db()
    user = conn.execute('SELECT room_code, username FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user or not user['room_code']:
        conn.close()
        return jsonify({'error': 'You are not in any room!'}), 400

    room_code = user['room_code']
    settlement = get_settlement_data(conn, room_code, month)

    if not settlement:
        conn.close()
        return jsonify({'error': 'Could not calculate settlement!'}), 400

    # Generate messages for each user ID
    for m in settlement['members_summary']:
        uid = m['user_id']
        paid = m['paid']
        per_head = settlement['per_head_share']
        diff = m['net_balance']

        if diff > 0:
            status_txt = f"You paid a total of ₹{paid}. Your per-head share is ₹{per_head}. You will RECEIVE ₹{diff}."
        elif diff < 0:
            status_txt = f"You paid a total of ₹{paid}. Your per-head share is ₹{per_head}. You NEED TO PAY ₹{abs(diff)}."
        else:
            status_txt = f"Your balance is settled (Per head: ₹{per_head}). Clear!"

        msg_title = f"🗓 Month End Bill Statement ({month})"
        msg_body = (f"Room: {settlement['room_name']} | Month: {month}\n"
                    f"Total Room Expense: ₹{settlement['grand_total']} (Groceries: ₹{settlement['total_groceries']}, Bills: ₹{settlement['bills_breakdown']['total_bills']})\n"
                    f"Per Person Share: ₹{per_head}\n\n"
                    f"👉 {status_txt}")

        conn.execute('''
            INSERT INTO messages (room_code, user_id, sender_name, msg_type, title, message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (room_code, uid, 'Month End Bot', 'month_end_bill', msg_title, msg_body))

    # Save settlement history record
    conn.execute('''
        INSERT INTO settlements (room_code, month_year, total_groceries, total_bills, total_grand, per_person, summary_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (room_code, month, settlement['total_groceries'], settlement['bills_breakdown']['total_bills'], settlement['grand_total'], settlement['per_head_share'], json.dumps(settlement)))

    conn.commit()
    conn.close()

    return jsonify({
        'message': f'Settlement for {month} finalized and messages sent to all room members!'
    })


# ================= MESSAGES & CHAT ENDPOINTS =================
@app.route('/api/messages', methods=['GET', 'POST'])
def handle_messages():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Please login first!'}), 401

    conn = get_db()
    user = conn.execute('SELECT room_code, username FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user or not user['room_code']:
        conn.close()
        return jsonify({'error': 'You are not in any room!'}), 400

    room_code = user['room_code']

    if request.method == 'POST':
        data = request.get_json() or {}
        text = data.get('message', '').strip()
        if not text:
            conn.close()
            return jsonify({'error': 'Cannot send an empty message!'}), 400

        conn.execute('''
            INSERT INTO messages (room_code, user_id, sender_name, msg_type, title, message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (room_code, 0, user['username'], 'chat', 'Room Chat', text))

        conn.commit()
        conn.close()
        return jsonify({'message': 'Message sent successfully!'})

    else: # GET
        # Messages targeted to this user (user_id = uid) OR targeted to room broadcast (user_id = 0)
        msgs = conn.execute('''
            SELECT * FROM messages
            WHERE room_code = ? AND (user_id = ? OR user_id = 0)
            ORDER BY created_at DESC LIMIT 50
        ''', (room_code, user_id)).fetchall()

        unread_count = conn.execute('''
            SELECT COUNT(*) as count FROM messages
            WHERE room_code = ? AND (user_id = ? OR user_id = 0) AND is_read = 0
        ''', (room_code, user_id)).fetchone()['count']

        conn.close()

        return jsonify({
            'messages': [dict(m) for m in msgs],
            'unread_count': unread_count
        })

@app.route('/api/messages/<int:msg_id>/read', methods=['POST'])
def mark_read(msg_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()
    conn.execute('UPDATE messages SET is_read = 1 WHERE id = ?', (msg_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Read marked'})


if __name__ == '__main__':
    print("🚀 Room Management Website Starting on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

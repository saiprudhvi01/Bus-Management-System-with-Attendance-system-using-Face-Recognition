from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os
import sqlite3
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import requests
import urllib.parse
import base64
import hashlib

app = Flask(__name__)
app.secret_key = 'smart_campus_transit_2024'

# Configuration
UPLOAD_FOLDER = 'static/uploads'
PASS_PHOTOS_FOLDER = 'static/pass_photos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# WhatsApp Configuration - TextMeBot
WHATSAPP_CONFIG = {
    'api_url': 'http://api.textmebot.com/send.php',
    'phone_number': '+917893277617',  # Your WhatsApp number
    'api_key': '8TTpz87ybvbb'  # Your TextMeBot API key
}

# Create directories
for folder in [UPLOAD_FOLDER, PASS_PHOTOS_FOLDER, 'static/temp']:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PASS_PHOTOS_FOLDER'] = PASS_PHOTOS_FOLDER

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# WhatsApp function
def send_whatsapp_to_parent(parent_phone, student_name, driver_name, location, distance_left, time_required, custom_message):
    """Send WhatsApp notification to parent using TextMeBot API"""
    try:
        print(f"DEBUG: Attempting to send WhatsApp to {parent_phone}")
        
        # Format the message
        message = f"""🚌 *Smart Campus Transit System*

📋 *Student Update*
👤 Student: {student_name}
👨‍✈️ Driver: {driver_name}
📍 Current Location: {location}
🛣️ Distance Left: {distance_left}
⏰ Time Required: {time_required}

💬 *Driver Message:* {custom_message}

---
This is an automated message from Smart Campus Transit System."""
        
        # Clean phone number and add +91 prefix for TextMeBot
        clean_phone = parent_phone.replace('+91-', '').replace('+', '').replace('-', '').replace(' ', '')
        if not clean_phone.startswith('+91'):
            clean_phone = '+91' + clean_phone
        
        # URL encode the message
        encoded_message = urllib.parse.quote(message)
        
        # TextMeBot API URL (correct format from documentation)
        api_url = f"http://api.textmebot.com/send.php?recipient={clean_phone}&apikey={WHATSAPP_CONFIG['api_key']}&text={encoded_message}"
        
        print(f"DEBUG: Sending WhatsApp via TextMeBot API...")
        print(f"DEBUG: Phone: {clean_phone}")
        print(f"DEBUG: API Key: {WHATSAPP_CONFIG['api_key']}")
        print(f"DEBUG: API URL: {api_url}")
        
        # Send WhatsApp message
        response = requests.get(api_url, timeout=30)
        
        print(f"DEBUG: Response Status Code: {response.status_code}")
        print(f"DEBUG: Response Text: {response.text}")
        
        if response.status_code == 200:
            print("DEBUG: WhatsApp message sent successfully via TextMeBot!")
            # Check if response contains success message
            if "success" in response.text.lower() or "sent" in response.text.lower():
                return True, "WhatsApp message sent successfully"
            elif "failed" in response.text.lower() or "invalid" in response.text.lower():
                # Extract the error message
                if "Invalid Destination WhatsApp number" in response.text:
                    return False, "Failed: The recipient's WhatsApp number is not valid or not registered with WhatsApp"
                elif "not in contacts" in response.text.lower():
                    return False, "Failed: Recipient must be in your WhatsApp contacts"
                else:
                    return False, f"Failed: {response.text.split('Result: <b>Failed</b> -')[-1].strip() if 'Result:' in response.text else 'Unknown error'}"
            else:
                print(f"DEBUG: API returned 200 but response indicates issue: {response.text}")
                return True, f"WhatsApp message queued (API response: {response.text[:100]})"
        else:
            print(f"DEBUG: TextMeBot error: {response.status_code} - {response.text}")
            return False, f"WhatsApp API error: {response.status_code} - {response.text}"
        
    except Exception as e:
        print(f"DEBUG: WhatsApp error: {str(e)}")
        return False, f"Failed to send WhatsApp message: {str(e)}"

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect('transit_system.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_student_by_user_id(user_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return student

# Routes
@app.route('/')
def index():
    return render_template('transit_index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'driver':
                return redirect(url_for('driver_dashboard'))
            elif user['role'] == 'student':
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session['role'] != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get statistics
    total_students = conn.execute('SELECT COUNT(*) as count FROM students').fetchone()['count']
    total_drivers = conn.execute('SELECT COUNT(*) as count FROM users WHERE role = "driver"').fetchone()['count']
    approved_passes = conn.execute('SELECT COUNT(*) as count FROM bus_passes WHERE status = "approved"').fetchone()['count']
    pending_passes = conn.execute('SELECT COUNT(*) as count FROM bus_passes WHERE status = "pending"').fetchone()['count']
    
    # Get recent applications
    recent_applications = conn.execute('''
        SELECT s.name, s.student_id, b.pass_number, b.route, b.status, b.created_at, b.pass_id
        FROM bus_passes b
        JOIN students s ON b.student_id = s.student_id
        ORDER BY b.created_at DESC
        LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         total_students=total_students,
                         total_drivers=total_drivers,
                         approved_passes=approved_passes,
                         pending_passes=pending_passes,
                         recent_applications=recent_applications)

@app.route('/driver/dashboard')
@login_required
def driver_dashboard():
    if session['role'] != 'driver':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get statistics
    today_attendance = conn.execute('SELECT COUNT(*) as count FROM attendance WHERE date = ?', 
                                   (datetime.now().strftime('%Y-%m-%d'),)).fetchone()['count']
    total_students = conn.execute('SELECT COUNT(*) as count FROM students').fetchone()['count']
    active_passes = conn.execute('SELECT COUNT(*) as count FROM bus_passes WHERE status = "approved"').fetchone()['count']
    
    conn.close()
    
    return render_template('driver_dashboard.html',
                         today_attendance=today_attendance,
                         total_students=total_students,
                         active_passes=active_passes)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if session['role'] != 'student':
        return redirect(url_for('index'))
    
    student = get_student_by_user_id(session['user_id'])
    
    if not student:
        flash('Student profile not found', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get student's bus pass
    bus_pass = conn.execute('SELECT * FROM bus_passes WHERE student_id = ? ORDER BY created_at DESC LIMIT 1', 
                           (student['student_id'],)).fetchone()
    
    # Get attendance history
    attendance_history = conn.execute('''
        SELECT date, boarding_time, status, verification_type
        FROM attendance 
        WHERE student_id = ?
        ORDER BY date DESC
        LIMIT 10
    ''', (student['student_id'],)).fetchall()
    
    conn.close()
    
    return render_template('student_dashboard.html', 
                         student=student, 
                         bus_pass=bus_pass,
                         attendance_history=attendance_history)

@app.route('/register')
def register():
    return render_template('register.html')

def simple_face_recognition(image_data):
    """Simple face recognition using image hashing"""
    try:
        # Decode base64 image
        image_data = image_data.split(',')[1]  # Remove data:image/jpeg;base64, prefix
        image_bytes = base64.b64decode(image_data)
        
        # Create hash of the image
        image_hash = hashlib.md5(image_bytes).hexdigest()
        
        # Simple face database (in production, use proper face recognition)
        face_database = {
            'sai': 'a1b2c3d4e5f6',  # Mock hash for sai
            'student': 'f6e5d4c3b2a1',  # Mock hash for student
        }
        
        # Simple matching (in real app, use proper face recognition)
        for name, face_hash in face_database.items():
            if abs(hash(image_hash) - hash(face_hash)) < 100:  # Simple similarity check
                return name
        
        return None
        
    except Exception as e:
        print(f"Face recognition error: {e}")
        return None

@app.route('/recognize')
def recognize():
    if 'user_id' in session and session['role'] == 'driver':
        return render_template('recognize-render.html')
    else:
        return redirect(url_for('login'))

@app.route('/api/recognize', methods=['POST'])
def api_recognize():
    if 'user_id' not in session or session['role'] != 'driver':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        image_data = request.json.get('image')
        if not image_data:
            return jsonify({'success': False, 'message': 'No image provided'})
        
        # Perform face recognition
        recognized_name = simple_face_recognition(image_data)
        
        if recognized_name:
            # Get student info
            conn = get_db_connection()
            student = conn.execute('SELECT * FROM students WHERE name = ?', (recognized_name,)).fetchone()
            
            if student:
                # Get bus pass
                bus_pass = conn.execute('SELECT * FROM bus_passes WHERE student_id = ? AND status = "approved"', 
                                      (student['student_id'],)).fetchone()
                
                if bus_pass:
                    # Mark attendance
                    conn.execute('''
                        INSERT INTO attendance (student_id, pass_id, date, boarding_time, verification_type, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (student['student_id'], bus_pass['pass_id'], datetime.now().strftime('%Y-%m-%d'), 
                          datetime.now().strftime('%H:%M:%S'), 'face_recognition', 'present'))
                    conn.commit()
                    conn.close()
                    
                    return jsonify({
                        'success': True,
                        'student': {
                            'name': student['name'],
                            'pass_number': bus_pass['pass_number'],
                            'route': bus_pass['route']
                        },
                        'message': f'Attendance marked for {student["name"]}'
                    })
                else:
                    conn.close()
                    return jsonify({'success': False, 'message': 'No valid bus pass found'})
            else:
                conn.close()
                return jsonify({'success': False, 'message': 'Student not found'})
        else:
            return jsonify({'success': False, 'message': 'Face not recognized'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/student_register')
def student_register():
    return render_template('student_register.html')

@app.route('/apply_pass')
@login_required
def apply_pass():
    if session['role'] != 'student':
        return redirect(url_for('index'))
    
    student = get_student_by_user_id(session['user_id'])
    
    if not student:
        flash('Student profile not found', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Check if student already has a pass
    existing_pass = conn.execute('SELECT * FROM bus_passes WHERE student_id = ? ORDER BY created_at DESC LIMIT 1', 
                               (student['student_id'],)).fetchone()
    
    conn.close()
    
    return render_template('apply_pass.html', student=student, existing_pass=existing_pass)

@app.route('/driver/update_location', methods=['GET', 'POST'])
@login_required
def driver_update_location():
    if session['role'] != 'driver':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        location = request.form.get('location')
        destination = request.form.get('destination')
        distance_left = request.form.get('distance_left')
        time_required = request.form.get('time_required')
        custom_message = request.form.get('custom_message')
        
        # Save location update to database
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO bus_locations (driver_id, current_location, destination, distance_left, time_required, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], location, destination, distance_left, time_required, custom_message, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        
        flash('Location updated successfully!', 'success')
        return redirect(url_for('driver_dashboard'))
    
    return render_template('driver_update_location.html')

@app.route('/api/bus_location')
def get_bus_location():
    conn = get_db_connection()
    location = conn.execute('''
        SELECT current_location, destination, distance_left, time_required, message, created_at
        FROM bus_locations 
        ORDER BY created_at DESC 
        LIMIT 1
    ''').fetchone()
    conn.close()
    
    if location:
        return jsonify({
            'success': True,
            'location': dict(location)
        })
    else:
        return jsonify({
            'success': False,
            'message': 'No location updates available'
        })

@app.route('/driver/attendance', methods=['GET', 'POST'])
@login_required
def driver_attendance():
    if session['role'] != 'driver':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        status = request.form.get('status', 'present')
        
        # Get student and pass info
        conn = get_db_connection()
        student = conn.execute('SELECT * FROM students WHERE student_id = ?', (student_id,)).fetchone()
        bus_pass = conn.execute('SELECT * FROM bus_passes WHERE student_id = ? AND status = "approved"', (student_id,)).fetchone()
        
        if student and bus_pass:
            # Mark attendance
            conn.execute('''
                INSERT INTO attendance (student_id, pass_id, date, boarding_time, verification_type, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student_id, bus_pass['pass_id'], datetime.now().strftime('%Y-%m-%d'), 
                  datetime.now().strftime('%H:%M:%S'), 'manual', status))
            conn.commit()
            
            flash(f'Attendance marked for {student["name"]}', 'success')
        else:
            flash('Student not found or no valid bus pass', 'error')
        
        conn.close()
        return redirect(url_for('driver_attendance'))
    
    # Get students with approved passes
    conn = get_db_connection()
    students = conn.execute('''
        SELECT s.student_id, s.name, b.pass_number, b.route
        FROM students s
        JOIN bus_passes b ON s.student_id = b.student_id
        WHERE b.status = 'approved'
    ''').fetchall()
    conn.close()
    
    return render_template('driver_attendance.html', students=students)

@app.route('/driver/send_parent_notification', methods=['GET', 'POST'])
@login_required
def driver_send_parent_notification():
    if session['role'] != 'driver':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        print("DEBUG: POST request received for parent notification")
        student_id = request.form.get('student_id')
        parent_phone = request.form.get('parent_phone')
        student_name = request.form.get('student_name')
        driver_name = request.form.get('driver_name', 'Bus Driver')
        location = request.form.get('location')
        distance_left = request.form.get('distance_left')
        time_required = request.form.get('time_required')
        custom_message = request.form.get('custom_message')
        
        print(f"DEBUG: Form data - Phone: {parent_phone}, Student: {student_name}, Driver: {driver_name}")
        
        # Send WhatsApp message
        success, message = send_whatsapp_to_parent(
            parent_phone, student_name, driver_name, 
            location, distance_left, time_required, custom_message
        )
        
        print(f"DEBUG: WhatsApp result - Success: {success}, Message: {message}")
        
        return jsonify({
            'success': success,
            'message': message
        })
    
    print("DEBUG: GET request for parent notification form")
    # Get students with approved passes for dropdown
    conn = get_db_connection()
    students = conn.execute('''
        SELECT s.student_id, s.name, s.father_phone, b.pass_number, b.route
        FROM students s
        JOIN bus_passes b ON s.student_id = b.student_id
        WHERE b.status = 'approved'
    ''').fetchall()
    conn.close()
    
    print(f"DEBUG: Found {len(students)} students with approved passes")
    return render_template('driver_send_notification.html', students=students)

# Initialize database on first run
def init_database():
    if not os.path.exists('transit_system.db'):
        conn = get_db_connection()
        
        # Create tables
        conn.execute('''
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                father_name TEXT,
                father_phone TEXT,
                father_email TEXT,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE bus_passes (
                pass_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                pass_number TEXT UNIQUE NOT NULL,
                route TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (student_id)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE attendance (
                attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                pass_id INTEGER,
                date TEXT NOT NULL,
                boarding_time TEXT,
                verification_type TEXT,
                status TEXT DEFAULT 'present',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (student_id),
                FOREIGN KEY (pass_id) REFERENCES bus_passes (pass_id)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE bus_locations (
                location_id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id INTEGER,
                current_location TEXT,
                destination TEXT,
                distance_left TEXT,
                time_required TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (driver_id) REFERENCES users (user_id)
            )
        ''')
        
        # Insert default users
        conn.execute('''
            INSERT INTO users (username, password, role) VALUES 
            ('admin', ?, 'admin'),
            ('driver', ?, 'driver'),
            ('student', ?, 'student')
        ''', (
            generate_password_hash('admin123'),
            generate_password_hash('driver123'),
            generate_password_hash('student123')
        ))
        
        # Insert sample students
        conn.execute('''
            INSERT INTO students (user_id, name, email, phone, father_name, father_phone, father_email, address) VALUES 
            (3, 'sai', 'sai@example.com', '1234567890', 'Father Name', '7893277617', 'father@example.com', '123 Main St')
        ''')
        
        # Insert sample bus pass
        conn.execute('''
            INSERT INTO bus_passes (student_id, pass_number, route, status) VALUES 
            (1, 'BP001', 'Route A', 'approved')
        ''')
        
        conn.commit()
        conn.close()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

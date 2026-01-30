from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import cv2
import numpy as np
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
app = Flask(__name__)
app.secret_key = 'smart_campus_transit_2024'

# Configuration
UPLOAD_FOLDER = 'static/uploads'
KNOWN_FACES_FOLDER = 'static/known_faces'
PASS_PHOTOS_FOLDER = 'static/pass_photos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# WhatsApp Configuration - TextMeBot
WHATSAPP_CONFIG = {
    'api_url': 'https://api.textmebot.com/whatsapp.php',
    'phone_number': '+917893277617',  # Your WhatsApp number
    'api_key': '8TTpz87ybvbb'  # Your TextMeBot API key
}

# Create directories
for folder in [UPLOAD_FOLDER, KNOWN_FACES_FOLDER, PASS_PHOTOS_FOLDER, 'static/temp']:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['KNOWN_FACES_FOLDER'] = KNOWN_FACES_FOLDER
app.config['PASS_PHOTOS_FOLDER'] = PASS_PHOTOS_FOLDER

# Initialize face cascade
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Database initialization
def init_db():
    conn = sqlite3.connect('transit_system.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            roll_number TEXT UNIQUE,
            department TEXT,
            year TEXT,
            phone_number TEXT,
            father_name TEXT,
            father_phone TEXT,
            address TEXT,
            face_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bus_passes (
            pass_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            pass_number TEXT UNIQUE NOT NULL,
            issue_date DATE,
            expiry_date DATE,
            route TEXT,
            status TEXT DEFAULT 'pending',
            photo_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (student_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            pass_id INTEGER,
            date DATE,
            boarding_time TIME,
            drop_time TIME,
            verification_type TEXT,
            status TEXT DEFAULT 'present',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (student_id),
            FOREIGN KEY (pass_id) REFERENCES bus_passes (pass_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bus_locations (
            location_id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER,
            current_location TEXT,
            destination TEXT,
            distance_left TEXT,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS routes (
            route_id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_name TEXT UNIQUE NOT NULL,
            start_point TEXT,
            end_point TEXT,
            stops TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default admin if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                      ('admin', 'admin123', 'admin'))
    
    # Insert default routes
    cursor.execute("SELECT * FROM routes")
    if not cursor.fetchone():
        routes = [
            ('Route 1', 'College Gate', 'Main Campus', 'Stop1,Stop2,Stop3'),
            ('Route 2', 'City Center', 'College', 'StopA,StopB,StopC'),
            ('Route 3', 'Railway Station', 'College', 'Station1,Station2')
        ]
        cursor.executemany("INSERT INTO routes (route_name, start_point, end_point, stops) VALUES (?, ?, ?, ?)", routes)
    
    conn.commit()
    conn.close()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

class FaceRecognitionSystem:
    def __init__(self):
        self.known_faces = {}
        self.load_known_faces()
    
    def enhance_image(self, image):
        """Enhance image brightness and contrast"""
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        enhanced = cv2.convertScaleAbs(enhanced, alpha=1.2, beta=20)
        return enhanced
    
    def capture_from_webcam(self, save_path=None):
        """Capture image from webcam without display"""
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            return None, "Cannot access camera. Make sure camera is connected and not in use."
        
        try:
            cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.6)
            cap.set(cv2.CAP_PROP_CONTRAST, 0.7)
            cap.set(cv2.CAP_PROP_SATURATION, 0.8)
            
            for _ in range(5):
                ret, frame = cap.read()
                if not ret:
                    continue
            
            ret, frame = cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                enhanced_frame = self.enhance_image(frame)
                
                if save_path:
                    cv2.imwrite(save_path, enhanced_frame)
                
                cap.release()
                return enhanced_frame, None
            else:
                cap.release()
                return None, "Failed to capture image from camera"
        except Exception as e:
            cap.release()
            return None, f"Camera error: {str(e)}"
    
    def detect_faces(self, image):
        """Detect faces in image"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        return faces
    
    def extract_face_encoding(self, image_path):
        """Extract face features from image using histogram comparison"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return None
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                return None
            
            (x, y, w, h) = faces[0]
            face_region = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face_region, (100, 100))
            
            hist = cv2.calcHist([face_resized], [0], None, [256], [0, 256])
            cv2.normalize(hist, hist)
            
            return hist.flatten()
        except Exception as e:
            print(f"Error extracting encoding: {e}")
            return None
    
    def save_known_face(self, student_id, image_path):
        """Save known face with student ID"""
        encoding = self.extract_face_encoding(image_path)
        if encoding is not None:
            self.known_faces[str(student_id)] = encoding.tolist()
            self.save_known_faces()
            return True
        return False
    
    def recognize_student(self, image_path, tolerance=0.6):
        """Recognize student from image using histogram correlation"""
        print(f"DEBUG: Starting face recognition for {image_path}")
        
        unknown_encoding = self.extract_face_encoding(image_path)
        if unknown_encoding is None:
            print("DEBUG: No face detected in image")
            return None, "No face detected"
        
        print(f"DEBUG: Face encoding extracted, shape: {unknown_encoding.shape}")
        
        if not self.known_faces:
            print("DEBUG: No known faces in database")
            return None, "No registered students in database"
        
        print(f"DEBUG: Found {len(self.known_faces)} known faces: {list(self.known_faces.keys())}")
        
        best_match = None
        best_score = -1
        
        for key, encoding in self.known_faces.items():
            encoding = np.array(encoding)
            
            try:
                unknown_encoding_reshaped = unknown_encoding.reshape(256, 1).astype(np.float32)
                encoding_reshaped = encoding.reshape(256, 1).astype(np.float32)
                
                correlation = cv2.compareHist(encoding_reshaped, unknown_encoding_reshaped, cv2.HISTCMP_CORREL)
                
                correlation_score = float(correlation)
                print(f"DEBUG: Comparing with '{key}': score = {correlation_score:.4f}")
                
                if correlation_score > best_score:
                    best_score = correlation_score
                    best_match = key
                    
            except Exception as e:
                print(f"DEBUG: Error comparing with '{key}': {e}")
                continue
        
        print(f"DEBUG: Best match: '{best_match}' with score: {best_score:.4f}")
        print(f"DEBUG: Tolerance: {tolerance}")
        
        if best_score >= tolerance:
            # Check if the match is a student ID or name
            if best_match.isdigit():
                # It's a student ID
                print(f"DEBUG: Match is student ID: {best_match}")
                return best_match, f"Student recognized (similarity: {best_score:.4f})"
            else:
                # It's a name, try to find the student by name
                print(f"DEBUG: Match is name: '{best_match}', looking up student...")
                student = self.get_student_by_name(best_match)
                if student:
                    print(f"DEBUG: Student found: ID={student['student_id']}, Name={student['name']}")
                    return str(student['student_id']), f"Student recognized (similarity: {best_score:.4f})"
                else:
                    print(f"DEBUG: Student '{best_match}' not found in database")
                    return None, f"Face recognized but student '{best_match}' not found in database"
        else:
            print(f"DEBUG: Score {best_score:.4f} below tolerance {tolerance}")
            return None, f"Unknown student (best similarity: {best_score:.4f})"
    
    def get_student_by_name(self, name):
        """Get student by name from database"""
        try:
            conn = get_db_connection()
            student = conn.execute('SELECT * FROM students WHERE name = ?', (name,)).fetchone()
            conn.close()
            return student
        except Exception as e:
            print(f"Error finding student by name: {e}")
            return None
    
    def load_known_faces(self):
        """Load known faces from file"""
        try:
            if os.path.exists('known_faces.json'):
                with open('known_faces.json', 'r') as f:
                    self.known_faces = json.load(f)
        except Exception as e:
            print(f"Error loading known faces: {e}")
            self.known_faces = {}
    
    def save_known_faces(self):
        """Save known faces to file"""
        try:
            with open('known_faces.json', 'w') as f:
                json.dump(self.known_faces, f)
        except Exception as e:
            print(f"Error saving known faces: {e}")

# Initialize face recognition system
face_system = FaceRecognitionSystem()

# Database helper functions
def send_whatsapp_to_parent(parent_phone, student_name, driver_name, location, distance_left, time_required, custom_message):
    """Send WhatsApp notification to parent using CallMeBot API"""
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
        print(f"DEBUG: Message: {message[:100]}...")  # Show first 100 chars
        
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

def get_db_connection():
    conn = sqlite3.connect('transit_system.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_student_by_user_id(user_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return student

def get_student_by_id(student_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE student_id = ?', (student_id,)).fetchone()
    conn.close()
    return student

def get_bus_pass_by_student_id(student_id):
    conn = get_db_connection()
    pass_info = conn.execute('SELECT * FROM bus_passes WHERE student_id = ? ORDER BY created_at DESC LIMIT 1', 
                           (student_id,)).fetchone()
    conn.close()
    return pass_info

# Routes
@app.route('/')
def index():
    return render_template('transit_index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                          (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('driver_dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = 'student'
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', 
                          (username, password, role))
            user_id = cursor.lastrowid
            conn.commit()
            
            # Create student record
            cursor.execute('''
                INSERT INTO students (user_id, name, roll_number, department, year, phone_number, 
                                    father_name, father_phone, address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, request.form['name'], request.form['roll_number'], 
                  request.form['department'], request.form['year'], request.form['phone_number'],
                  request.form['father_name'], request.form['father_phone'], request.form['address']))
            conn.commit()
            conn.close()
            
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or roll number already exists')
            conn.close()
    
    return render_template('student_register.html')

@app.route('/student/attendance_history')
@login_required
def student_attendance_history():
    if session['role'] != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    student = get_student_by_user_id(session['user_id'])
    if not student:
        return jsonify({'success': False, 'error': 'Student not found'})
    
    conn = get_db_connection()
    attendance_records = conn.execute('''
        SELECT a.date, a.boarding_time, a.verification_type, a.status, b.pass_number, b.route
        FROM attendance a
        JOIN bus_passes b ON a.pass_id = b.pass_id
        WHERE a.student_id = ?
        ORDER BY a.date DESC, a.boarding_time DESC
        LIMIT 30
    ''', (student['student_id'],)).fetchall()
    conn.close()
    
    attendance_list = []
    for record in attendance_records:
        attendance_list.append({
            'date': record['date'],
            'boarding_time': record['boarding_time'],
            'verification_type': record['verification_type'],
            'status': record['status'],
            'pass_number': record['pass_number'],
            'route': record['route']
        })
    
    return jsonify({
        'success': True,
        'attendance': attendance_list
    })

@app.route('/driver/update_location', methods=['GET', 'POST'])
@login_required
def driver_update_location():
    if session['role'] != 'driver':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        current_location = request.form.get('current_location')
        destination = request.form.get('destination')
        distance_left = request.form.get('distance_left')
        message = request.form.get('message')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert new location update
        cursor.execute('''
            INSERT INTO bus_locations (driver_id, current_location, destination, distance_left, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], current_location, destination, distance_left, message))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Location updated successfully'})
    
    return render_template('driver_update_location.html')

@app.route('/get_latest_location')
def get_latest_location():
    """API endpoint to get latest driver location for students"""
    conn = get_db_connection()
    latest_location = conn.execute('''
        SELECT current_location, destination, distance_left, message, timestamp
        FROM bus_locations
        ORDER BY timestamp DESC
        LIMIT 1
    ''').fetchone()
    conn.close()
    
    if latest_location:
        return jsonify({
            'success': True,
            'current_location': latest_location['current_location'],
            'destination': latest_location['destination'],
            'distance_left': latest_location['distance_left'],
            'message': latest_location['message'],
            'timestamp': latest_location['timestamp']
        })
    else:
        return jsonify({
            'success': False,
            'message': 'No location updates available'
        })

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

@app.route('/test_email_config')
def test_email_config():
    """Test email configuration and show current settings"""
    config_info = {
        'smtp_server': EMAIL_CONFIG['smtp_server'],
        'smtp_port': EMAIL_CONFIG['smtp_port'],
        'sender_email': EMAIL_CONFIG['sender_email'],
        'sender_password_set': bool(EMAIL_CONFIG['sender_password'] and EMAIL_CONFIG['sender_password'] != 'APP_PASSWORD'),
        'sender_name': EMAIL_CONFIG['sender_name']
    }
    
    return jsonify({
        'success': True,
        'config': config_info,
        'message': 'Check if sender_email is your actual email and sender_password_set is True'
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if session['role'] != 'student':
        return redirect(url_for('index'))
    
    student = get_student_by_user_id(session['user_id'])
    bus_pass = get_bus_pass_by_student_id(student['student_id']) if student else None
    
    return render_template('student_dashboard.html', student=student, bus_pass=bus_pass)

@app.route('/apply_pass')
@login_required
def apply_pass():
    if session['role'] != 'student':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    routes = conn.execute('SELECT * FROM routes').fetchall()
    conn.close()
    
    return render_template('apply_pass.html', routes=routes)

@app.route('/capture_photo', methods=['POST'])
@login_required
def capture_photo():
    """Capture photo for bus pass application"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = os.path.join('static/temp', f'pass_photo_{timestamp}.jpg')
        
        frame, error = face_system.capture_from_webcam(temp_path)
        if error:
            return jsonify({'success': False, 'error': error})
        
        # Detect faces
        faces = face_system.detect_faces(frame)
        
        if len(faces) == 0:
            return jsonify({'success': False, 'error': 'No face detected'})
        
        # Draw rectangles around faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # Save image with face detection
        result_path = os.path.join('static/temp', f'pass_result_{timestamp}.jpg')
        cv2.imwrite(result_path, frame)
        
        # Convert to base64 for display
        with open(result_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode()
        
        # Clean up temp files
        if os.path.exists(result_path):
            os.remove(result_path)
        
        return jsonify({
            'success': True,
            'image': f'data:image/jpeg;base64,{img_data}',
            'temp_path': temp_path,
            'faces_detected': len(faces)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/submit_pass_application', methods=['POST'])
@login_required
def submit_pass_application():
    """Submit bus pass application"""
    try:
        student = get_student_by_user_id(session['user_id'])
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'})
        
        # Get form data
        route = request.form.get('route')
        duration_from = request.form.get('duration_from')
        duration_to = request.form.get('duration_to')
        temp_path = request.form.get('temp_path')
        
        if not all([route, duration_from, duration_to, temp_path]):
            return jsonify({'success': False, 'error': 'All fields are required'})
        
        if not os.path.exists(temp_path):
            return jsonify({'success': False, 'error': 'No photo captured'})
        
        # Save photo permanently
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_filename = f'student_{student["student_id"]}_{timestamp}.jpg'
        photo_path = os.path.join(app.config['PASS_PHOTOS_FOLDER'], photo_filename)
        
        import shutil
        shutil.copy2(temp_path, photo_path)
        
        # Generate pass number
        pass_number = f"PASS{datetime.now().strftime('%Y%m%d')}{student['student_id']:04d}"
        
        # Save bus pass application
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bus_passes (student_id, pass_number, issue_date, expiry_date, route, photo_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (student['student_id'], pass_number, duration_from, duration_to, route, photo_path, 'pending'))
        pass_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Save face for recognition
        face_system.save_known_face(str(student['student_id']), photo_path)
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return jsonify({
            'success': True,
            'message': 'Bus pass application submitted successfully!',
            'pass_number': pass_number
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/driver/dashboard')
@login_required
def driver_dashboard():
    if session['role'] != 'driver':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get statistics
    total_students = conn.execute('SELECT COUNT(*) as count FROM students').fetchone()['count']
    active_passes = conn.execute('SELECT COUNT(*) as count FROM bus_passes WHERE status = "approved"').fetchone()['count']
    today_attendance = conn.execute('SELECT COUNT(*) as count FROM attendance WHERE date = ?', 
                                  (datetime.now().date(),)).fetchone()['count']
    
    conn.close()
    
    return render_template('driver_dashboard.html', 
                         total_students=total_students,
                         active_passes=active_passes,
                         today_attendance=today_attendance)

@app.route('/driver/attendance')
@login_required
def driver_attendance():
    if session['role'] != 'driver':
        return redirect(url_for('index'))
    
    return render_template('driver_attendance.html')

@app.route('/capture_attendance', methods=['POST'])
@login_required
def capture_attendance():
    """Capture face for attendance marking"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = os.path.join('static/temp', f'attendance_{timestamp}.jpg')
        
        frame, error = face_system.capture_from_webcam(temp_path)
        if error:
            return jsonify({'success': False, 'error': error})
        
        # Detect faces
        faces = face_system.detect_faces(frame)
        
        if len(faces) == 0:
            return jsonify({'success': False, 'error': 'No face detected'})
        
        # Draw rectangles around faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # Save image with face detection
        result_path = os.path.join('static/temp', f'attendance_result_{timestamp}.jpg')
        cv2.imwrite(result_path, frame)
        
        # Try to recognize student
        recognized_student_id, message = face_system.recognize_student(temp_path)
        
        student_info = None
        attendance_marked = False
        
        if recognized_student_id:
            # Get student information
            student = get_student_by_id(recognized_student_id)
            if student:
                # Check if student has valid bus pass
                bus_pass = get_bus_pass_by_student_id(recognized_student_id)
                if bus_pass and bus_pass['status'] == 'approved':
                    # Mark attendance
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    # Check if already marked today
                    today = datetime.now().date()
                    existing = conn.execute('''
                        SELECT * FROM attendance 
                        WHERE student_id = ? AND date = ? AND boarding_time IS NOT NULL
                    ''', (recognized_student_id, today)).fetchone()
                    
                    if not existing:
                        cursor.execute('''
                            INSERT INTO attendance (student_id, pass_id, date, boarding_time, verification_type, status)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (recognized_student_id, bus_pass['pass_id'], today, 
                              datetime.now().strftime('%H:%M:%S'), 'face', 'present'))
                        conn.commit()
                        attendance_marked = True
                    
                    conn.close()
                    
                    student_info = {
                        'name': student['name'],
                        'roll_number': student['roll_number'],
                        'department': student['department'],
                        'pass_number': bus_pass['pass_number'],
                        'route': bus_pass['route']
                    }
        
        # Convert to base64 for display
        with open(result_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode()
        
        # Clean up temp files
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(result_path):
            os.remove(result_path)
        
        return jsonify({
            'success': True,
            'image': f'data:image/jpeg;base64,{img_data}',
            'student_info': student_info,
            'attendance_marked': attendance_marked,
            'message': message,
            'faces_detected': len(faces)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session['role'] != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get statistics
    total_students = conn.execute('SELECT COUNT(*) as count FROM students').fetchone()['count']
    pending_passes = conn.execute('SELECT COUNT(*) as count FROM bus_passes WHERE status = "pending"').fetchone()['count']
    approved_passes = conn.execute('SELECT COUNT(*) as count FROM bus_passes WHERE status = "approved"').fetchone()['count']
    today_attendance = conn.execute('SELECT COUNT(*) as count FROM attendance WHERE date = ?', 
                                  (datetime.now().date(),)).fetchone()['count']
    
    # Get recent applications
    recent_applications = conn.execute('''
        SELECT b.pass_id, s.name, s.roll_number, b.pass_number, b.status, b.created_at
        FROM bus_passes b
        JOIN students s ON b.student_id = s.student_id
        ORDER BY b.created_at DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         total_students=total_students,
                         pending_passes=pending_passes,
                         approved_passes=approved_passes,
                         today_attendance=today_attendance,
                         recent_applications=recent_applications)

@app.route('/admin/pass_applications')
@login_required
def admin_pass_applications():
    if session['role'] != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    applications = conn.execute('''
        SELECT b.*, s.name, s.roll_number, s.department, s.phone_number
        FROM bus_passes b
        JOIN students s ON b.student_id = s.student_id
        ORDER BY b.created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin_applications.html', applications=applications)

@app.route('/admin/approve_pass/<int:pass_id>', methods=['POST'])
@login_required
def approve_pass(pass_id):
    if session['role'] != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    conn = get_db_connection()
    conn.execute('UPDATE bus_passes SET status = ? WHERE pass_id = ?', ('approved', pass_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Bus pass approved successfully'})

@app.route('/admin/reject_pass/<int:pass_id>', methods=['POST'])
@login_required
def reject_pass(pass_id):
    if session['role'] != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'})
    
    conn = get_db_connection()
    conn.execute('UPDATE bus_passes SET status = ? WHERE pass_id = ?', ('rejected', pass_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Bus pass rejected'})

@app.route('/admin/attendance_report')
@login_required
def admin_attendance_report():
    if session['role'] != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    attendance = conn.execute('''
        SELECT a.date, a.boarding_time, s.name, s.roll_number, s.department, b.pass_number
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        JOIN bus_passes b ON a.pass_id = b.pass_id
        ORDER BY a.date DESC, a.boarding_time DESC
        LIMIT 100
    ''').fetchall()
    conn.close()
    
    return render_template('admin_attendance.html', attendance=attendance)

@app.route('/test_camera')
def test_camera():
    """Test camera functionality"""
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return jsonify({
                'success': False,
                'error': 'Camera not accessible. Check if camera is connected and not in use.'
            })
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            return jsonify({
                'success': True,
                'message': 'Camera is working properly',
                'resolution': f'{frame.shape[1]}x{frame.shape[0]}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Camera accessible but failed to capture image'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Camera test failed: {str(e)}'
        })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import cv2
import numpy as np
import os
import json
import time
from datetime import datetime
import base64
# import face_recognition  # Using OpenCV instead for better compatibility
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'face_recognition_secret_key'

# Configuration
UPLOAD_FOLDER = 'static/uploads'
KNOWN_FACES_FOLDER = 'static/known_faces'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(KNOWN_FACES_FOLDER, exist_ok=True)
os.makedirs('static/temp', exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['KNOWN_FACES_FOLDER'] = KNOWN_FACES_FOLDER

# Initialize face cascade
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

class FaceRecognitionSystem:
    def __init__(self):
        self.known_faces = {}
        self.load_known_faces()
    
    def enhance_image(self, image):
        """Enhance image brightness and contrast"""
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        
        # Merge channels and convert back
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # Additional brightness and contrast adjustment
        enhanced = cv2.convertScaleAbs(enhanced, alpha=1.2, beta=20)
        
        return enhanced
    
    def capture_from_webcam(self, save_path=None):
        """Capture image from webcam without display"""
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            return None, "Cannot access camera. Make sure camera is connected and not in use."
        
        try:
            # Set camera settings for better quality
            cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.6)
            cap.set(cv2.CAP_PROP_CONTRAST, 0.7)
            cap.set(cv2.CAP_PROP_SATURATION, 0.8)
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            
            # Capture a few frames to warm up
            for _ in range(5):
                ret, frame = cap.read()
                if not ret:
                    continue
            
            # Capture the actual frame
            ret, frame = cap.read()
            if ret:
                # Flip horizontally for mirror effect
                frame = cv2.flip(frame, 1)
                
                # Enhance the image
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
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                return None
            
            # Get the first face
            (x, y, w, h) = faces[0]
            face_region = gray[y:y+h, x:x+w]
            
            # Resize to standard size
            face_resized = cv2.resize(face_region, (100, 100))
            
            # Calculate histogram as feature
            hist = cv2.calcHist([face_resized], [0], None, [256], [0, 256])
            cv2.normalize(hist, hist)
            
            return hist.flatten()
        except Exception as e:
            print(f"Error extracting encoding: {e}")
            return None
    
    def save_known_face(self, name, image_path):
        """Save known face with name"""
        print(f"Debug: save_known_face called for '{name}' with image '{image_path}'")
        
        encoding = self.extract_face_encoding(image_path)
        if encoding is not None:
            print(f"Debug: Face encoding extracted successfully, shape: {encoding.shape}")
            self.known_faces[name] = encoding.tolist()
            print(f"Debug: Known faces count before save: {len(self.known_faces)}")
            self.save_known_faces()
            print(f"Debug: Face saved successfully for '{name}'")
            return True
        else:
            print(f"Debug: Failed to extract face encoding from '{image_path}'")
            return False
    
    def recognize_face(self, image_path, tolerance=0.6):
        """Recognize face from image using histogram correlation"""
        unknown_encoding = self.extract_face_encoding(image_path)
        if unknown_encoding is None:
            return None, "No face detected"
        
        if not self.known_faces:
            return None, "No known faces in database"
        
        # Compare with known faces using histogram correlation
        best_match = None
        best_score = -1
        
        print(f"Debug: Comparing with {len(self.known_faces)} known faces")
        
        for name, encoding in self.known_faces.items():
            encoding = np.array(encoding)
            
            try:
                # Ensure both arrays are properly shaped for comparison
                unknown_encoding_reshaped = unknown_encoding.reshape(256, 1).astype(np.float32)
                encoding_reshaped = encoding.reshape(256, 1).astype(np.float32)
                
                # Compare histograms using correlation
                correlation = cv2.compareHist(encoding_reshaped, unknown_encoding_reshaped, cv2.HISTCMP_CORREL)
                
                # correlation is a scalar value, not an array
                print(f"Debug: {name} correlation = {correlation}")
                
                # Use float() to ensure we're comparing scalars
                correlation_score = float(correlation)
                if correlation_score > best_score:
                    best_score = correlation_score
                    best_match = name
                    
            except Exception as e:
                print(f"Debug: Error comparing with {name}: {e}")
                continue
        
        # Use correlation as similarity score (higher is better)
        # Ensure best_score is a scalar for comparison
        best_score = float(best_score) if best_score > -1 else -1
        
        if best_score >= tolerance:
            return best_match, f"Face recognized as {best_match} (similarity: {best_score:.4f})"
        else:
            return None, f"Unknown face (best similarity: {best_score:.4f})"
    
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
    
    def get_all_known_faces(self):
        """Get list of all known faces"""
        return list(self.known_faces.keys())

# Initialize face recognition system
face_system = FaceRecognitionSystem()

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/register')
def register():
    """Registration page"""
    return render_template('register.html')

@app.route('/recognize')
def recognize():
    """Recognition page"""
    return render_template('recognize.html', known_faces=face_system.get_all_known_faces())

@app.route('/capture_register', methods=['POST'])
def capture_register():
    """Capture face for registration"""
    try:
        # Capture image from webcam
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = os.path.join('static/temp', f'temp_{timestamp}.jpg')
        
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
        result_path = os.path.join('static/temp', f'result_{timestamp}.jpg')
        cv2.imwrite(result_path, frame)
        
        # Convert to base64 for display
        with open(result_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode()
        
        return jsonify({
            'success': True,
            'image': f'data:image/jpeg;base64,{img_data}',
            'temp_path': temp_path,
            'faces_detected': len(faces)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/save_face', methods=['POST'])
def save_face():
    """Save face with name"""
    try:
        name = request.form.get('name', '').strip()
        temp_path = request.form.get('temp_path', '')
        
        print(f"Debug: Saving face - Name: '{name}', Temp path: '{temp_path}'")
        
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'})
        
        if not temp_path or not os.path.exists(temp_path):
            print(f"Debug: Temp file check failed - Path: '{temp_path}', Exists: {os.path.exists(temp_path) if temp_path else 'No path'}")
            return jsonify({'success': False, 'error': 'No image captured'})
        
        # Save to known faces folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'{secure_filename(name)}_{timestamp}.jpg'
        known_face_path = os.path.join(app.config['KNOWN_FACES_FOLDER'], filename)
        
        print(f"Debug: Copying from '{temp_path}' to '{known_face_path}'")
        
        # Copy image
        import shutil
        shutil.copy2(temp_path, known_face_path)
        
        print(f"Debug: Image copied successfully")
        
        # Save face encoding
        print(f"Debug: Extracting face encoding...")
        if face_system.save_known_face(name, known_face_path):
            print(f"Debug: Face encoding saved successfully")
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"Debug: Temp file cleaned up")
            
            return jsonify({
                'success': True,
                'message': f'Face registered successfully for {name}',
                'name': name
            })
        else:
            print(f"Debug: Failed to extract face features")
            return jsonify({'success': False, 'error': 'Failed to extract face features'})
            
    except Exception as e:
        print(f"Debug: Exception in save_face: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Save error: {str(e)}'})

@app.route('/capture_recognize', methods=['POST'])
def capture_recognize():
    """Capture face for recognition"""
    try:
        print("Debug: Starting face recognition capture...")
        
        # Capture image from webcam
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = os.path.join('static/temp', f'recognition_{timestamp}.jpg')
        
        print(f"Debug: Capturing to temp path: {temp_path}")
        
        frame, error = face_system.capture_from_webcam(temp_path)
        if error:
            print(f"Debug: Camera capture error: {error}")
            return jsonify({'success': False, 'error': error})
        
        print("Debug: Camera capture successful")
        
        # Detect faces
        faces = face_system.detect_faces(frame)
        print(f"Debug: Found {len(faces)} faces in captured image")
        
        if len(faces) == 0:
            return jsonify({'success': False, 'error': 'No face detected'})
        
        # Draw rectangles around faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # Save image with face detection
        result_path = os.path.join('static/temp', f'recognition_result_{timestamp}.jpg')
        cv2.imwrite(result_path, frame)
        print(f"Debug: Saved result image to: {result_path}")
        
        # Try to recognize face
        print("Debug: Starting face recognition...")
        recognized_name, message = face_system.recognize_face(temp_path)
        print(f"Debug: Recognition result - Name: '{recognized_name}', Message: '{message}'")
        
        # Convert to base64 for display
        with open(result_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode()
        
        # Clean up temp files
        if os.path.exists(temp_path):
            os.remove(temp_path)
            print("Debug: Cleaned up temp capture file")
        if os.path.exists(result_path):
            os.remove(result_path)
            print("Debug: Cleaned up result file")
        
        return jsonify({
            'success': True,
            'image': f'data:image/jpeg;base64,{img_data}',
            'recognized_name': recognized_name,
            'message': message,
            'faces_detected': len(faces)
        })
        
    except Exception as e:
        print(f"Debug: Exception in capture_recognize: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_face', methods=['POST'])
def delete_face():
    """Delete known face"""
    try:
        name = request.form.get('name', '').strip()
        
        if name in face_system.known_faces:
            del face_system.known_faces[name]
            face_system.save_known_faces()
            return jsonify({'success': True, 'message': f'Face for {name} deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Face not found'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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
        
        # Try to capture a test frame
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

@app.route('/api/known_faces')
def api_known_faces():
    """API endpoint to get known faces"""
    return jsonify({'faces': face_system.get_all_known_faces()})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

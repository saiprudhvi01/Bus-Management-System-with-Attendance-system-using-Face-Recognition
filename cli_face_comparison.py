import cv2
import numpy as np
import os
from datetime import datetime

class CLIFaceComparison:
    def __init__(self):
        self.reference_face_path = "reference_face.jpg"
        self.detection_face_path = "detection_face.jpg"
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
    def capture_reference_face(self):
        """Capture your reference face from webcam"""
        print("Capturing reference face...")
        print("Press SPACE to capture, ESC to exit")
        print("(Camera window will open - look at the camera)")
        
        cap = cv2.VideoCapture(0)
        face_detected = False
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture from camera")
                break
                
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Detect faces
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            # Draw rectangle around faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Display instructions
            cv2.putText(frame, "Press SPACE to capture", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if len(faces) > 0:
                cv2.putText(frame, f"Face detected: {len(faces)}", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                face_detected = True
            else:
                cv2.putText(frame, "No face detected", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                face_detected = False
            
            try:
                cv2.imshow('Capture Reference Face', frame)
            except:
                print("Cannot display camera feed. Capturing blind...")
                break
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' ') and face_detected:  # Space key to capture
                # Save the captured image
                cv2.imwrite(self.reference_face_path, frame)
                print(f"✅ Reference face saved as {self.reference_face_path}")
                break
                
            elif key == 27:  # ESC key
                print("❌ Capture cancelled")
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        # If display failed, try blind capture
        if not os.path.exists(self.reference_face_path):
            print("Trying blind capture method...")
            self.blind_capture(self.reference_face_path, "reference")
    
    def capture_detection_face(self):
        """Capture face for detection/comparison"""
        print("\nCapturing detection face...")
        print("Press SPACE to capture, ESC to exit")
        print("(Camera window will open - look at the camera)")
        
        cap = cv2.VideoCapture(0)
        face_detected = False
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture from camera")
                break
                
            # Flip frame horizontally
            frame = cv2.flip(frame, 1)
            
            # Detect faces
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            # Draw rectangle around faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Display instructions
            cv2.putText(frame, "Press SPACE to capture", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if len(faces) > 0:
                cv2.putText(frame, f"Face detected: {len(faces)}", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                face_detected = True
            else:
                cv2.putText(frame, "No face detected", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                face_detected = False
            
            try:
                cv2.imshow('Capture Detection Face', frame)
            except:
                print("Cannot display camera feed. Capturing blind...")
                break
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' ') and face_detected:  # Space key to capture
                # Save the captured image
                cv2.imwrite(self.detection_face_path, frame)
                print(f"✅ Detection face saved as {self.detection_face_path}")
                break
                
            elif key == 27:  # ESC key
                print("❌ Capture cancelled")
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        # If display failed, try blind capture
        if not os.path.exists(self.detection_face_path):
            print("Trying blind capture method...")
            self.blind_capture(self.detection_face_path, "detection")
    
    def blind_capture(self, save_path, capture_type):
        """Capture without display"""
        print(f"Performing blind {capture_type} capture...")
        print("Look at the camera and press ENTER to capture...")
        
        cap = cv2.VideoCapture(0)
        
        # Capture a few frames to warm up
        for _ in range(5):
            ret, frame = cap.read()
            if not ret:
                continue
        
        # Capture the actual frame
        ret, frame = cap.read()
        if ret:
            # Flip horizontally
            frame = cv2.flip(frame, 1)
            
            # Save the image
            cv2.imwrite(save_path, frame)
            print(f"✅ {capture_type.capitalize()} face saved as {save_path}")
        else:
            print(f"❌ Failed to capture {capture_type} face")
        
        cap.release()
    
    def extract_face_features(self, image_path):
        """Extract basic face features using histogram comparison"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                print(f"Could not load image: {image_path}")
                return None
                
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                print(f"No face detected in {image_path}")
                return None
            
            print(f"Found {len(faces)} face(s) in {image_path}")
            
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
            print(f"Error extracting features from {image_path}: {e}")
            return None
    
    def compare_faces(self):
        """Compare faces using histogram correlation"""
        print("\n🔍 Comparing faces...")
        
        # Extract features from both images
        ref_features = self.extract_face_features(self.reference_face_path)
        det_features = self.extract_face_features(self.detection_face_path)
        
        if ref_features is None:
            print("❌ Could not extract features from reference image")
            return False
        
        if det_features is None:
            print("❌ Could not extract features from detection image")
            return False
        
        # Compare using correlation
        correlation = cv2.compareHist(ref_features.reshape(256, 1), 
                                     det_features.reshape(256, 1), 
                                     cv2.HISTCMP_CORREL)
        
        print(f"📊 Face similarity score: {correlation:.4f}")
        
        # Threshold for similarity (adjust as needed)
        threshold = 0.6
        match = correlation >= threshold
        
        print(f"🎯 Similarity threshold: {threshold}")
        
        if match:
            print("🎉✅ FACE RECOGNIZED - Same person detected!")
        else:
            print("🚫❌ FACE NOT RECOGNIZED - Different person detected!")
        
        return match
    
    def run_comparison(self):
        """Main function to run the complete face comparison process"""
        print("=" * 50)
        print("📸 CLI FACE COMPARISON SYSTEM")
        print("=" * 50)
        
        # Check camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Error: Cannot access camera")
            return
        cap.release()
        
        print("📷 Camera detected successfully!")
        print()
        
        # Step 1: Capture reference face
        print("📍 Step 1: Capture your reference face")
        self.capture_reference_face()
        
        if not os.path.exists(self.reference_face_path):
            print("❌ Failed to capture reference face. Exiting...")
            return
        
        # Step 2: Capture detection face
        print("\n📍 Step 2: Capture face for comparison")
        self.capture_detection_face()
        
        if not os.path.exists(self.detection_face_path):
            print("❌ Failed to capture detection face. Exiting...")
            return
        
        # Step 3: Compare faces
        print("\n📍 Step 3: Comparing faces...")
        result = self.compare_faces()
        
        # Summary
        print("\n" + "=" * 50)
        print("📋 SUMMARY")
        print("=" * 50)
        print(f"📁 Reference image: {self.reference_face_path}")
        print(f"📁 Detection image: {self.detection_face_path}")
        print(f"🎯 Result: {'MATCH' if result else 'NO MATCH'}")
        print("=" * 50)
        
        return result

def main():
    """Main function to run the face comparison system"""
    try:
        # Create face comparison system
        face_system = CLIFaceComparison()
        
        # Run the comparison process
        result = face_system.run_comparison()
        
        return result
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Program interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        # Clean up any open windows
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

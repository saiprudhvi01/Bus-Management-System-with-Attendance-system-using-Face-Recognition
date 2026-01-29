import cv2
import numpy as np
import os
import time
from datetime import datetime

class HeadlessFaceComparison:
    def __init__(self):
        self.reference_face_path = "reference_face.jpg"
        self.detection_face_path = "detection_face.jpg"
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
    def capture_face(self, image_path, capture_type):
        """Capture face without display"""
        print(f"\n📸 Capturing {capture_type} face...")
        print("👀 Look at the camera...")
        print("⏳ Capturing in 3 seconds...")
        
        # Countdown
        for i in range(3, 0, -1):
            print(f"⏰ {i}...")
            time.sleep(1)
        
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print(f"❌ Error: Cannot access camera")
            return False
        
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
            
            # Save the image
            cv2.imwrite(image_path, frame)
            print(f"✅ {capture_type.capitalize()} face saved as {image_path}")
            
            # Check if face was detected
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) > 0:
                print(f"👤 Face detected: {len(faces)} face(s) found")
                return True
            else:
                print("⚠️  No face detected in captured image")
                return False
        else:
            print(f"❌ Failed to capture {capture_type} face")
            return False
        
        cap.release()
    
    def extract_face_features(self, image_path):
        """Extract basic face features using histogram comparison"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Could not load image: {image_path}")
                return None
                
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                print(f"❌ No face detected in {image_path}")
                return None
            
            print(f"🔍 Found {len(faces)} face(s) in {image_path}")
            
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
            print(f"❌ Error extracting features from {image_path}: {e}")
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
        print("=" * 60)
        print("📸 HEADLESS FACE COMPARISON SYSTEM")
        print("=" * 60)
        
        # Check camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Error: Cannot access camera")
            print("💡 Make sure your camera is connected and not being used by another application")
            return False
        cap.release()
        
        print("📷 Camera detected successfully!")
        
        # Step 1: Capture reference face
        print("\n" + "="*60)
        print("📍 STEP 1: CAPTURE REFERENCE FACE")
        print("="*60)
        
        ref_success = self.capture_face(self.reference_face_path, "reference")
        
        if not ref_success:
            print("❌ Failed to capture reference face. Exiting...")
            return False
        
        # Step 2: Capture detection face
        print("\n" + "="*60)
        print("📍 STEP 2: CAPTURE DETECTION FACE")
        print("="*60)
        print("💡 Now capture the face you want to compare with the reference")
        
        det_success = self.capture_face(self.detection_face_path, "detection")
        
        if not det_success:
            print("❌ Failed to capture detection face. Exiting...")
            return False
        
        # Step 3: Compare faces
        print("\n" + "="*60)
        print("📍 STEP 3: COMPARING FACES")
        print("="*60)
        
        result = self.compare_faces()
        
        # Summary
        print("\n" + "="*60)
        print("📋 COMPARISON SUMMARY")
        print("="*60)
        print(f"📁 Reference image: {self.reference_face_path}")
        print(f"📁 Detection image: {self.detection_face_path}")
        print(f"🎯 Result: {'✅ MATCH' if result else '❌ NO MATCH'}")
        
        if result:
            print("🎉 The faces belong to the same person!")
        else:
            print("🚫 The faces belong to different people!")
        
        print("="*60)
        
        return result

def main():
    """Main function to run the face comparison system"""
    try:
        # Create face comparison system
        face_system = HeadlessFaceComparison()
        
        # Run the comparison process
        result = face_system.run_comparison()
        
        return result
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Program interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    main()

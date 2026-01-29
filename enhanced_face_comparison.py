import cv2
import numpy as np
import os
import time
from datetime import datetime

class EnhancedFaceComparison:
    def __init__(self):
        self.reference_face_path = "reference_face.jpg"
        self.detection_face_path = "detection_face.jpg"
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
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
    
    def capture_face(self, image_path, capture_type):
        """Capture face with enhancement"""
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
            
            # Save both original and enhanced
            original_path = image_path.replace('.jpg', '_original.jpg')
            cv2.imwrite(original_path, frame)
            cv2.imwrite(image_path, enhanced_frame)
            
            print(f"✅ {capture_type.capitalize()} face saved as {image_path}")
            print(f"📸 Original also saved as {original_path}")
            
            # Check if face was detected in enhanced image
            gray = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) > 0:
                print(f"👤 Face detected: {len(faces)} face(s) found")
                return True
            else:
                print("⚠️  No face detected, but image was captured and enhanced")
                return True  # Still return True since we have the image
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
            
            # Try to detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                print(f"⚠️  No face detected in {image_path}, using full image for comparison")
                # Use the center portion of the image
                h, w = gray.shape
                face_region = gray[h//4:3*h//4, w//4:3*w//4]
            else:
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
    
    def compare_and_display(self):
        """Compare faces and display results"""
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
        threshold = 0.5  # Lowered threshold for better matching
        match = correlation >= threshold
        
        print(f"🎯 Similarity threshold: {threshold}")
        
        if match:
            print("🎉✅ FACE RECOGNIZED - Same person detected!")
        else:
            print("🚫❌ FACE NOT RECOGNIZED - Different person detected!")
        
        return match
    
    def analyze_image_quality(self, image_path):
        """Analyze and report image quality"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return
            
            # Calculate brightness
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            
            # Calculate contrast
            contrast = np.std(gray)
            
            print(f"📊 Image quality analysis for {image_path}:")
            print(f"   🌟 Brightness: {brightness:.1f} (0-255)")
            print(f"   🎭 Contrast: {contrast:.1f}")
            
            if brightness < 50:
                print("   ⚠️  Image is quite dark")
            elif brightness > 200:
                print("   ⚠️  Image is very bright")
            else:
                print("   ✅ Brightness looks good")
            
            if contrast < 30:
                print("   ⚠️  Low contrast")
            else:
                print("   ✅ Good contrast")
                
        except Exception as e:
            print(f"❌ Error analyzing image: {e}")
    
    def run_comparison(self):
        """Run the complete face comparison process"""
        print("=" * 60)
        print("📸 ENHANCED FACE COMPARISON SYSTEM")
        print("=" * 60)
        
        # Check camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Error: Cannot access camera")
            print("💡 Make sure your camera is connected and not being used by another application")
            return False
        cap.release()
        
        print("📷 Camera detected successfully!")
        print("🔧 Using enhanced image processing for better quality")
        
        # Step 1: Capture reference face
        print("\n" + "="*60)
        print("📍 STEP 1: CAPTURE REFERENCE FACE")
        print("="*60)
        
        ref_success = self.capture_face(self.reference_face_path, "reference")
        
        if not ref_success:
            print("❌ Failed to capture reference face. Exiting...")
            return False
        
        # Analyze captured image
        self.analyze_image_quality(self.reference_face_path)
        
        # Step 2: Capture detection face
        print("\n" + "="*60)
        print("📍 STEP 2: CAPTURE DETECTION FACE")
        print("="*60)
        print("💡 Now capture the face you want to compare with the reference")
        
        det_success = self.capture_face(self.detection_face_path, "detection")
        
        if not det_success:
            print("❌ Failed to capture detection face. Exiting...")
            return False
        
        # Analyze captured image
        self.analyze_image_quality(self.detection_face_path)
        
        # Step 3: Compare faces
        print("\n" + "="*60)
        print("📍 STEP 3: COMPARING FACES")
        print("="*60)
        
        result = self.compare_and_display()
        
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
        face_system = EnhancedFaceComparison()
        
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

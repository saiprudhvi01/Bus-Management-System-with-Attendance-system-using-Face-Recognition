import cv2
import numpy as np
import os
from datetime import datetime

class SimpleFaceComparison:
    def __init__(self):
        self.reference_face_path = "reference_face.jpg"
        self.detection_face_path = "detection_face.jpg"
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
    def capture_reference_face(self):
        """Capture your reference face from webcam"""
        print("Capturing reference face...")
        print("Press SPACE to capture, ESC to exit")
        
        cap = cv2.VideoCapture(0)
        
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
            else:
                cv2.putText(frame, "No face detected", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imshow('Capture Reference Face', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' ') and len(faces) > 0:  # Space key to capture
                # Save the captured image
                cv2.imwrite(self.reference_face_path, frame)
                print(f"Reference face saved as {self.reference_face_path}")
                break
                
            elif key == 27:  # ESC key
                print("Capture cancelled")
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
    def capture_detection_face(self):
        """Capture face for detection/comparison"""
        print("\nCapturing detection face...")
        print("Press SPACE to capture, ESC to exit")
        
        cap = cv2.VideoCapture(0)
        
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
            else:
                cv2.putText(frame, "No face detected", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imshow('Capture Detection Face', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' ') and len(faces) > 0:  # Space key to capture
                # Save the captured image
                cv2.imwrite(self.detection_face_path, frame)
                print(f"Detection face saved as {self.detection_face_path}")
                break
                
            elif key == 27:  # ESC key
                print("Capture cancelled")
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
    def extract_face_features(self, image_path):
        """Extract basic face features using histogram comparison"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return None
                
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
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
            print(f"Error extracting features: {e}")
            return None
    
    def compare_faces(self):
        """Compare faces using histogram correlation"""
        # Extract features from both images
        ref_features = self.extract_face_features(self.reference_face_path)
        det_features = self.extract_face_features(self.detection_face_path)
        
        if ref_features is None or det_features is None:
            print("Could not extract features from one or both images")
            return False
        
        # Compare using correlation
        correlation = cv2.compareHist(ref_features.reshape(256, 1), 
                                     det_features.reshape(256, 1), 
                                     cv2.HISTCMP_CORREL)
        
        print(f"Face similarity score: {correlation:.4f}")
        
        # Threshold for similarity (adjust as needed)
        threshold = 0.6
        match = correlation >= threshold
        
        if match:
            print("✅ FACE RECOGNIZED - Same person detected!")
        else:
            print("❌ FACE NOT RECOGNIZED - Different person detected!")
        
        return match
    
    def display_comparison_result(self, match):
        """Display both images side by side with result"""
        try:
            # Load images
            ref_img = cv2.imread(self.reference_face_path)
            det_img = cv2.imread(self.detection_face_path)
            
            if ref_img is None or det_img is None:
                print("Could not load images for display")
                return
            
            # Resize images to same height
            height = 300
            ref_img = cv2.resize(ref_img, (int(ref_img.shape[1] * height / ref_img.shape[0]), height))
            det_img = cv2.resize(det_img, (int(det_img.shape[1] * height / det_img.shape[0]), height))
            
            # Add labels
            cv2.putText(ref_img, "Reference Face", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(det_img, "Detection Face", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Add result
            result_text = "MATCH" if match else "NO MATCH"
            result_color = (0, 255, 0) if match else (0, 0, 255)
            cv2.putText(det_img, result_text, (10, det_img.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, result_color, 3)
            
            # Combine images side by side
            combined = np.hstack([ref_img, det_img])
            
            # Display result
            cv2.imshow('Face Comparison Result', combined)
            print("\nPress any key to close the result window...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
        except Exception as e:
            print(f"Error displaying result: {e}")
    
    def run_comparison(self):
        """Main function to run the complete face comparison process"""
        print("=== SIMPLE FACE COMPARISON SYSTEM ===")
        print("Step 1: Capture your reference face")
        
        # Capture reference face
        self.capture_reference_face()
        
        if not os.path.exists(self.reference_face_path):
            print("Failed to capture reference face. Exiting...")
            return
        
        print("\nStep 2: Capture face for comparison")
        
        # Capture detection face
        self.capture_detection_face()
        
        if not os.path.exists(self.detection_face_path):
            print("Failed to capture detection face. Exiting...")
            return
        
        print("\nStep 3: Comparing faces...")
        
        # Compare faces
        result = self.compare_faces()
        
        # Display results with images
        self.display_comparison_result(result)

def main():
    """Main function to run the face comparison system"""
    try:
        # Create face comparison system
        face_system = SimpleFaceComparison()
        
        # Run the comparison process
        face_system.run_comparison()
        
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        # Clean up any open windows
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

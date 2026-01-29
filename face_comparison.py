import cv2
import numpy as np
import face_recognition
import os
from datetime import datetime

class FaceComparisonSystem:
    def __init__(self):
        self.known_face_encoding = None
        self.reference_image_path = "reference_face.jpg"
        self.detection_image_path = "detection_face.jpg"
        
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
            
            # Display instructions
            cv2.putText(frame, "Press SPACE to capture", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow('Capture Reference Face', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):  # Space key to capture
                # Save the captured image
                cv2.imwrite(self.reference_image_path, frame)
                print(f"Reference face saved as {self.reference_image_path}")
                
                # Extract face encoding
                self.known_face_encoding = self.extract_face_encoding(self.reference_image_path)
                if self.known_face_encoding is not None:
                    print("Reference face captured and encoded successfully!")
                    break
                else:
                    print("No face detected in captured image. Please try again.")
                    
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
            
            # Display instructions
            cv2.putText(frame, "Press SPACE to capture", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow('Capture Detection Face', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):  # Space key to capture
                # Save the captured image
                cv2.imwrite(self.detection_image_path, frame)
                print(f"Detection face saved as {self.detection_image_path}")
                break
                
            elif key == 27:  # ESC key
                print("Capture cancelled")
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
    def extract_face_encoding(self, image_path):
        """Extract face encoding from image"""
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Find face locations and encodings
            face_locations = face_recognition.face_locations(image)
            
            if len(face_locations) == 0:
                print("No face detected in the image")
                return None
            elif len(face_locations) > 1:
                print("Multiple faces detected. Using the first one.")
            
            # Get face encoding for the first face
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if len(face_encodings) > 0:
                return face_encodings[0]
            else:
                print("Could not extract face encoding")
                return None
                
        except Exception as e:
            print(f"Error extracting face encoding: {e}")
            return None
    
    def compare_faces(self, tolerance=0.6):
        """Compare reference face with detection face"""
        if self.known_face_encoding is None:
            print("No reference face available. Please capture reference face first.")
            return False
        
        # Extract encoding from detection image
        unknown_face_encoding = self.extract_face_encoding(self.detection_image_path)
        
        if unknown_face_encoding is None:
            print("No face detected in detection image")
            return False
        
        # Compare faces
        distance = face_recognition.face_distance([self.known_face_encoding], unknown_face_encoding)[0]
        
        print(f"Face distance: {distance:.4f}")
        print(f"Tolerance: {tolerance}")
        
        # Determine if faces match
        match = distance <= tolerance
        
        if match:
            print("✅ FACE RECOGNIZED - Same person detected!")
        else:
            print("❌ FACE NOT RECOGNIZED - Different person detected!")
        
        return match
    
    def run_comparison(self):
        """Main function to run the complete face comparison process"""
        print("=== FACE COMPARISON SYSTEM ===")
        print("Step 1: Capture your reference face")
        
        # Capture reference face
        self.capture_reference_face()
        
        if self.known_face_encoding is None:
            print("Failed to capture reference face. Exiting...")
            return
        
        print("\nStep 2: Capture face for comparison")
        
        # Capture detection face
        self.capture_detection_face()
        
        if not os.path.exists(self.detection_image_path):
            print("Failed to capture detection face. Exiting...")
            return
        
        print("\nStep 3: Comparing faces...")
        
        # Compare faces
        result = self.compare_faces()
        
        # Display results with images
        self.display_comparison_result(result)
    
    def display_comparison_result(self, match):
        """Display both images side by side with result"""
        try:
            # Load images
            ref_img = cv2.imread(self.reference_image_path)
            det_img = cv2.imread(self.detection_image_path)
            
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

def main():
    """Main function to run the face comparison system"""
    try:
        # Create face comparison system
        face_system = FaceComparisonSystem()
        
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

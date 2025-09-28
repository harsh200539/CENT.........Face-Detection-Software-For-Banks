import cv2
import numpy as np
import pickle
import os
import imutils
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
from imutils import paths
import base64
import io
from PIL import Image

class FaceRecognition:
    def __init__(self):
        self.detector = None
        self.embedder = None
        self.recognizer = None
        self.le = None
        self.load_models()
    
    def load_models(self):
        """Load the face detection and recognition models"""
        try:
            # Get the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Load face detector
            self.detector = cv2.dnn.readNetFromCaffe(
                os.path.join(project_root, 'face_detection_model', 'deploy.prototxt'),
                os.path.join(project_root, 'face_detection_model', 'res10_300x300_ssd_iter_140000.caffemodel')
            )
            
            # Load face embedder
            self.embedder = cv2.dnn.readNetFromTorch(os.path.join(project_root, 'nn4.small2.v1.t7'))
            
            # Load trained models if they exist
            recognizer_path = os.path.join(project_root, 'output', 'recognizer.pickle')
            le_path = os.path.join(project_root, 'output', 'le.pickle')
            if os.path.exists(recognizer_path) and os.path.exists(le_path):
                self.recognizer = pickle.loads(open(recognizer_path, "rb").read())
                self.le = pickle.loads(open(le_path, "rb").read())
                print(f"[DEBUG] Loaded model with user IDs: {self.le.classes_}")
            else:
                print("[WARNING] No trained models found. Face recognition will not work until training is completed.")
            
            print("[INFO] Models loaded successfully")
        except Exception as e:
            print(f"[ERROR] Failed to load models: {e}")
    
    def detect_face(self, image):
        """Detect faces in an image"""
        try:
            # Resize image
            image = imutils.resize(image, width=600)
            (h, w) = image.shape[:2]
            
            # Create blob
            imageBlob = cv2.dnn.blobFromImage(
                cv2.resize(image, (300, 300)), 1.0, (300, 300),
                (104.0, 177.0, 123.0), swapRB=False, crop=False
            )
            
            # Detect faces
            self.detector.setInput(imageBlob)
            detections = self.detector.forward()
            
            faces = []
            for i in range(0, detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > 0.2:  # Even lower threshold for better detection
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")
                    
                    # Ensure coordinates are within image bounds
                    startX = max(0, startX)
                    startY = max(0, startY)
                    endX = min(w, endX)
                    endY = min(h, endY)
                    
                    face = image[startY:endY, startX:endX]
                    (fH, fW) = face.shape[:2]
                    
                    if fW >= 20 and fH >= 20:
                        faces.append({
                            'face': face,
                            'confidence': confidence,
                            'box': (startX, startY, endX, endY)
                        })
                        print(f"[DEBUG] Face detected with confidence: {confidence:.2f}, size: {fW}x{fH}")
            
            print(f"[DEBUG] Total faces detected: {len(faces)}")
            return faces
        except Exception as e:
            print(f"[ERROR] Face detection failed: {e}")
            return []
    
    def get_face_embedding(self, face):
        """Get face embedding for recognition"""
        try:
            faceBlob = cv2.dnn.blobFromImage(
                face, 1.0 / 255, (96, 96), (0, 0, 0), 
                swapRB=True, crop=False
            )
            self.embedder.setInput(faceBlob)
            vec = self.embedder.forward()
            return vec.flatten()
        except Exception as e:
            print(f"[ERROR] Face embedding failed: {e}")
            return None
    
    def recognize_face(self, image):
        """Recognize a face in the image"""
        try:
            if self.recognizer is None or self.le is None:
                print("[WARNING] Models not trained, attempting to load...")
                self.load_models()
                if self.recognizer is None or self.le is None:
                    return {'success': False, 'message': 'Models not available'}
            
            faces = self.detect_face(image)
            if not faces:
                return {'success': False, 'message': 'No face detected'}
            
            # Try all detected faces and pick the best match
            best_match = None
            best_confidence = 0
            
            # Print available classes for debugging
            print(f"[DEBUG] Available user IDs in model: {self.le.classes_}")
            
            for face_data in faces:
                face = face_data['face']
                embedding = self.get_face_embedding(face)
                
                if embedding is None:
                    continue
                
                # Predict
                preds = self.recognizer.predict_proba(embedding.reshape(1, -1))[0]
                j = np.argmax(preds)
                proba = preds[j]
                name = self.le.classes_[j]
                
                # Ensure we're using the correct user_id (stored as string in the model)
                user_id = int(name)
                print(f"[DEBUG] Face recognition attempt: User ID {user_id} with confidence {proba * 100:.2f}%")
                
                if proba > best_confidence:
                    best_confidence = proba
                    best_match = {
                        'user_id': user_id,
                        'confidence': proba * 100
                    }
            
            # Lower threshold for better recognition
            if best_match and best_confidence * 100 >= 15:  # Very low threshold for better recognition
                print(f"[DEBUG] Best match: User {best_match['user_id']} with confidence {best_match['confidence']:.2f}%")
                return {
                    'success': True,
                    'user_id': best_match['user_id'],
                    'confidence': best_match['confidence']
                }
            else:
                return {'success': False, 'message': f'Face not recognized - best confidence was {best_confidence * 100:.2f}%'}
            
        except Exception as e:
            print(f"[ERROR] Face recognition failed: {e}")
            return {'success': False, 'message': str(e)}
    
    def capture_and_train(self, user_id, images):
        """Capture face images and train the model"""
        try:
            # Get the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Create user directory
            user_dir = os.path.join(project_root, 'dataset', str(user_id))
            os.makedirs(user_dir, exist_ok=True)
            
            valid_images = 0
            
            # Save and validate images
            for i, image_data in enumerate(images):
                try:
                    # Decode base64 image
                    image_data = image_data.split(',')[1]  # Remove data:image/jpeg;base64, prefix
                    image_bytes = base64.b64decode(image_data)
                    image = Image.open(io.BytesIO(image_bytes))
                    image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                    
                    # Check if face is detected in the image
                    faces = self.detect_face(image)
                    if faces:
                        # Use the largest face
                        largest_face = max(faces, key=lambda x: x['face'].shape[0] * x['face'].shape[1])
                        face = largest_face['face']
                        
                        # Save the face image
                        cv2.imwrite(os.path.join(user_dir, f'{valid_images}.jpg'), face)
                        print(f"[DEBUG] Saved face image {valid_images} for user {user_id}")
                        valid_images += 1
                    else:
                        print(f"[WARNING] No face detected in image {i}")
                        
                except Exception as e:
                    print(f"[ERROR] Failed to process image {i}: {e}")
                    continue
            
            if valid_images < 3:
                print(f"[ERROR] Not enough valid face images captured: {valid_images}/5")
                return False
            
            print(f"[INFO] Successfully captured {valid_images} face images for user {user_id}")
            
            # Train model with new data
            self.train_model()
            return True
        except Exception as e:
            print(f"[ERROR] Face capture failed: {e}")
            return False
    
    def train_model(self):
        """Train the face recognition model"""
        try:
            print("[INFO] Loading face embeddings...")
            
            # Get the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Get all image paths
            dataset_path = os.path.join(project_root, 'dataset')
            imagePaths = list(paths.list_images(dataset_path))
            if not imagePaths:
                print("[ERROR] No images found for training")
                return False
            
            knownEmbeddings = []
            knownNames = []
            total = 0
            
            # Process each image
            for (i, imagePath) in enumerate(imagePaths):
                print(f"[INFO] Processing image {i + 1}/{len(imagePaths)}")
                
                # Extract person name from path - this is the user_id
                name = imagePath.split(os.path.sep)[-2]
                print(f"[DEBUG] Processing image for user_id: {name}")
                
                # Load and process image
                image = cv2.imread(imagePath)
                image = imutils.resize(image, width=600)
                (h, w) = image.shape[:2]
                
                # Create blob
                imageBlob = cv2.dnn.blobFromImage(
                    cv2.resize(image, (300, 300)), 1.0, (300, 300),
                    (104.0, 177.0, 123.0), swapRB=False, crop=False
                )
                
                # Detect faces
                self.detector.setInput(imageBlob)
                detections = self.detector.forward()
                
                if len(detections) > 0:
                    # Get the face with highest confidence
                    i = np.argmax(detections[0, 0, :, 2])
                    confidence = detections[0, 0, i, 2]
                    
                    if confidence > 0.5:
                        # Get face coordinates
                        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                        (startX, startY, endX, endY) = box.astype("int")
                        
                        # Extract face
                        face = image[startY:endY, startX:endX]
                        (fH, fW) = face.shape[:2]
                        
                        if fW >= 20 and fH >= 20:
                            # Get embedding
                            faceBlob = cv2.dnn.blobFromImage(
                                face, 1.0 / 255, (96, 96), (0, 0, 0),
                                swapRB=True, crop=False
                            )
                            self.embedder.setInput(faceBlob)
                            vec = self.embedder.forward()
                            
                            # Store the actual user_id as the name
                            knownNames.append(name)
                            knownEmbeddings.append(vec.flatten())
                            total += 1
            
            if total == 0:
                print("[ERROR] No valid faces found for training")
                return False
            
            # Train the model
            print(f"[INFO] Training model with {total} faces...")
            le = LabelEncoder()
            labels = le.fit_transform(knownNames)
            
            recognizer = SVC(C=1.0, kernel="linear", probability=True)
            recognizer.fit(knownEmbeddings, labels)
            
            # Save models
            output_dir = os.path.join(project_root, 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            with open(os.path.join(output_dir, 'recognizer.pickle'), "wb") as f:
                f.write(pickle.dumps(recognizer))
            
            with open(os.path.join(output_dir, 'le.pickle'), "wb") as f:
                f.write(pickle.dumps(le))
            
            # Update instance variables
            self.recognizer = recognizer
            self.le = le
            
            print("[INFO] Model training completed successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Model training failed: {e}")
            return False

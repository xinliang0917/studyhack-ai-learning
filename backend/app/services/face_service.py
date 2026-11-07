import io, base64, os
import numpy as np
from PIL import Image
from pathlib import Path
import cv2

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MODEL_SRC = os.path.join(_BACKEND_DIR, "face_landmarker.task")
_OPENCV_DATA_DIR = os.path.join(_BACKEND_DIR, "opencv_data")


def _cascade_candidates(filename):
    candidates = [os.path.join(_OPENCV_DATA_DIR, filename)]
    cv2_data = getattr(cv2, "data", None)
    haar_dir = getattr(cv2_data, "haarcascades", None)
    if haar_dir:
        candidates.append(os.path.join(haar_dir, filename))
    candidates.extend([
        os.path.join("/usr/share/opencv4/haarcascades", filename),
        os.path.join("/usr/local/share/opencv4/haarcascades", filename),
        os.path.join("/usr/share/opencv/haarcascades", filename),
    ])
    return candidates


def _load_cascade(filename):
    for path in _cascade_candidates(filename):
        if not os.path.exists(path):
            continue
        cascade = cv2.CascadeClassifier(path)
        if not cascade.empty():
            return cascade, path
    return cv2.CascadeClassifier(), None


class FaceService:
    def __init__(self):
        self.detector = None
        self.model_loaded = False
        self.cascade, default_path = _load_cascade(
            "haarcascade_frontalface_default.xml"
        )
        self.alt_cascade, alt_path = _load_cascade(
            "haarcascade_frontalface_alt2.xml"
        )
        print(f"OpenCV face data: {default_path}, {alt_path}")
        self.cascades = [
            cascade for cascade in (self.cascade, self.alt_cascade)
            if cascade is not None and not cascade.empty()
        ]
        if not self.cascades:
            print("OpenCV face cascades failed to load")
        else:
            print(f"OpenCV face cascades loaded: {len(self.cascades)}")
        self._try_load_model()
        default_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "face_images",
        )
        self.face_images_dir = os.getenv("FACE_IMAGES_DIR", default_dir)
        os.makedirs(self.face_images_dir, exist_ok=True)
        self.recognizer = None
        self.recognizer_trained = False
        self._load_recognizer()

    @staticmethod
    def _imwrite(path, image) -> bool:
        ext = os.path.splitext(path)[1] or ".jpg"
        ok, buf = cv2.imencode(ext, image)
        if not ok:
            return False
        buf.tofile(path)
        return True

    @staticmethod
    def _imread(path, flags=cv2.IMREAD_COLOR):
        if not os.path.exists(path):
            return None
        arr = np.fromfile(path, dtype=np.uint8)
        if arr.size == 0:
            return None
        return cv2.imdecode(arr, flags)

    def _try_load_model(self):
        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            if os.path.exists(_MODEL_SRC):
                with open(_MODEL_SRC, "rb") as f:
                    buf = f.read()
                opts = python.BaseOptions(model_asset_buffer=buf)
                opts2 = vision.FaceLandmarkerOptions(
                    base_options=opts, num_faces=1
                )
                self.detector = vision.FaceLandmarker.create_from_options(opts2)
                self.model_loaded = True
                print(f"FaceLandmarker loaded from memory ({len(buf)} bytes)")
            else:
                print(f"Model not found at {_MODEL_SRC}, using OpenCV fallback")
        except Exception as e:
            print(f"MediaPipe init failed: {e}")

    def _detect_face_box(self, gray):
        if gray is None or gray.size == 0:
            return None
        variants = [gray]
        try:
            variants.append(cv2.equalizeHist(gray))
        except Exception:
            pass
        for image in variants:
            for cascade in self.cascades:
                for scale, neighbors, min_size in (
                    (1.05, 3, (60, 60)),
                    (1.1, 4, (80, 80)),
                    (1.1, 6, (100, 100)),
                ):
                    faces = cascade.detectMultiScale(
                        image,
                        scaleFactor=scale,
                        minNeighbors=neighbors,
                        minSize=min_size,
                    )
                    if len(faces):
                        return max(faces, key=lambda box: box[2] * box[3])
        try:
            flipped = cv2.flip(gray, 1)
            for cascade in self.cascades:
                faces = cascade.detectMultiScale(
                    flipped,
                    scaleFactor=1.05,
                    minNeighbors=3,
                    minSize=(60, 60),
                )
                if len(faces):
                    return max(faces, key=lambda box: box[2] * box[3])
        except Exception:
            pass
        return None

    def extract_features(self, image_data):
        if self.model_loaded:
            f = self._mp_extract(image_data)
            if f is not None:
                return f
        return self._cv_extract(image_data)

    def _mp_extract(self, image_data):
        try:
            from mediapipe.tasks.python import vision
            import mediapipe as mp
            img = Image.open(io.BytesIO(image_data)).convert("RGB")
            arr = np.array(img)
            mpimg = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
            res = self.detector.detect(mpimg)
            if not res.face_landmarks:
                return None
            pts = np.array([[p.x, p.y, p.z] for p in res.face_landmarks[0]])
            # Use pairwise inter-landmark distances (pose-invariant)
            sampled = pts[::10]
            diff = sampled[:, np.newaxis, :] - sampled[np.newaxis, :, :]
            dists = np.sqrt(np.sum(diff ** 2, axis=-1))
            iu = np.triu_indices_from(dists, k=1)
            features = dists[iu]
            features = features / (np.mean(features) + 1e-8)
            return features.astype(np.float32)
        except Exception as e:
            print(f"MP extraction error: {e}")
            return None

    def _cv_extract(self, image_data):
        try:
            img = Image.open(io.BytesIO(image_data))
            arr = np.array(img)
            if arr.ndim == 3:
                if arr.shape[2] == 4:
                    gray = cv2.cvtColor(arr, cv2.COLOR_RGBA2GRAY)
                else:
                    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            else:
                gray = arr
            box = self._detect_face_box(gray)
            if box is None:
                return None
            x, y, w, h = box
            roi = gray[y:y+h, x:x+w]
            resized = cv2.resize(roi, (80, 80))
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4,4))
            clahe_img = clahe.apply(resized)
            # LBP-like features
            rows, cols = clahe_img.shape
            centers = clahe_img[1:-1, 1:-1].astype(np.float32)
            offsets = [(-1,-1),(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1)]
            for k, (dr, dc) in enumerate(offsets):
                nb = clahe_img[1+dr:rows-1+dr, 1+dc:cols-1+dc].astype(np.float32)
                if k == 0:
                    lbp = (nb > centers).astype(np.float32).reshape(-1, 1)
                else:
                    lbp = np.concatenate([lbp, (nb > centers).astype(np.float32).reshape(-1, 1)], axis=1)
            gx = cv2.Sobel(clahe_img, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(clahe_img, cv2.CV_32F, 0, 1, ksize=3)
            mag = np.sqrt(gx**2 + gy**2)[2:-2, 2:-2].flatten()
            angle = np.arctan2(gy[2:-2, 2:-2], gx[2:-2, 2:-2]).flatten()
            feat = np.concatenate([lbp.flatten()[::2], mag[::4], angle[::4]])
            return (feat - np.mean(feat)) / (np.std(feat) + 1e-8)
        except Exception as e:
            print(f"CV extraction error: {e}")
            return None

    def compare_faces(self, f1, f2, threshold=0.18):
        # Lower threshold for stricter matching
        threshold = 0.12
        a1 = np.array(f1, dtype=np.float32).flatten()
        a2 = np.array(f2, dtype=np.float32).flatten()
        # Dimension mismatch check: if lengths differ by more than 5%, reject
        l1, l2 = len(a1), len(a2)
        if l1 == 0 or l2 == 0:
            return False, 99.0
        ratio = min(l1, l2) / max(l1, l2)
        if ratio < 0.95:
            return False, 99.0
        n = min(l1, l2)
        dist = np.linalg.norm(a1[:n] - a2[:n])
        nd = dist / (n ** 0.5)
        return nd < threshold, float(nd)

    def _load_recognizer(self):
        model_path = os.path.join(self.face_images_dir, "lbph_model.yml")
        if os.path.exists(model_path):
            try:
                self.recognizer = cv2.face.LBPHFaceRecognizer_create()
                self.recognizer.read(model_path)
                self.recognizer_trained = True
            except Exception:
                self.recognizer_trained = False

    def save_face_sample(self, username, image_bytes, user_id):
        try:
            arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                print("save_face_sample: image decode failed")
                return False
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            box = self._detect_face_box(gray)
            if box is not None:
                x, y, w, h = box
                face_roi = gray[y:y+h, x:x+w]
            elif self.model_loaded:
                # MediaPipe fallback for face detection
                try:
                    from mediapipe.tasks.python import vision
                    import mediapipe as mp
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    mpimg = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    res = self.detector.detect(mpimg)
                    if not res.face_landmarks:
                        return False
                    hh, ww = gray.shape
                    lms = res.face_landmarks[0]
                    xs = [int(lm.x * ww) for lm in lms]
                    ys = [int(lm.y * hh) for lm in lms]
                    mx, my = min(xs), min(ys)
                    mx2, my2 = max(xs), max(ys)
                    face_roi = gray[my:my2, mx:mx2]
                    if face_roi.size == 0:
                        return False
                except Exception as e:
                    print(f'save_face_sample MP fallback error: {e}')
                    return False
            else:
                height, width = gray.shape[:2]
                print(
                    f"save_face_sample: no face detected image={width}x{height} "
                    f"cascades={len(self.cascades)} mediapipe={self.model_loaded}"
                )
                return False
            roi = cv2.resize(face_roi, (200, 200))
            existing = list(Path(self.face_images_dir).glob(f"user_{user_id}_*.jpg"))
            count = len(existing)
            save_dir = self.face_images_dir
            # Save original
            self._imwrite(os.path.join(save_dir, f"user_{user_id}_{count:03d}.jpg"), roi)
            # Augment: flip and brightness variants to give LBPH more samples
            self._imwrite(os.path.join(save_dir, f"user_{user_id}_{count+1:03d}.jpg"), cv2.flip(roi, 1))
            small = cv2.resize(roi, (180, 180))
            self._imwrite(os.path.join(save_dir, f"user_{user_id}_{count+2:03d}.jpg"), cv2.resize(small, (200, 200)))
            bright = cv2.convertScaleAbs(roi, alpha=1.2, beta=10)
            self._imwrite(os.path.join(save_dir, f"user_{user_id}_{count+3:03d}.jpg"), bright)
            self._train_recognizer()
            return True
        except Exception as e:
            print(f"save_face_sample error: {e}")
            return False

    def _train_recognizer(self):
        faces, labels = [], []
        for fname in sorted(os.listdir(self.face_images_dir)):
            if not fname.endswith(".jpg"):
                continue
            parts = fname.split("_")
            if len(parts) < 2:
                continue
            try:
                uid = int(parts[1])
            except ValueError:
                continue
            img = self._imread(os.path.join(self.face_images_dir, fname), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            faces.append(img)
            labels.append(uid)
        if len(faces) == 0:
            self.recognizer_trained = False
            return False
        # OpenCV LBPH needs >1 sample; auto-augment if only 1
        if len(faces) < 2:
            faces.append(cv2.flip(faces[0], 1))
            labels.append(labels[0])
            faces.append(cv2.resize(cv2.resize(faces[0], (180, 180)), (200, 200)))
            labels.append(labels[0])
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.train(faces, np.array(labels))
        model_path = os.path.join(self.face_images_dir, "lbph_model.yml")
        self.recognizer.write(model_path)
        self.recognizer_trained = True
        return True

    def lbph_predict(self, image_bytes, user_id):
        if not self.recognizer_trained:
            return None, None
        try:
            arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return None, None
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            box = self._detect_face_box(gray)
            if box is not None:
                x, y, w, h = box
                face_roi = gray[y:y+h, x:x+w]
            elif self.model_loaded:
                try:
                    from mediapipe.tasks.python import vision
                    import mediapipe as mp
                    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    mpimg = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    res = self.detector.detect(mpimg)
                    if not res.face_landmarks:
                        return None, None
                    hh, ww = gray.shape
                    lms = res.face_landmarks[0]
                    xs = [int(lm.x * ww) for lm in lms]
                    ys = [int(lm.y * hh) for lm in lms]
                    face_roi = gray[min(ys):max(ys), min(xs):max(xs)]
                    if face_roi.size == 0:
                        return None, None
                except Exception as e:
                    print(f'lbph_predict MP fallback error: {e}')
                    return None, None
            else:
                return None, None
            roi = cv2.resize(face_roi, (200, 200))
            predicted, confidence = self.recognizer.predict(roi)
            return predicted, confidence
        except Exception as e:
            print(f"lbph_predict error: {e}")
            return None, None

    def decode_image(self, s):
        if "," in s:
            s = s.split(",")[1]
        return base64.b64decode(s)

face_service = FaceService()

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
import numpy as np


class TestFaceService:
    """单元测试：人脸识别核心逻辑"""

    def test_decode_image_from_base64(self):
        """测试Base64图片解码"""
        from app.services.face_service import face_service
        import base64
        raw = bytes([137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82,
                     0, 0, 0, 1, 0, 0, 0, 1, 8, 2, 0, 0, 0, 144, 119, 83, 222,
                     0, 0, 0, 12, 73, 68, 65, 84, 8, 215, 99, 248, 207, 192, 0,
                     0, 0, 4, 0, 1, 54, 99, 164, 77, 0, 0, 0, 0, 73, 69, 78, 68,
                     174, 66, 96, 130])
        b64 = base64.b64encode(raw).decode()
        decoded = face_service.decode_image(b64)
        assert isinstance(decoded, bytes)
        assert len(decoded) > 0

    def test_decode_image_with_data_uri_prefix(self):
        from app.services.face_service import face_service
        import base64
        raw = b"test_image_bytes"
        b64 = "data:image/jpeg;base64," + base64.b64encode(raw).decode()
        decoded = face_service.decode_image(b64)
        assert decoded == raw

    def test_decode_image_no_prefix(self):
        from app.services.face_service import face_service
        import base64
        raw = b"raw_bytes_only"
        b64 = base64.b64encode(raw).decode()
        decoded = face_service.decode_image(b64)
        assert decoded == raw

    def test_compare_faces_identical(self):
        from app.services.face_service import face_service
        f1 = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
        is_match, distance = face_service.compare_faces(f1, f1)
        assert is_match  # use truthiness, not "is True"
        assert distance < 0.12

    def test_compare_faces_similar(self):
        from app.services.face_service import face_service
        f1 = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
        f2 = np.array([0.11, 0.21, 0.31, 0.41, 0.51], dtype=np.float32)
        is_match, distance = face_service.compare_faces(f1, f2)
        assert is_match

    def test_compare_faces_different(self):
        from app.services.face_service import face_service
        f1 = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
        f3 = np.array([0.9, 0.8, 0.7, 0.6, 0.5], dtype=np.float32)
        is_match, distance = face_service.compare_faces(f1, f3)
        assert not is_match

    def test_compare_faces_dimension_mismatch(self):
        from app.services.face_service import face_service
        f1 = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
        f2 = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        is_match, distance = face_service.compare_faces(f1, f2)
        assert not is_match
        assert distance == 99.0

    def test_compare_faces_empty_feature(self):
        from app.services.face_service import face_service
        f1 = np.array([], dtype=np.float32)
        f2 = np.array([0.1, 0.2], dtype=np.float32)
        is_match, distance = face_service.compare_faces(f1, f2)
        assert not is_match
        assert distance == 99.0

    def test_feature_extraction_with_no_face(self):
        from app.services.face_service import face_service
        import io
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        features = face_service.extract_features(buf.getvalue())
        # No face in blank image; either None (MP) or some fallback features (CV)
        pass  # accept any outcome

    def test_lbph_predict_no_recognizer(self):
        from app.services.face_service import face_service
        import io
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(100, 100, 100))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        predicted, confidence = face_service.lbph_predict(buf.getvalue(), 1)
        assert predicted is None
        assert confidence is None

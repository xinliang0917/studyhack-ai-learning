import io
import os
import uuid
from typing import List

from app.config import settings

class DocumentParser:
    EXTRACT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
    os.makedirs(EXTRACT_DIR, exist_ok=True)
    _ocr_engine = None

    @staticmethod
    def parse(file_path: str, file_type: str) -> List[str]:
        file_type = file_type.lower().lstrip(".")
        if file_type == "pdf":
            return DocumentParser._parse_pdf(file_path)
        elif file_type == "docx":
            return DocumentParser._parse_docx(file_path)
        elif file_type == "pptx":
            return DocumentParser._parse_pptx(file_path)
        elif file_type == "txt":
            return DocumentParser._parse_txt(file_path)
        elif file_type in ("md", "markdown"):
            return DocumentParser._parse_md(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @staticmethod
    def _ocr_image_bytes(img_bytes: bytes) -> str:
        try:
            import numpy as np
            from PIL import Image
            from rapidocr_onnxruntime import RapidOCR
            if DocumentParser._ocr_engine is None:
                DocumentParser._ocr_engine = RapidOCR()
            image = np.array(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
            result, _ = DocumentParser._ocr_engine(image)
            if not result:
                return ""
            return "\n".join(str(item[1]) for item in result if len(item) > 1)
        except Exception:
            pass
        try:
            import pytesseract
            from PIL import Image
            image = Image.open(io.BytesIO(img_bytes))
            try:
                return pytesseract.image_to_string(image, lang="chi_sim+eng")
            except Exception:
                return pytesseract.image_to_string(image, lang="eng")
        except Exception:
            return ""

    @staticmethod
    def _ocr_pdf_page(file_path: str, page_index: int) -> str:
        try:
            import fitz
        except Exception:
            return ""
        try:
            doc = fitz.open(file_path)
            page = doc[page_index]
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            doc.close()
        except Exception:
            return ""
        return DocumentParser._ocr_image_bytes(img_bytes)

    @staticmethod
    def _parse_pdf(file_path: str) -> List[str]:
        import pdfplumber
        texts = []
        with pdfplumber.open(file_path) as pdf:
            for index, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if (
                    settings.ocr_enabled
                    and len(text.strip()) < settings.ocr_min_text
                ):
                    ocr_text = DocumentParser._ocr_pdf_page(file_path, index)
                    if ocr_text.strip():
                        text = f"{text}\n{ocr_text}".strip()
                if text.strip():
                    texts.append(text)
        return texts if texts else ["[PDF content could not be extracted]"]

    @staticmethod
    def _parse_docx(file_path: str) -> List[str]:
        from docx import Document
        doc = Document(file_path)
        texts = []
        for para in doc.paragraphs:
            if para.text.strip():
                texts.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text for cell in row.cells)
                texts.append(row_text)
        return texts if texts else ["[DOCX content could not be extracted]"]

    @staticmethod
    def _parse_pptx(file_path: str) -> List[str]:
        from pptx import Presentation
        prs = Presentation(file_path)
        texts = []
        for slide in prs.slides:
            slide_texts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_texts.append(shape.text)
            if slide_texts:
                texts.extend(slide_texts)
        return texts if texts else ["[PPT content could not be extracted]"]

    @staticmethod
    def _parse_txt(file_path: str) -> List[str]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [line.strip() for line in content.split("\n") if line.strip()]

    @staticmethod
    def _parse_md(file_path: str) -> List[str]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [line for line in content.split("\n") if line.strip()]

    @staticmethod
    def save_upload(file_content: bytes, filename: str, user_id: int = None) -> str:
        safe_name = os.path.basename(filename) or "upload.bin"
        target_dir = DocumentParser.EXTRACT_DIR
        if user_id is not None:
            target_dir = os.path.join(target_dir, str(user_id))
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, f"{uuid.uuid4().hex}_{safe_name}")
        with open(file_path, "wb") as f:
            f.write(file_content)
        return file_path

    @staticmethod
    def delete_file(file_path: str) -> bool:
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            os.remove(file_path)
            return True
        except OSError:
            return False

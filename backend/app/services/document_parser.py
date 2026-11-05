import os
from typing import List

class DocumentParser:
    EXTRACT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
    os.makedirs(EXTRACT_DIR, exist_ok=True)

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
    def _parse_pdf(file_path: str) -> List[str]:
        import pdfplumber
        texts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
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
    def save_upload(file_content: bytes, filename: str) -> str:
        os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"), exist_ok=True)
        # Remove any path traversal
        safe_name = os.path.basename(filename)
        file_path = os.path.join(DocumentParser.EXTRACT_DIR, safe_name)
        with open(file_path, "wb") as f:
            f.write(file_content)
        return file_path

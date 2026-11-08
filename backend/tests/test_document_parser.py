import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
import tempfile


class TestDocumentParser:
    """单元测试：文档解析模块核心逻辑"""

    def test_parse_txt(self):
        from app.services.document_parser import DocumentParser
        content = b"Hello World\nLine 2\nLine 3"
        path = DocumentParser.save_upload(content, "test.txt")
        texts = DocumentParser.parse(path, "txt")
        assert len(texts) == 3
        assert texts[0] == "Hello World"
        os.remove(path)

    def test_parse_md(self):
        from app.services.document_parser import DocumentParser
        content = b"# Title\n## Subtitle\nContent"
        path = DocumentParser.save_upload(content, "test.md")
        texts = DocumentParser.parse(path, "md")
        assert len(texts) == 3
        assert texts == ["Title", "Subtitle", "Content"]
        os.remove(path)

    def test_parse_markdown_extension(self):
        from app.services.document_parser import DocumentParser
        content = b"# Heading\nParagraph"
        path = DocumentParser.save_upload(content, "test.markdown")
        texts = DocumentParser.parse(path, "markdown")
        assert len(texts) == 2
        assert texts == ["Heading", "Paragraph"]
        os.remove(path)

    def test_parse_md_strips_formatting_symbols(self):
        from app.services.document_parser import DocumentParser
        content = (
            "# 标题\n"
            "**粗体** 和 *斜体*\n"
            "- 列表项\n"
            "> 引用\n"
            "[链接](https://example.com)\n"
        ).encode("utf-8")
        path = DocumentParser.save_upload(content, "format.md")
        texts = DocumentParser.parse(path, "md")
        assert texts == ["标题", "粗体 和 斜体", "列表项", "引用", "链接"]
        os.remove(path)

    def test_markdown_to_txt_returns_plain_text(self):
        from app.services.document_parser import DocumentParser
        content = b"## Head\nSome **strong** text"
        path = DocumentParser.save_upload(content, "plain.md")
        text = DocumentParser.markdown_to_txt(path)
        assert text == "Head\nSome strong text"
        os.remove(path)

    def test_unsupported_type_raises_error(self):
        from app.services.document_parser import DocumentParser
        with pytest.raises(ValueError, match="Unsupported file type"):
            DocumentParser.parse("test.xyz", "xyz")

    def test_unsupported_type_dot_prefix(self):
        from app.services.document_parser import DocumentParser
        with pytest.raises(ValueError, match="Unsupported file type"):
            DocumentParser.parse("test.xyz", ".xyz")

    def test_save_and_parse_txt(self):
        from app.services.document_parser import DocumentParser
        content = b"Test document content for parsing"
        path = DocumentParser.save_upload(content, "save_test.txt")
        assert os.path.exists(path)
        texts = DocumentParser.parse(path, "txt")
        assert len(texts) == 1
        assert "Test" in texts[0]
        os.remove(path)

    def test_empty_txt_lines_skipped(self):
        from app.services.document_parser import DocumentParser
        content = b"Line1\n\n\nLine2\n\nLine3"
        path = DocumentParser.save_upload(content, "empty.txt")
        texts = DocumentParser.parse(path, "txt")
        assert len(texts) == 3
        os.remove(path)

    def test_empty_md_lines_kept(self):
        from app.services.document_parser import DocumentParser
        content = b"Line1\n\n\nLine2"
        path = DocumentParser.save_upload(content, "empty.md")
        texts = DocumentParser.parse(path, "md")
        assert len(texts) >= 2
        os.remove(path)

    def test_save_upload_prevents_path_traversal(self):
        from app.services.document_parser import DocumentParser
        content = b"safe"
        path = DocumentParser.save_upload(content, "../../malicious.txt")
        assert ".." not in path.split(os.sep)[-1]
        assert os.path.exists(path)
        os.remove(path)

    def test_save_upload_empty_file(self):
        from app.services.document_parser import DocumentParser
        path = DocumentParser.save_upload(b"", "empty.txt")
        assert os.path.exists(path)
        texts = DocumentParser.parse(path, "txt")
        assert len(texts) == 0
        os.remove(path)

    def test_save_upload_unicode_content(self):
        from app.services.document_parser import DocumentParser
        content = "你好世界\n测试文档".encode("utf-8")
        path = DocumentParser.save_upload(content, "unicode.txt")
        texts = DocumentParser.parse(path, "txt")
        assert texts[0] == "你好世界"
        os.remove(path)

    def test_chunking_small_text_no_split(self):
        from app.services.vector_store import vector_store
        texts = ["Short text"]
        chunks = vector_store.get_chunks(texts, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert chunks[0]["content"] == "Short text"

    def test_chunking_large_text_splits(self):
        from app.services.vector_store import vector_store
        texts = ["A" * 1000, "B" * 300]
        chunks = vector_store.get_chunks(texts, chunk_size=500, overlap=50)
        assert len(chunks) >= 3
        assert all("index" in c for c in chunks)
        assert all("content" in c for c in chunks)

    def test_chunking_overlap_boundary(self):
        from app.services.vector_store import vector_store
        text = "X" * 1000
        chunks = vector_store.get_chunks([text], chunk_size=300, overlap=30)
        assert len(chunks) >= 3
        expected_count = -(-1000 // 270)
        assert len(chunks) == expected_count

    def test_chunking_empty_list(self):
        from app.services.vector_store import vector_store
        chunks = vector_store.get_chunks([], chunk_size=500, overlap=50)
        assert chunks == []

    def test_chunking_zero_overlap(self):
        from app.services.vector_store import vector_store
        texts = ["A" * 1000]
        chunks = vector_store.get_chunks(texts, chunk_size=500, overlap=0)
        assert len(chunks) == 2
        assert len(chunks[0]["content"]) == 500
        assert len(chunks[1]["content"]) == 500

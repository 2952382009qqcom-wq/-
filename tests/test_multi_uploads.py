"""Ordered batches must include every attachment or reject the entire batch."""

import io
import unittest
from unittest import mock

from PIL import Image
from werkzeug.datastructures import FileStorage

from core import doc_parser


def upload(name, data=b"text"):
    return FileStorage(stream=io.BytesIO(data), filename=name)


class MultiUploadTests(unittest.TestCase):
    def test_real_images_are_each_ocrd_in_order_with_per_file_metadata(self):
        image = io.BytesIO()
        Image.new("RGB", (2, 2), "white").save(image, "PNG")
        with mock.patch.object(doc_parser, "_run_ocr", side_effect=[
            ("第一页合同", 0.95), ("第二页争议条款", 0.85),
        ]) as ocr:
            filename, parsed = doc_parser.parse_uploads_detailed([
                upload("page1.png", image.getvalue()),
                upload("page2.png", image.getvalue()),
            ])
        self.assertEqual(ocr.call_count, 2)
        self.assertEqual(filename, "2 个附件")
        self.assertLess(parsed.text.index("第一页合同"), parsed.text.index("第二页争议条款"))
        self.assertEqual(parsed.metadata["file_count"], 2)
        self.assertEqual(parsed.page_count, 2)
        self.assertAlmostEqual(parsed.ocr_confidence, 0.9)
        self.assertEqual([item["filename"] for item in parsed.files], ["page1.png", "page2.png"])

    def test_single_file_keeps_legacy_response_metadata(self):
        name, parsed = doc_parser.parse_uploads_detailed([upload("note.txt", b"original")])
        self.assertEqual((name, parsed.text, parsed.method), ("note.txt", "original", "text"))
        self.assertNotIn("files", parsed.metadata)

    def test_corrupt_later_file_is_not_silently_ignored(self):
        with self.assertRaises(doc_parser.DocumentParseError) as raised:
            doc_parser.parse_uploads_detailed([
                upload("first.txt", b"valid"), upload("broken.png", b"not an image"),
            ])
        self.assertEqual(raised.exception.code, "invalid_image")
        self.assertIn("第 2 个附件", raised.exception.message)
        self.assertIn("broken.png", raised.exception.message)

    def test_count_limit_is_checked_before_any_parsing(self):
        parser = mock.Mock()
        with self.assertRaises(doc_parser.DocumentParseError) as raised:
            doc_parser.parse_uploads_detailed([upload(f"{i}.txt") for i in range(11)], parser=parser)
        self.assertEqual(raised.exception.code, "too_many_files")
        parser.assert_not_called()

    def test_combined_byte_limit_uses_actual_stream_sizes_before_ocr(self):
        files = [upload("a.png", b"123456"), upload("b.png", b"123456")]
        parser = mock.Mock()
        with mock.patch.object(doc_parser, "_max_upload_bytes", return_value=10):
            with self.assertRaises(doc_parser.DocumentParseError) as raised:
                doc_parser.parse_uploads_detailed(files, parser=parser)
        self.assertEqual(raised.exception.code, "files_too_large")
        self.assertEqual([item.stream.tell() for item in files], [0, 0])
        parser.assert_not_called()

    def test_total_page_limit_stops_before_remaining_files(self):
        parser = mock.Mock(side_effect=lambda file: (
            file.filename, doc_parser.ParsedDocument(text="正文", method="pdf_text", page_count=11),
        ))
        with self.assertRaises(doc_parser.DocumentParseError) as raised:
            doc_parser.parse_uploads_detailed([upload(f"{i}.pdf") for i in range(3)], parser=parser)
        self.assertEqual(raised.exception.code, "too_many_pages")
        self.assertEqual(parser.call_count, 2)

    def test_max_count_and_exact_byte_boundary_are_allowed(self):
        files = [upload(f"{i}.txt", b"abcd") for i in range(10)]
        with mock.patch.object(doc_parser, "_max_upload_bytes", return_value=40):
            _, parsed = doc_parser.parse_uploads_detailed(files)
        self.assertEqual(parsed.metadata["file_count"], 10)
        self.assertEqual(parsed.files[-1]["filename"], "9.txt")

    def test_empty_batch_is_rejected(self):
        with self.assertRaises(doc_parser.DocumentParseError) as raised:
            doc_parser.parse_uploads_detailed([upload("", b"")])
        self.assertEqual(raised.exception.code, "missing_file")

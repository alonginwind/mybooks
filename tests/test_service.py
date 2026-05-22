#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import tempfile
import unittest

from tests.test_main import TestWithUserLogin, setUpModule as init, testdir
from webserver.services import AsyncService
from webserver.services.convert import ConvertService
from webserver.services.extract import ExtractService
from webserver.handlers.static_files import guess_favicon_content_type


def setUpModule():
    init()


class TestConvert(TestWithUserLogin):
    def test_convert(self):
        fin = testdir + "/cases/old.epub"
        fout = "/tmp/output.mobi"
        flog = "/tmp/output.log"
        ok = ConvertService().do_ebook_convert(fin, fout, flog)
        self.assertEqual(ok, True)


class TestExtract(TestWithUserLogin):
    def test_convert(self):
        bid = 666
        fpath = testdir + "/cases/book.txt"
        ok = ExtractService().parse_txt_content(bid, fpath)
        self.assertEqual(ok, True)


class TestAsyncServiceRegistry(unittest.TestCase):
    def test_same_method_name_uses_distinct_queue(self):
        class FirstService(AsyncService):
            def do_import(self):
                return None

        class SecondService(AsyncService):
            def do_import(self):
                return None

        AsyncService.running = {}
        q1 = FirstService().start_service(FirstService.do_import)
        q2 = SecondService().start_service(SecondService.do_import)

        self.assertIsNot(q1, q2)
        self.assertEqual(len(AsyncService.running), 2)


class TestFaviconContentType(unittest.TestCase):
    def test_svg_payload_uses_svg_content_type(self):
        with tempfile.NamedTemporaryFile("wb", suffix=".ico", delete=False) as tmp:
            tmp.write(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>")
            tmp_path = tmp.name

        try:
            self.assertEqual(guess_favicon_content_type(tmp_path), "image/svg+xml")
        finally:
            os.unlink(tmp_path)

    def test_falls_back_to_extension_for_binary_icon(self):
        with tempfile.NamedTemporaryFile("wb", suffix=".ico", delete=False) as tmp:
            tmp.write(b"\x00\x00\x01\x00")
            tmp_path = tmp.name

        try:
            self.assertIn(guess_favicon_content_type(tmp_path), {"image/x-icon", "image/vnd.microsoft.icon"})
        finally:
            os.unlink(tmp_path)

#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import logging

from webserver.constants import META_SOURCE_OPENLIBRARY
from webserver.plugins.meta.base import MetaSourcePlugin

from .api import OpenLibraryApi, KEY


class OpenLibraryMetaPlugin(MetaSourcePlugin):
    """Open Library 信息源插件 —— 免费 ISBN 精确查询，适合外文书兜底"""

    SOURCE_KEYS = (META_SOURCE_OPENLIBRARY,)
    PROVIDER_KEY = KEY

    def search(self, title=None, isbn=None, publisher=None):
        if not isbn:
            return []
        api = OpenLibraryApi(copy_image=False)
        try:
            book = api.get_book_by_isbn(isbn)
            return [book] if book else []
        except Exception as e:
            logging.error("OpenLibrary search failed: %s", e)
            return []

    def search_by_isbn(self, isbn):
        """按 ISBN 查询（用于 find_physical_book_by_isbn 兜底链）"""
        if not isbn:
            return None
        try:
            return OpenLibraryApi(copy_image=True).get_book_by_isbn(isbn)
        except Exception as e:
            logging.error("OpenLibrary ISBN search failed for %s: %s", isbn, e)
            return None

    def search_best(self, mi):
        isbn = getattr(mi, "isbn", None)
        if not isbn:
            return None
        return self.search_by_isbn(isbn)

    def get_metadata_by_provider(self, provider_value, mi=None):
        # provider_value 形如 "books/OL2045747M"，暂不支持按 key 重新拉取，直接返回已有信息
        cover_url = getattr(mi, "cover_url", None)
        if mi and cover_url:
            cover_data = OpenLibraryApi.get_cover(cover_url)
            if cover_data:
                mi.cover_data = cover_data
        return mi

    def get_cover(self, cover_url):
        return OpenLibraryApi.get_cover(cover_url)

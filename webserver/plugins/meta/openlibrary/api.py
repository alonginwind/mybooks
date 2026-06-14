#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import logging
import requests

KEY = "openlibrary"

_BASE_URL = "https://openlibrary.org/api/books"


class OpenLibraryApi:
    """Open Library Books API (https://openlibrary.org/dev/docs/api)
    完全免费，无需 API Key，支持 ISBN 精确查询。
    """

    def __init__(self, copy_image=True):
        self.copy_image = copy_image
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MyBooks/1.0 (https://github.com/talebook/talebook)",
            "Accept": "application/json",
        })

    def get_book_by_isbn(self, isbn):
        if not isbn:
            return None

        clean_isbn = isbn.replace("-", "").strip()
        url = _BASE_URL
        params = {
            "bibkeys": f"ISBN:{clean_isbn}",
            "format": "json",
            "jscmd": "data",
        }
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logging.error("OpenLibrary request failed for ISBN %s: %s", isbn, e)
            return None

        key = f"ISBN:{clean_isbn}"
        if key not in data:
            logging.info("OpenLibrary: no result for ISBN %s", isbn)
            return None

        return self._build_metadata(data[key], clean_isbn)

    def _build_metadata(self, book, isbn):
        from calibre.ebooks.metadata.book.base import Metadata
        from calibre.utils.date import utcnow

        title = book.get("title", "").strip()
        if not title:
            return None

        authors = [a["name"] for a in book.get("authors", [])] or ["Unknown"]
        mi = Metadata(title, authors)
        mi.author_sort = authors[0]
        mi.isbn = isbn

        publishers = book.get("publishers", [])
        if publishers:
            mi.publisher = publishers[0].get("name", "")

        publish_date = book.get("publish_date", "")
        if publish_date:
            try:
                from calibre.utils.date import parse_only_date
                mi.pubdate = parse_only_date(publish_date, assume_utc=True)
            except Exception:
                mi.pubdate = utcnow()
        else:
            mi.pubdate = utcnow()

        mi.timestamp = utcnow()

        # subjects → tags
        subjects = book.get("subjects", [])
        mi.tags = [s["name"] for s in subjects[:10] if isinstance(s, dict) and s.get("name")]

        # number_of_pages
        pages = book.get("number_of_pages")
        if pages:
            try:
                mi.tags.append(f"{pages}p")
            except Exception:
                pass

        # description / notes
        notes = book.get("notes", "")
        if isinstance(notes, dict):
            notes = notes.get("value", "")
        mi.comments = notes or ""

        # website
        mi.website = book.get("url", "")

        mi.source = "Open Library"
        mi.provider_key = KEY
        mi.provider_value = book.get("key", f"/isbn/{isbn}").lstrip("/")

        # Cover
        cover = book.get("cover", {})
        cover_url = cover.get("large") or cover.get("medium") or cover.get("small")
        if cover_url:
            mi.cover_url = cover_url
            if self.copy_image:
                mi.cover_data = self._get_cover(cover_url)

        return mi

    def _get_cover(self, url):
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return ("jpg", resp.content)
        except Exception as e:
            logging.warning("OpenLibrary: failed to download cover %s: %s", url, e)
            return None

    @staticmethod
    def get_cover(url):
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return ("jpg", resp.content)
        except Exception as e:
            logging.warning("OpenLibrary: failed to get cover %s: %s", url, e)
            return None

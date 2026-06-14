#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import logging
import re
import requests

KEY = "cnbip"

_BASE_URL = "http://www.cnbip.cn/Stock/Search.aspx"


class CnbipApi:
    """中国出版物信息平台 (http://www.cnbip.cn) API

    收录国内出版物非常全面，适合作为中文书的最终兜底数据源。
    通过 ISBN 查询，解析返回的 HTML 页面获取书籍信息。
    """

    def __init__(self, copy_image=True):
        self.copy_image = copy_image
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    def get_book_by_isbn(self, isbn):
        if not isbn:
            return None

        clean_isbn = isbn.replace("-", "").strip()
        params = {"ISBN": clean_isbn}
        try:
            resp = self.session.get(_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            logging.error("Cnbip request failed for ISBN %s: %s", isbn, e)
            return None

        return self._parse_result(resp.text, clean_isbn)

    def _parse_result(self, html, isbn):
        # 检查是否有结果
        if "总品种：0" in html or "总品种 ：0" in html:
            logging.info("Cnbip: no result for ISBN %s", isbn)
            return None
    
        # 找到包含 ISBN 的结果行，提取各列数据
        # 页面结构: <tr><td>checkbox</td><td>ISBN</td><td>书名</td><td>定价</td><td>作者</td><td>出版社</td><td>出版日期</td><td>详情</td>...</tr>
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL)
        result_row = None
        for row in rows:
            if isbn in row and re.search(r'<td[^>]*>.*?</td>\s*<td[^>]*>.*?' + re.escape(isbn), row, re.DOTALL):
                result_row = row
                break
    
        if not result_row:
            logging.warning("Cnbip: could not find result row for ISBN %s", isbn)
            return None
    
        cells = re.findall(r"<td[^>]*>(.*?)</td>", result_row, re.DOTALL)
        if len(cells) < 7:
            logging.warning("Cnbip: not enough cells in result row for ISBN %s (got %d)", isbn, len(cells))
            return None
    
        def clean(s):
            return re.sub(r"<[^>]+>", "", s).strip()
    
        # cells[0] = checkbox, cells[1] = ISBN, cells[2] = 书名, cells[3] = 定价,
        # cells[4] = 作者, cells[5] = 出版社, cells[6] = 出版日期
        title = clean(cells[2])
        if not title:
            return None
    
        from calibre.ebooks.metadata.book.base import Metadata
        from calibre.utils.date import utcnow
    
        author_raw = clean(cells[4]) or "佚名"
        authors = [a.strip() for a in re.split(r"[,，、;；]", author_raw) if a.strip()] or ["佚名"]
    
        mi = Metadata(title, authors)
        mi.author_sort = authors[0]
        mi.isbn = isbn
    
        publisher = clean(cells[5])
        if publisher:
            mi.publisher = publisher
    
        pubdate_str = clean(cells[6])
        if pubdate_str:
            mi.pubdate = self._parse_date(pubdate_str) or utcnow()
        else:
            mi.pubdate = utcnow()
    
        mi.timestamp = utcnow()
        mi.tags = []
        mi.comments = ""
        mi.source = "中国出版物信息平台"
        mi.provider_key = KEY
        mi.provider_value = isbn
    
        # 尝试获取封面
        cover_url = self._find_cover_url(result_row, html, isbn)
        if cover_url:
            mi.cover_url = cover_url
            if self.copy_image:
                mi.cover_data = self._get_cover(cover_url)
    
        return mi

    def _parse_date(self, date_str):
        """解析日期字符串，如 '2025年02月'、'2024'、'2023年03月01日'"""
        from calibre.utils.date import parse_only_date
        # 标准化为 yyyy-MM 格式
        m = re.match(r"(\d{4})年(\d{1,2})月", date_str)
        if m:
            date_str = f"{m.group(1)}-{int(m.group(2)):02d}"
        try:
            return parse_only_date(date_str, assume_utc=True)
        except Exception:
            return None

    def _find_cover_url(self, result_row, html, isbn):
        """尝试从详情页链接或页面中提取封面URL"""
        # 从结果行中查找详情链接
        detail_match = re.search(r"href='(/BaseInfo/BookInfo\.aspx\?id=\d+)'", result_row)
        if not detail_match:
            detail_match = re.search(r'href="(/BaseInfo/BookInfo\.aspx\?id=\d+)"', result_row)
        if not detail_match:
            # 兜底：在整个页面中搜索
            detail_match = re.search(r"href=['\"](/BaseInfo/BookInfo\.aspx\?id=\d+)['\"]", html)
        if not detail_match:
            return None

        detail_url = f"http://www.cnbip.cn{detail_match.group(1)}"
        try:
            resp = self.session.get(detail_url, timeout=10)
            # 从详情页找封面图片
            img_match = re.search(r'<img[^>]+src="([^"]*(?:cover|book|image)[^"]*)"', resp.text, re.IGNORECASE)
            if not img_match:
                img_match = re.search(r'class="[^"]*cover[^"]*"[^>]*src="([^"]*)"', resp.text, re.IGNORECASE)
            if not img_match:
                img_match = re.search(r'src="([^"]*(?:douban|img\d)[^"]*\.(?:jpg|jpeg|png))"', resp.text, re.IGNORECASE)
            if img_match:
                cover_url = img_match.group(1)
                if cover_url.startswith("//"):
                    cover_url = "https:" + cover_url
                elif cover_url.startswith("/"):
                    cover_url = f"http://www.cnbip.cn{cover_url}"
                return cover_url
        except Exception as e:
            logging.debug("Cnbip: failed to get cover from detail page: %s", e)
        return None

    def _get_cover(self, url):
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return ("jpg", resp.content)
        except Exception as e:
            logging.warning("Cnbip: failed to download cover %s: %s", url, e)
            return None

    @staticmethod
    def get_cover(url):
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return ("jpg", resp.content)
        except Exception as e:
            logging.warning("Cnbip: failed to get cover %s: %s", url, e)
            return None

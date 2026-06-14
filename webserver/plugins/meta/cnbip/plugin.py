#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import logging

from webserver.constants import META_SOURCE_CNBIP
from webserver.plugins.meta.base import MetaSourcePlugin

from .api import CnbipApi, KEY


class CnbipMetaPlugin(MetaSourcePlugin):
    """中国出版物信息平台信息源插件

    收录国内出版物非常全面，适合作为中文实体书 ISBN 查询的最终兜底数据源。
    当前仅作为 ISBN 实体书添加的兜底数据源使用（见 BookSearch.find_physical_book_by_isbn），
    不参与聚合搜索 / 自动刮削，也不受 META_SELECTED_SOURCES 限制。
    """

    SOURCE_KEYS = (META_SOURCE_CNBIP,)
    PROVIDER_KEY = KEY

    def search_by_isbn(self, isbn):
        """按 ISBN 查询（用于 find_physical_book_by_isbn 兜底链）"""
        if not isbn:
            return None
        try:
            return CnbipApi(copy_image=True).get_book_by_isbn(isbn)
        except Exception as e:
            logging.error("Cnbip ISBN search failed for %s: %s", isbn, e)
            return None

    def get_cover(self, cover_url):
        return CnbipApi.get_cover(cover_url)

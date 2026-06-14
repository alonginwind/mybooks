#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
图书搜索工具类，统一对外暴露各信息源插件的检索能力
@author: PoxenStudio, 2026-06
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from webserver.i18n import _

from webserver import loader
from webserver.constants import META_SELECTED_SOURCES
from webserver.plugins.meta.douban import DoubanMetaPlugin, has_proper_book
from webserver.plugins.meta.douban_v2 import DoubanV2MetaPlugin
from webserver.plugins.meta.baike import BaikeMetaPlugin
from webserver.plugins.meta.youshu import YoushuMetaPlugin
from webserver.plugins.meta.calibre import CalibreMetaPlugin
from webserver.plugins.meta.xhsd import XhsdMetaPlugin
from webserver.plugins.meta.neodb import NeodbMetaPlugin
from webserver.plugins.meta.openlibrary import OpenLibraryMetaPlugin

CONF = loader.get_settings()
_PLUGIN_CLASSES = [DoubanMetaPlugin, BaikeMetaPlugin, CalibreMetaPlugin, YoushuMetaPlugin, DoubanV2MetaPlugin, NeodbMetaPlugin]
_PROVIDER_PLUGIN_CLASSES = _PLUGIN_CLASSES + [XhsdMetaPlugin, OpenLibraryMetaPlugin]  # 不参与聚合搜索但需要 provider 路由


class BookSearch:
    has_proper_book = staticmethod(has_proper_book)

    _search_executor = None

    @classmethod
    def _get_search_executor(cls):
        if cls._search_executor is None:
            cls._search_executor = ThreadPoolExecutor(
                max_workers=max(1, len(_PLUGIN_CLASSES)),
                thread_name_prefix="meta-search",
            )
        return cls._search_executor

    @staticmethod
    def _enabled_plugins(sources):
        plugins = (klass() for klass in _PLUGIN_CLASSES)
        return [p for p in plugins if p.is_enabled(sources)]

    @staticmethod
    def all_sources():
        keys = []
        for klass in _PROVIDER_PLUGIN_CLASSES:
            for key in klass.SOURCE_KEYS:
                if key not in keys:
                    keys.append(key)
        return keys

    @staticmethod
    def _find_plugin_by_provider_key(provider_key):
        for klass in _PROVIDER_PLUGIN_CLASSES:
            plugin = klass()
            if plugin.PROVIDER_KEY == provider_key:
                return plugin
        return None

    @staticmethod
    def search_books(title=None, isbn=None, publisher=None):
        """
        从已启用的信息源插件并行搜索图书信息（多结果聚合，供候选列表展示）

        Args:
            title: 图书标题（可选）
            isbn: ISBN号（可选）
            publisher: 出版社（可选）
            * title & isbn 至少有一个
        Returns:
            list: 搜索到的图书元数据列表，按信息源声明顺序拼接
        """
        sources = CONF.get(META_SELECTED_SOURCES, [])
        if not sources:
            return []

        if not title and not isbn:
            return []

        logging.info(_("开始搜索图书，title: %s, isbn: %s, publisher: %s, sources: %s") % (title, isbn, publisher, sources))

        # 清理标题，移除括号及其内容（含括号本身）
        if title:
            clean_title = re.sub(r'\([^)]*\)|\[[^\]]*\]|（[^）]*）|【[^】]*】', '', title).strip()
        else:
            clean_title = ""

        plugins = BookSearch._enabled_plugins(sources)
        if not plugins:
            return []

        # 每个已启用的信息源各自分配一个 worker 并行搜索，未启用的源不创建 worker
        executor = BookSearch._get_search_executor()
        futures = {
            executor.submit(plugin.search, title=clean_title, isbn=isbn, publisher=publisher): plugin
            for plugin in plugins
        }

        results = {}
        for future, plugin in futures.items():
            try:
                results[plugin] = future.result(timeout=60) or []
            except Exception as e:
                logging.error("信息源[%s]查询失败: %s" % (plugin.name, str(e)))
                results[plugin] = []

        # 按信息源声明顺序拼接，保持与改造前一致的展示顺序
        books = []
        for plugin in plugins:
            books.extend(results.get(plugin, []))

        logging.info("搜索完成，找到 %d 本书" % len(books))
        return books

    @staticmethod
    def search_best_book(mi):
        """
        按信息源优先级顺序逐个查询，返回第一个可用的最佳匹配（找到即停止，不再查询后续信息源）

        Args:
            mi: 参考的书籍元数据（Metadata），至少需要 title；isbn/author/publisher 按需使用

        Returns:
            Metadata or None: 找到的最佳匹配書籍信息，找不到时返回 None
        """
        sources = CONF.get(META_SELECTED_SOURCES, [])
        if not sources:
            return None

        title = re.sub("[(（].*", "", mi.title)
        search_mi = mi
        if title != mi.title:
            search_mi = mi.deepcopy()
            search_mi.title = title

        for plugin in BookSearch._enabled_plugins(sources):
            try:
                book = plugin.search_best(search_mi)
                if book:
                    return book
            except Exception:
                logging.error(_("信息源[%s]查询 %s 失败"), plugin.name, title)

        return None

    @staticmethod
    def get_cover(provider_key, cover_url):
        plugin = BookSearch._find_plugin_by_provider_key(provider_key)
        return plugin.get_cover(cover_url) if plugin else None

    @staticmethod
    def get_metadata_by_provider(provider_key, provider_value, mi):
        plugin = BookSearch._find_plugin_by_provider_key(provider_key)
        if plugin is None:
            return mi
        metadata = plugin.get_metadata_by_provider(provider_value, mi)
        return metadata if metadata is not None else mi

    @staticmethod
    def find_physical_book_by_isbn(isbn):
        """
        通过 ISBN 查询实体书信息：先豆瓣（受 META_SELECTED_SOURCES 限制），
        查不到再用新华书店(xhsd)兜底（不受 META_SELECTED_SOURCES 限制，与改造前行为一致）

        Args:
            isbn: ISBN号

        Returns:
            Metadata or None
        """
        sources = CONF.get(META_SELECTED_SOURCES, [])
        book_data = None

        douban_plugin = DoubanMetaPlugin()
        if douban_plugin.is_enabled(sources):
            try:
                book_data = douban_plugin.search_physical_by_isbn(isbn)
            except Exception as e:
                logging.error(f"Douban API error for ISBN {isbn}: {e}")
                book_data = None

        douban_plugin = DoubanV2MetaPlugin()
        if douban_plugin.is_enabled(sources) and not book_data:
            try:
                book_data = douban_plugin.search_physical_by_isbn(isbn)
            except Exception as e:
                logging.error(f"Douban V2 API error for ISBN {isbn}: {e}")
                book_data = None

        if not book_data:
            try:
                logging.info(f"Trying Xhsd API for ISBN {isbn}")
                book_data = XhsdMetaPlugin().search_by_isbn(isbn)
            except Exception as e:
                logging.error(f"Xhsd API error for ISBN {isbn}: {e}")
                book_data = None

        if not book_data:
            # Open Library：免费无需 API Key，适合外文书等国内数据库未收录的图书
            try:
                logging.info(f"Trying Open Library API for ISBN {isbn}")
                book_data = OpenLibraryMetaPlugin().search_by_isbn(isbn)
                if book_data:
                    logging.info(f"Open Library found: {getattr(book_data, 'title', '')}")
            except Exception as e:
                logging.error(f"Open Library API error for ISBN {isbn}: {e}")
                book_data = None

        return book_data

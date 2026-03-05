from io import BytesIO
from threading import Event

import sys
import os

# Setup Calibre paths
path = os.environ.get('CALIBRE_PYTHON_PATH', '/usr/lib/calibre')
if path not in sys.path:
    sys.path.insert(0, path)

sys.resources_location = os.environ.get('CALIBRE_RESOURCES_PATH', '/usr/share/calibre')
sys.extensions_location = os.environ.get('CALIBRE_EXTENSIONS_PATH', '/usr/lib/calibre/calibre/plugins')
sys.executables_location = os.environ.get('CALIBRE_EXECUTABLES_PATH', '/usr/bin')

from calibre.ebooks.metadata.sources.identify import identify
from calibre.ebooks.metadata.sources.covers import download_cover
from calibre.ebooks.metadata.sources.base import create_log
from calibre.ebooks.metadata.sources.update import patch_plugins
from calibre.customize.ui import metadata_plugins, all_metadata_plugins

# 必须先调用 patch_plugins() 以加载最新插件补丁（来自 calibre 服务器）
patch_plugins()


def print_available_plugins():
    """打印当前 calibre 环境可用插件列表。"""
    all_plugins = list(all_metadata_plugins())
    all_plugin_names = sorted({p.name for p in all_plugins})

    identify_plugins = list(metadata_plugins({'identify'}))
    identify_plugin_names = sorted({p.name for p in identify_plugins})

    print("=== Calibre 可用插件（全部）===")
    print(f"总数: {len(all_plugin_names)}")
    for name in all_plugin_names:
        print(name)

    print("\n=== Calibre 可用插件（支持 identify）===")
    print(f"总数: {len(identify_plugin_names)}")
    for name in identify_plugin_names:
        print(name)


print_available_plugins()

# 创建 log 对象（必须）
buf = BytesIO()
log = create_log(buf)

# 创建 abort 事件（用于中断）
abort = Event()

# ① 按 ISBN 查询
results = identify(
    log,
    abort,
    identifiers={'isbn': '9787115428028'},
    allowed_plugins={'Google', 'Amazon.com'},
    timeout=30,
)

if results:
    print("=== 查询结果(ISBN) ===")
    print("结果数量:", len(results))
    for result in results:
        print(f"Title: {result.title}, Authors: {result.authors}, Publisher: {result.publisher}, PubDate: {result.pubdate}")
        print(f"Identifiers: {result.identifiers}, Language: {result.language}")
        print(f"Rating: {result.rating}, Tags: {result.tags}")
        print(f"Comments: {result.comments[:100]}...")  # 只显示简介的前100字符
        print(result.identifiers)
        print("-" * 40)

# # ② 按书名+作者查询
# results = identify(
#     log,
#     abort,
#     title='流畅的 Python',
#     authors=['Luciano Ramalho'],
#     timeout=30,
# )

# ③ 限定只用 Google Books 和 Amazon
results = identify(
    log,
    abort,
    title='Python Cookbook',
    authors=['David Beazley'],
    allowed_plugins={'Google', 'Amazon.com'},  # 插件名称需精确匹配
    timeout=30,
)

# results 是按相关性排序的 Metadata 对象列表（最佳结果在 results[0]）
if results:
    print("=== 查询结果 (Title & Author) ===")
    print("结果数量:", len(results))
    for result in results:
        print(f"Title: {result.title}, Authors: {result.authors}, Publisher: {result.publisher}, PubDate: {result.pubdate}")
        print(f"Identifiers: {result.identifiers}, Language: {result.language}")
        print(f"Rating: {result.rating}, Tags: {result.tags}")
        print(f"Comments: {result.comments[:100]}...")  # 只显示简介的前100字符
        print("-" * 40)

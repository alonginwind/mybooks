#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import tornado

from webserver.i18n import _
from webserver.handlers.base import BaseHandler, js, is_admin


class AdminToolList(BaseHandler):
    @js
    @is_admin
    def get(self):
        from webserver.toolbox.toolset import ToolSet
        ToolSet.collect_tools()
        tools = [t.to_dict() for t in ToolSet.all_tools()]
        return {"err": "ok", "tools": tools}


class AdminRareBookDownloader(BaseHandler):
    @js
    @is_admin
    def post(self):
        from urllib.parse import urlparse
        from webserver.toolbox.rare_book_downloader import RareBookDownloader

        data = tornado.escape.json_decode(self.request.body)
        url = (data.get("url") or "").strip()
        if not url:
            return {"err": "params.url.missing", "msg": _("请提供URL参数")}

        host = urlparse(url).hostname or ""
        if host != "hkust.edu.hk" and not host.endswith(".hkust.edu.hk"):
            return {"err": "params.url.unsupported", "msg": _("不支持的URL，仅支持 hkust.edu.hk 及其子域名")}

        RareBookDownloader().download(url, self.user_id())
        return {"err": "ok", "msg": _("古书下载任务已启动，右上角可以查看进度")}


def routes():
    return [
        (r"/api/toolbox/list", AdminToolList),
        (r"/api/toolbox/rare_book_downloader", AdminRareBookDownloader),
    ]

# -*- coding: UTF-8 -*-
import logging
import threading
from tornado.web import RequestHandler
from tornado.wsgi import WSGIContainer
from webserver import loader

CONF = loader.get_settings()


class WebDAVHandler(RequestHandler):
    """
    Tornado request handler to bridge WebDAV WSGI app.
    支持WebDAV查询、下载和写入操作（sync目录可写）。
    路由在启动时无条件注册；是否启用由 CONF["ENABLE_WEBDAV_SERVICE"] 运行时控制。
    WSGI app 采用懒加载：首次请求时创建，此后缓存复用。
    """

    # Add WebDAV methods to supported methods list
    SUPPORTED_METHODS = RequestHandler.SUPPORTED_METHODS + (
        'PROPFIND',    # 查询文件/目录属性
        'MKCOL',       # 创建目录
    )

    # Lazily-initialized WSGI container; reset via reset_app() when needed.
    _wsgi_container: "WSGIContainer | None" = None
    _wsgi_container_lock: threading.Lock = threading.Lock()

    @classmethod
    def reset_app(cls) -> None:
        """Discard the cached WSGI app so it is recreated on the next request."""
        with cls._wsgi_container_lock:
            cls._wsgi_container = None

    def initialize(self, cache=None, session=None):
        """
        Store references needed to lazily create the WebDAV WSGI app.

        Args:
            cache: Calibre library cache (new_api)
            session: SQLAlchemy scoped session factory
        """
        self._cache = cache
        self._session = session

    def _get_wsgi_container(self) -> "WSGIContainer | None":
        """Return the cached WSGIContainer, creating it if necessary.

        Returns None when the WebDAV service is currently disabled.
        """
        if not CONF.get("ENABLE_WEBDAV_SERVICE", False):
            return None
        with WebDAVHandler._wsgi_container_lock:
            if WebDAVHandler._wsgi_container is None:
                from webserver.webdav.server import create_webdav_app
                wsgi_app = create_webdav_app(self._cache, self._session)
                WebDAVHandler._wsgi_container = WSGIContainer(wsgi_app)
                logging.info("[WebDAV] WSGI app initialized")
        return WebDAVHandler._wsgi_container

    def prepare(self):
        """Called before any HTTP method handler."""
        # Handle collection URL without trailing slash - redirect to add slash
        request_path = self.request.path
        if (request_path == "/books"
            or (request_path.startswith("/books/")
                and not request_path.endswith("/")
                and self.request.method == "GET")):
            # Check if this might be a collection (directory)
            # For /books specifically, always redirect
            if request_path == "/books":
                self.redirect(request_path + "/", permanent=False)
                self._finished = True
                return

        self._handle_request()
        self._finished = True

    def _handle_request(self):
        """Delegate the request to the WSGI application."""
        container = self._get_wsgi_container()
        if container is None:
            self.set_status(404)
            self.finish("WebDAV service is not enabled")
            return
        try:
            container(self.request)
        except Exception as e:
            logging.error(f"WebDAV handler error: {e}")
            import traceback
            logging.error(traceback.format_exc())
            self.set_status(500)
            self.finish("Internal Server Error")

    # Support all HTTP methods used by WebDAV (read-only)
    def get(self, *args, **kwargs):
        pass  # Handled in prepare()

    def head(self, *args, **kwargs):
        pass

    def options(self, *args, **kwargs):
        pass

    def propfind(self, *args, **kwargs):
        """WebDAV PROPFIND method - 查询文件/目录属性"""
        pass

    def mkcol(self, *args, **kwargs):
        """WebDAV MKCOL method - 创建目录"""
        pass

    def put(self, *args, **kwargs):
        """HTTP PUT method - 上传文件"""
        pass

    def delete(self, *args, **kwargs):
        """HTTP DELETE method - 删除文件/目录"""
        pass

# -*- coding: UTF-8 -*-
import logging
from tornado.web import RequestHandler
from tornado.wsgi import WSGIContainer

class WebDAVHandler(RequestHandler):
    """
    Tornado request handler to bridge WebDAV WSGI app.
    """

    # Add WebDAV methods to supported methods list
    SUPPORTED_METHODS = RequestHandler.SUPPORTED_METHODS + (
        'PROPFIND', 'PROPPATCH', 'MKCOL', 'COPY', 'MOVE', 'LOCK', 'UNLOCK'
    )

    def initialize(self, wsgi_app):
        """
        Initialize the handler with a WSGI application.

        Args:
            wsgi_app: WsgiDAV application instance
        """
        logging.info("[!!!!!]Initializing WebDAVHandler with WSGI application")
        self.wsgi_container = WSGIContainer(wsgi_app)

    def prepare(self):
        """Called before any HTTP method handler."""
        self._handle_request()
        self._finished = True

    def _handle_request(self):
        """Delegate the request to the WSGI application."""
        # Create WSGI environ from Tornado request
        try:
            self.wsgi_container(self.request)
        except Exception as e:
            logging.error(f"WebDAV handler error: {e}")
            import traceback
            logging.error(traceback.format_exc())
            self.set_status(500)
            self.finish("Internal Server Error")

    # Support all HTTP methods used by WebDAV
    def get(self, *args, **kwargs):
        pass  # Handled in prepare()

    def post(self, *args, **kwargs):
        pass

    def put(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def head(self, *args, **kwargs):
        pass

    def options(self, *args, **kwargs):
        pass

    def propfind(self, *args, **kwargs):
        """WebDAV PROPFIND method"""
        pass

    def proppatch(self, *args, **kwargs):
        """WebDAV PROPPATCH method"""
        pass

    def mkcol(self, *args, **kwargs):
        """WebDAV MKCOL method"""
        pass

    def copy(self, *args, **kwargs):
        """WebDAV COPY method"""
        pass

    def move(self, *args, **kwargs):
        """WebDAV MOVE method"""
        pass

    def lock(self, *args, **kwargs):
        """WebDAV LOCK method"""
        pass

    def unlock(self, *args, **kwargs):
        """WebDAV UNLOCK method"""
        pass


def setup_webdav_handler(wsgi_app):
    """
    Create a Tornado request handler configured with the WebDAV WSGI app.

    Args:
        wsgi_app: WsgiDAV application instance

    Returns:
        Configured handler class
    """
    return lambda: WebDAVHandler(wsgi_app=wsgi_app)

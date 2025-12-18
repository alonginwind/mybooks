#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Quick test to verify WebDAV service is accessible.
This creates a minimal test to check if WebDAV routes are working.
"""

import sys
import os

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
webserver_dir = os.path.dirname(current_dir)
project_dir = os.path.dirname(webserver_dir)
sys.path.insert(0, project_dir)
os.chdir(project_dir)

def test_webdav_routes():
    """Test that WebDAV routes are properly configured"""
    print("Testing WebDAV route configuration...")

    try:
        from tornado.web import FallbackHandler
        from tornado.wsgi import WSGIContainer
        from webserver.webdav.server import create_webdav_app

        # Mock objects for testing
        class MockCache:
            def field_metadata(self):
                return {}

        class MockSession:
            def __call__(self):
                return self
            def query(self, model):
                return self
            def filter(self, *args):
                return self
            def first(self):
                return None

        # Try to create the WebDAV app
        cache = MockCache()
        session = MockSession()

        print("Creating WebDAV app...")
        webdav_app = create_webdav_app(cache, session)
        print("✓ WebDAV app created successfully")

        print("Creating WSGI container...")
        webdav_container = WSGIContainer(webdav_app)
        print("✓ WSGI container created successfully")

        print("Creating route configuration...")
        webdav_routes = [
            (r"/books/?(.*)", FallbackHandler, dict(fallback=webdav_container)),
        ]
        print(f"✓ Route configured: {webdav_routes[0][0]}")

        print("\n" + "="*60)
        print("✓ WebDAV routes are properly configured!")
        print("="*60)
        print("\nRoute pattern: /books/?(.*)")
        print("Handler: FallbackHandler -> WSGIContainer -> WsgiDAVApp")
        print("\nThis route should match:")
        print("  - http://server:port/books")
        print("  - http://server:port/books/")
        print("  - http://server:port/books/Custom%20Categories")
        print("  - etc.")

        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_webdav_routes()
    sys.exit(0 if success else 1)

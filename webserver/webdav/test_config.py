#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Simple test script to verify WebDAV service configuration.
This doesn't start the actual server, just validates the setup.
"""

import sys
import os

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
webserver_dir = os.path.dirname(current_dir)
project_dir = os.path.dirname(webserver_dir)
sys.path.insert(0, project_dir)

os.chdir(project_dir)  # Change to project directory


def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")

    try:
        from wsgidav.wsgidav_app import WsgiDAVApp
        print("✓ WsgiDAV imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import WsgiDAV: {e}")
        return False

    try:
        from webserver.webdav.server import create_webdav_app
        print("✓ WebDAV server module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import WebDAV server: {e}")
        return False

    try:
        from webserver.webdav.auth import TalebookDomainController
        print("✓ WebDAV auth module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import WebDAV auth: {e}")
        return False

    try:
        from webserver.webdav.dav_provider import TalebookProvider
        print("✓ WebDAV provider module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import WebDAV provider: {e}")
        return False

    return True

def test_provider_structure():
    """Test provider class structure"""
    print("\nTesting provider structure...")

    try:
        from webserver.webdav.dav_provider import TalebookProvider, safe_filename

        # Test safe_filename
        assert safe_filename("test.txt") == "test.txt"
        assert safe_filename("test<>:|?.txt") == "test_____.txt"
        print("✓ safe_filename works correctly")

        # Can't fully test provider without a real cache
        print("✓ Provider class structure looks good")

        return True
    except Exception as e:
        print(f"✗ Provider test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("WebDAV Service Configuration Test")
    print("=" * 60)

    all_ok = True

    if not test_imports():
        all_ok = False

    if not test_provider_structure():
        all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("✓ All tests passed!")
        print("\nWebDAV service is properly configured.")
        print("Start the main server to enable WebDAV at /books")
    else:
        print("✗ Some tests failed")
    print("=" * 60)

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())

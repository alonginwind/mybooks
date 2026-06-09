"""
测试封面图片下载。
策略一：requests + 完整 headers（含解析 JS 挑战后的 cookie）
策略二：subprocess 调用系统 curl（已知可用，作为 fallback）
"""

import os
import re
import subprocess
import requests


TEST_URL = "https://img9.doubanio.com/view/subject/l/public/s35497266.jpg"
OUT_DIR = "out"
FILENAME = "s35497266_test.jpg"

CURL_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Priority": "u=0, i",
    "Referer": "https://search.douban.com/book/subject_search?search_text=%E5%8F%8C%E5%A4%A9%E8%87%B3&cat=1001",
    "Sec-Ch-Ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
}


def _parse_js_cookies(html: str) -> dict:
    """
    解析豆瓣 CDN 的 JS 反爬挑战，提取 __tst_status 和 EO_Bot_Ssid。
    JS 中的数值均为硬编码，直接用正则提取后计算。
    """
    cookies = {}

    # 提取 __tst_status = a(0) 的值：WTKkN + bOYDu + wyeCN
    m = re.search(r'WTKkN\s*:\s*(\d+)', html)
    wt = int(m.group(1)) if m else 0
    m = re.search(r'bOYDu\s*:\s*(\d+)', html)
    bo = int(m.group(1)) if m else 0
    m = re.search(r'wyeCN\s*:\s*(\d+)', html)
    wy = int(m.group(1)) if m else 0
    if wt or bo or wy:
        cookies["__tst_status"] = str(wt + bo + wy)

    # 提取 EO_Bot_Ssid 的值（hardcoded 数字，紧跟在 "EO_Bot_Ssid=" 附近）
    m = re.search(r'iTyzs\s*\([^,]+,\s*(\d+)\)', html)
    if m:
        cookies["EO_Bot_Ssid"] = m.group(1)

    return cookies


def download_with_requests(url: str, save_path: str) -> bool:
    print("[requests] 尝试直接下载...")
    session = requests.Session()
    resp = session.get(url, headers=CURL_HEADERS, timeout=10)

    content_type = resp.headers.get("Content-Type", "")
    print(f"  Content-Type: {content_type}  Size: {len(resp.content)} bytes")

    # 如果拿到 JS 挑战，解析 cookie 后重试
    if "text/html" in content_type or resp.content[:4] != b'\xff\xd8\xff\xe0' and b"<script" in resp.content[:512]:
        print("  检测到 JS 挑战，尝试解析 cookie 后重试...")
        cookies = _parse_js_cookies(resp.text)
        print(f"  解析到 cookies: {cookies}")
        if cookies:
            resp = session.get(url, headers=CURL_HEADERS, cookies=cookies, timeout=10)
            content_type = resp.headers.get("Content-Type", "")
            print(f"  重试 Content-Type: {content_type}  Size: {len(resp.content)} bytes")

    if resp.content[:3] in (b'\xff\xd8\xff', b'\x89PN') or "image" in content_type:
        with open(save_path, "wb") as f:
            f.write(resp.content)
        print(f"  [OK] 保存到 {save_path}")
        return True

    # 保存调试内容
    with open(save_path + ".debug.html", "wb") as f:
        f.write(resp.content)
    print(f"  [FAIL] 非图片内容，已保存调试文件: {save_path}.debug.html")
    return False


def download_with_curl(url: str, save_path: str) -> bool:
    print("[curl] 使用系统 curl 下载...")
    cmd = [
        "curl", "-L", "-o", save_path,
        "-H", f"Accept: {CURL_HEADERS['Accept']}",
        "-H", f"Accept-Language: {CURL_HEADERS['Accept-Language']}",
        "-H", "Cache-Control: no-cache",
        "-H", "Pragma: no-cache",
        "-H", f"Referer: {CURL_HEADERS['Referer']}",
        "-H", f"Sec-Ch-Ua: {CURL_HEADERS['Sec-Ch-Ua']}",
        "-H", "Sec-Ch-Ua-Mobile: ?0",
        "-H", f"Sec-Ch-Ua-Platform: {CURL_HEADERS['Sec-Ch-Ua-Platform']}",
        "-H", "Sec-Fetch-Dest: document",
        "-H", "Sec-Fetch-Mode: navigate",
        "-H", "Sec-Fetch-Site: cross-site",
        "-H", "Sec-Fetch-User: ?1",
        "-H", "Upgrade-Insecure-Requests: 1",
        "-H", f"User-Agent: {CURL_HEADERS['User-Agent']}",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(save_path):
        size = os.path.getsize(save_path)
        print(f"  [OK] 保存到 {save_path}  ({size} bytes)")
        return True
    print(f"  [FAIL] curl 退出码 {result.returncode}: {result.stderr}")
    return False


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 60)
    ok = download_with_requests(TEST_URL, os.path.join(OUT_DIR, "requests_" + FILENAME))

    print()
    print("=" * 60)
    download_with_curl(TEST_URL, os.path.join(OUT_DIR, "curl_" + FILENAME))

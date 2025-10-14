#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from pathlib import Path

# http://192.168.31.179:12121/files
# http://192.168.31.230:9310/files


def upload_file_to_duokan(file_path, server_url="http://192.168.31.179:12121/files"):
    """
    上传文件到多看服务器

    Args:
        file_path (str): 要上传的文件路径
        server_url (str): 服务器URL

    Returns:
        dict: 包含上传结果的字典

    Raises:
        ValueError: 当文件扩展名不是epub或pdf时
        FileNotFoundError: 当文件不存在时
        requests.exceptions.RequestException: 当网络请求失败时
    """

    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 获取文件信息
    file_path = Path(file_path)
    file_extension = file_path.suffix.lower()
    filename = file_path.name

    # 检查文件扩展名
    if file_extension not in ['.epub', '.pdf']:
        raise ValueError(f"不支持的文件格式: {file_extension}, 只支持 .epub 和 .pdf 文件")

    # 确定Content-Type
    if file_extension == '.epub':
        content_type = 'application/epub+zip'
    elif file_extension == '.pdf':
        content_type = 'application/pdf'

    try:
        # 准备文件数据
        with open(file_path, 'rb') as file:
            files = {
                'newfile': (filename, file, content_type)
            }

            # 发送POST请求
            response = requests.post(
                server_url,
                files=files,
                timeout=60
            )

            # 检查响应状态
            response.raise_for_status()

            # 返回结果
            result = {
                'success': True,
                'status_code': response.status_code,
                'filename': filename,
                'file_size': file_path.stat().st_size,
                'content_type': content_type
            }

            # 尝试解析JSON响应
            try:
                result['response_data'] = response.json()
            except ValueError:
                result['response_text'] = response.text

            return result

    except requests.exceptions.Timeout:
        raise requests.exceptions.RequestException(f"上传超时: {file_path}")

    except requests.exceptions.ConnectionError:
        raise requests.exceptions.RequestException(f"连接服务器失败: {server_url}")

    except requests.exceptions.HTTPError as e:
        raise requests.exceptions.RequestException(f"HTTP错误: {e.response.status_code} - {e.response.text}")

    except Exception as e:
        raise requests.exceptions.RequestException(f"上传失败: {str(e)}")


def main():
    """主函数 - 处理命令行参数并上传文件"""
    import sys

    if len(sys.argv) != 2:
        print("用法: python test_duokan_upload.py <文件路径>")
        print("示例: python test_duokan_upload.py /path/to/book.epub")
        return

    file_path = sys.argv[1]

    try:
        print(f"开始上传文件: {file_path}")
        result = upload_file_to_duokan(file_path)

        print("上传成功!")
        print(f"文件名: {result['filename']}")
        print(f"文件大小: {result['file_size']} bytes")
        print(f"Content-Type: {result['content_type']}")
        print(f"HTTP状态码: {result['status_code']}")

        if 'response_data' in result:
            print(f"服务器响应: {result['response_data']}")
        elif 'response_text' in result:
            print(f"服务器响应: {result['response_text']}")

    except ValueError as e:
        print(f"参数错误: {e}")
    except FileNotFoundError as e:
        print(f"文件错误: {e}")
    except requests.exceptions.RequestException as e:
        print(f"网络错误: {e}")
    except Exception as e:
        print(f"未知错误: {e}")


if __name__ == "__main__":
    main()

"""
格式精简工具

遍历书库中所有书籍，当一本书存在多个格式文件时，仅保留用户指定要保留的格式，
删除其余已存在的格式文件，以节省书库空间。
"""
import logging
import os
import time
import traceback
from typing import Callable, List, Optional

from webserver.i18n import _
from webserver.services import AsyncService
from webserver.services.background_service import BackgroundService, BackgroundTask
from webserver.toolbox.base_tool import BaseTool


class FormatsPruningTool(BaseTool):
    """遍历所有书籍，按指定的保留规则清理多余的格式文件。"""

    service_item_name = "格式精简"

    # 前端可选的保留格式项 -> 对应的实际 Calibre 格式名集合（大写）
    FORMAT_GROUPS = {
        "pdf": {"PDF"},
        "epub": {"EPUB"},
        "azw3_mobi": {"AZW3", "MOBI"},
        "txt": {"TXT"},
        "docx": {"DOCX"},
    }

    _last_task_id: Optional[int] = None

    @staticmethod
    def info() -> dict:
        return {
            "tool_id": "formats_pruning",
            "name": "格式精简",
            "description": "遍历书库中所有书籍，当书籍存在多个格式文件时，仅保留指定格式并清理其余格式以节省空间",
            "revision": "0.1.0",
            "author": "MyBooks",
            "publish_date": "2026-06-08",
        }

    @classmethod
    def resolve_keep_formats(cls, keep_keys: List[str]) -> set:
        """将前端选项 key 列表转换为实际的 Calibre 格式名集合（大写）。"""
        keep = set()
        for key in keep_keys:
            keep |= cls.FORMAT_GROUPS.get(key, set())
        return keep

    @classmethod
    def is_running(cls) -> bool:
        task = cls.get_last_task()
        return bool(task and task.get("status") == BackgroundTask.STATUS_RUNNING)

    @classmethod
    def get_last_task(cls) -> Optional[dict]:
        if cls._last_task_id is None:
            return None
        return BackgroundService().get_task(cls._last_task_id)

    @AsyncService.register_service
    def prune(
        self,
        keep_keys: List[str],
        user_id: int,
        callback: Optional[Callable[[int], None]] = None,
    ) -> Optional[dict]:
        """异步遍历所有书籍，清理未被指定保留的已存在格式文件。

        :param keep_keys: 需要保留的格式选项 key 列表，取值范围见 :attr:`FORMAT_GROUPS` 的键
                           （如 ``["pdf", "epub", "azw3_mobi", "txt", "docx"]``）。
                           不允许传入全部 key（否则将无法清理任何格式）。
        :param user_id:   操作关联的用户 ID（保留字段，目前仅记录日志）。
        :param callback:  进度回调，参数为 0-100 的整数进度值。
        :return:          同步模式下返回统计 dict；异步模式下返回 None。
        """
        if len(set(keep_keys) & set(self.FORMAT_GROUPS)) >= len(self.FORMAT_GROUPS):
            raise ValueError(_("不能选择全部格式，请至少保留一种格式用于清理"))

        keep_formats = self.resolve_keep_formats(keep_keys)

        task_id = self.create_task(progress_data={"status": "starting"})
        FormatsPruningTool._last_task_id = task_id

        progress_callback = self.make_progress_callback(task_id, outer_callback=callback)

        total_checked = 0
        total_pruned_books = 0
        total_pruned_formats = 0
        error_message = None
        book_ids: List[int] = []

        try:
            book_ids = self.get_all_book_ids()
            total = len(book_ids)
            logging.info("[FormatsPruningTool] Total books to check: %d [uid:%d]", total, user_id)

            self.update_task_progress(
                task_id, 0,
                {"status": "running", "total": total, "checked": 0, "pruned_books": 0, "pruned_formats": 0},
            )

            for idx, book_id in enumerate(book_ids, start=1):
                try:
                    removed = self._prune_book(book_id, keep_formats)
                    if removed:
                        total_pruned_books += 1
                        total_pruned_formats += len(removed)
                except Exception as err:
                    logging.warning(
                        "[FormatsPruningTool] Failed to process book_id=%d: %s",
                        book_id, err,
                    )

                total_checked += 1
                progress = int(idx * 100 / total) if total else 100
                if total_checked % 20 == 0 or idx == total:
                    self.update_task_progress(
                        task_id, progress,
                        {
                            "status": "running",
                            "total": total,
                            "checked": total_checked,
                            "pruned_books": total_pruned_books,
                            "pruned_formats": total_pruned_formats,
                        },
                    )
                    if progress_callback:
                        progress_callback(progress)
                    time.sleep(0.1)

        except Exception as err:
            logging.error("[FormatsPruningTool] prune failed: %s", err)
            error_message = str(err)
            logging.error(traceback.format_exc())

        self.complete_task(task_id, error_message=error_message)
        if error_message is None:
            self.update_task_progress(
                task_id, 100,
                {
                    "status": "completed",
                    "total": len(book_ids),
                    "checked": total_checked,
                    "pruned_books": total_pruned_books,
                    "pruned_formats": total_pruned_formats,
                },
            )

        return {
            "total": len(book_ids) if error_message is None else total_checked,
            "checked": total_checked,
            "pruned_books": total_pruned_books,
            "pruned_formats": total_pruned_formats,
        }

    def _prune_book(self, book_id: int, keep_formats: set) -> List[str]:
        """检查单本书籍，删除不在保留集合中且文件实际存在的格式。

        书籍仅有单一格式时跳过；为避免书籍变成无格式可读，删除后至少保留一个格式。

        :return: 实际删除的格式名列表（大写）。
        """
        books = self.db.get_data_as_dict(ids=[book_id])
        if not books:
            return []

        book = books[0]
        fmts = [f.upper() for f in (book.get("available_formats") or [])]
        if len(fmts) <= 1:
            return []

        to_remove = []
        for fmt in fmts:
            if fmt in keep_formats:
                continue
            fpath = self.db.format_abspath(book_id, fmt, index_is_id=True)
            if fpath and os.path.exists(fpath):
                to_remove.append(fmt)

        if to_remove and len(to_remove) == len(fmts):
            to_remove.pop()

        if not to_remove:
            return []

        self.db.new_api.remove_formats({book_id: to_remove})
        logging.info(
            "[FormatsPruningTool] book_id=%d removed formats=%s",
            book_id, to_remove,
        )
        return to_remove

#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import errno
import hashlib
import os
import logging
import time
import traceback

from webserver.i18n import _
from sqlalchemy.exc import IntegrityError

from webserver import utils
from webserver.models import Item, ScanFile
from webserver.services import AsyncService
from webserver.services.autofill import AutoFillService
from webserver.constants import CALIBRE_COLUMN_BOOK_TYPE, CALIBRE_COLUMN_CATEGORY, CALIBRE_ERROR_FLAG
from webserver.constants import BOOK_TYPE_EBOOK, BOOK_TYPE_PHYSICAL
from webserver.services.background_service import BackgroundService, BackgroundTask
from webserver import loader

SCAN_EXT = ["azw", "azw3", "epub", "mobi", "pdf", "txt"]
CONF = loader.get_settings()


class ScanService(AsyncService):
    static_is_importing = False
    invalid_folder: set[str] = set()

    @staticmethod
    def is_importing():
        return ScanService.static_is_importing

    @staticmethod
    def get_invalid_folders():
        if ScanService.invalid_folder:
            logging.info(f"Invalid folders#0: {ScanService.invalid_folder}")
        return list(ScanService.invalid_folder)

    @staticmethod
    def os_walk_error_handler(e):
        if e.errno == errno.EACCES:
            logging.error(f"[IMPORT]权限不足，跳过目录: {e.filename}")
            ScanService.invalid_folder.add(e.filename)
        elif e.errno == errno.ENOENT:
            logging.error(f"[IMPORT]目录消失: {e.filename}")
        else:
            ScanService.invalid_folder.add(e.filename)
            logging.error(f"[IMPORT]访问目录时发生错误: {e.filename}, 错误码: {e.errno}")

    @staticmethod
    def _remove_imported_file(fpath):
        try:
            os.remove(fpath)
            logging.info(f"Removed imported file: {fpath}")
        except Exception as e:
            logging.error(f"Failed to remove imported file {fpath}: {e}")

    def save_or_rollback(self, row, session=None):
        session = session or self.session
        bid = "[ book-id=%s ]" % row.book_id if row.book_id else ""
        logging.info("update: status=%-5s, path=%s %s", row.status, row.path, bid)
        try:
            row.save()
            session.commit()
            return True
        except IntegrityError as err:
            logging.error("IntegrityError: Duplicate hash detected: %s, %s", row.hash, err)
        except Exception as err:
            logging.exception("save error: %s", err)
        session.rollback()
        return False

    def _collect_files(self, paths):
        """Collect file paths from dirs, direct file paths, or None/'all' (uses scan_upload_path)."""
        if paths is None or paths == "all":
            dirs = [CONF.get("scan_upload_path", "")]
        elif isinstance(paths, str):
            dirs = [paths]
        else:
            dirs = list(paths)

        filelist = []
        for p in dirs:
            if os.path.isfile(p):
                fmt = p.split(".")[-1].lower()
                if fmt in SCAN_EXT:
                    filelist.append(p)
            elif os.path.isdir(p):
                for dirpath, __, filenames in os.walk(p, onerror=ScanService.os_walk_error_handler):
                    for fname in filenames:
                        fmt = fname.split(".")[-1].lower()
                        if not fmt or fmt not in SCAN_EXT or fname.startswith('.'):
                            continue
                        fpath = os.path.join(dirpath, fname)
                        if os.path.isfile(fpath):
                            filelist.append(fpath)
            else:
                logging.warning("[IMPORT] Path not found: %s", p)
        return filelist

    @AsyncService.register_service
    def do_import(self, paths, user_id):
        if ScanService.static_is_importing:
            logging.error("Importing is running, please wait...")
            return

        ScanService.invalid_folder.clear()
        ScanService.static_is_importing = True
        start_time = time.time()

        filelist = self._collect_files(paths)
        logging.info("[IMPORT] Collected %d files in %.3f seconds", len(filelist), time.time() - start_time)
        if not filelist:
            logging.warning("[IMPORT] No valid files found in: %s", paths)
            ScanService.static_is_importing = False
            return

        task_id = None
        try:
            service_item = _("导入图书")
            task = BackgroundService().update_task(
                service_type=BackgroundTask.SERVICE_TYPE_SCAN,
                service_item=service_item,
                progress=0,
                progress_data={"stage": "importing", "total": len(filelist), "imported": 0}
            )
            task_id = task.id
        except Exception as e:
            logging.error(f"Failed to create background task: {e}")

        try:
            self.do_import_internal(filelist, user_id, task_id)
            if task_id:
                BackgroundService().complete_task(task_id=task_id)
            logging.info("[IMPORT] Completed")
        except Exception as err:
            if task_id:
                BackgroundService().complete_task(task_id=task_id, error_message=str(err))
            logging.error(f"[IMPORT] Failed: {err}")
            logging.error(traceback.format_exc())
        ScanService.static_is_importing = False

    def _compute_hash(self, fpath):
        """Compute partial sha256 for the file.
        < 10MB: first 4MB; >= 10MB: first 3MB + last 3MB.
        Returns (hash_str, None) on success, or (None, bad_reason) on error."""
        sha256 = hashlib.sha256()
        _MB = 1024 * 1024
        try:
            file_size = os.path.getsize(fpath)
            with open(fpath, "rb") as f:
                if file_size < 10 * _MB:
                    sha256.update(f.read(4 * _MB))
                else:
                    sha256.update(f.read(3 * _MB))
                    f.seek(-3 * _MB, 2)
                    sha256.update(f.read(3 * _MB))
            return "sha256:" + sha256.hexdigest(), None
        except FileNotFoundError:
            logging.error("[IMPORT] File not found: %s", fpath)
            return None, ScanFile.MISSED
        except PermissionError:
            logging.error("[IMPORT] Permission denied: %s", fpath)
            return None, ScanFile.PERMISSION
        except Exception as e:
            logging.error("[IMPORT] Error reading file %s: %s", fpath, e)
            return None, ScanFile.INVALID

    def do_import_internal(self, filelist, user_id, task_id=None):
        """Process a list of file paths: compute sha256, check duplicates, read metadata, import."""
        from calibre.ebooks.metadata.meta import get_metadata
        from calibre.ebooks.metadata.book.base import Metadata

        session = self.session
        import_id = int(time.time())
        scan_upload_path = os.path.realpath(CONF.get("scan_upload_path", ""))
        total_count = len(filelist)
        imported = []
        processed_paths: set[str] = set()
        batch_size = 20

        start_time = time.time()
        logging.info("[IMPORT] Start Phase 1 (hash + dedup) for %d files", total_count)

        # === Phase 1: compute sha256, dedup, create READY ScanFile records ===
        rows_to_process = []
        for index, fpath in enumerate(filelist):
            if task_id and total_count > 0 and index % 50 == 0:
                try:
                    BackgroundService().update_progress(
                        task_id=task_id,
                        progress=int(index * 50 / total_count),
                        progress_data={"stage": "importing", "total": total_count, "imported": 0}
                    )
                except Exception as e:
                    logging.error("[IMPORT] Failed to update phase-1 progress: %s", e)

            if not os.path.isfile(fpath):
                logging.warning("[IMPORT] Not a valid file, skip: %s", fpath)
                continue

            fname = os.path.basename(fpath)
            fmt = fpath.split(".")[-1].lower()
            if not fmt or fmt not in SCAN_EXT:
                logging.info("[IMPORT] Unsupported format [%s], skip: %s", fmt, fpath)
                continue

            real_fpath = os.path.realpath(fpath)
            if real_fpath in processed_paths:
                logging.info("[IMPORT] Already processed in this run, skip: %s", fpath)
                continue

            # Check already imported by path
            same_path_rows = session.query(ScanFile).filter(ScanFile.path == fpath).all()
            already_done = False
            for r in same_path_rows:
                if r.status == ScanFile.IMPORTED and self.db.get_data_as_dict(ids=[r.book_id]):
                    logging.info("[IMPORT] Already imported by path: %s", fpath)
                    already_done = True
                    break
            if already_done:
                continue

            hash_val, bad_reason = self._compute_hash(fpath)

            if bad_reason:
                row = ScanFile(fpath, "", import_id)
                row.status = bad_reason
                self.save_or_rollback(row, session)
                continue

            processed_paths.add(real_fpath)

            # Check already imported by hash
            for hash_row in session.query(ScanFile).filter(ScanFile.hash == hash_val):
                if hash_row.status == ScanFile.IMPORTED and self.db.get_data_as_dict(ids=[hash_row.book_id]):
                    logging.info("[IMPORT] Already imported by hash: %s", fpath)
                    already_done = True
                    break
            if already_done:
                continue

            # Create or reuse ScanFile record
            if same_path_rows:
                row = same_path_rows[0]
                row.hash = hash_val
                row.import_id = import_id
            else:
                # Remove non-imported old records with same hash to avoid unique constraint violation
                session.query(ScanFile).filter(ScanFile.hash == hash_val).delete(synchronize_session=False)
                session.flush()
                row = ScanFile(fpath, hash_val, import_id)
            row.status = ScanFile.READY
            if self.save_or_rollback(row, session):
                rows_to_process.append(row)

        total_to_process = len(rows_to_process)
        logging.info("[IMPORT] Phase 1 done: %d files queued for import", total_to_process)

        # === Phase 2: read metadata and import books ===
        for index, row in enumerate(rows_to_process):
            if task_id and total_to_process > 0:
                try:
                    BackgroundService().update_progress(
                        task_id=task_id,
                        progress=50 + int(index * 50 / total_to_process),
                        progress_data={"stage": "importing", "total": total_to_process, "imported": len(imported)}
                    )
                except Exception as e:
                    logging.error("[IMPORT] Failed to update phase-2 progress: %s", e)

            fpath = row.path
            fname = os.path.basename(fpath)
            fmt = fpath.split(".")[-1].lower()
            start_time = time.time()
            logging.info("[IMPORT] Processing [%d/%d]: %s", index + 1, total_to_process, fpath)

            # Skip metadata reading when title/author are derived from filename
            skip_metadata = (fmt == "txt") or (fmt == "pdf" and CONF.get("PDF_TILE_WITH_FILE_NAME", False))
            if skip_metadata:
                title = utils.remove_zlibrary_suffix(fname.replace("." + fmt, ""))
                mi = Metadata(title, [_(u"佚名")])
                logging.info("[IMPORT] Skipped metadata read for %s: %s", fmt, repr(title))
            else:
                # Read metadata
                try:
                    with open(fpath, "rb") as stream:
                        mi = get_metadata(stream, stream_type=fmt, use_libprs_metadata=True)
                        mi.title = utils.super_strip(mi.title)
                        mi.authors = [utils.super_strip(s) for s in mi.authors]
                    logging.info("[IMPORT] Metadata read [%.3fs]: %s", time.time() - start_time, repr(mi.title))
                except Exception as e:
                    logging.error("[IMPORT] Error reading metadata from %s: %s", fpath, e)
                    row.status = ScanFile.INVALID
                    self.save_or_rollback(row, session)
                    continue

                if mi.title and mi.title == CALIBRE_ERROR_FLAG:
                    logging.error("[IMPORT] Failed to get metadata for %s", fpath)
                    row.status = ScanFile.INVALID
                    row.title = None
                    self.save_or_rollback(row, session)
                    continue

                # Normalize title/author for pdf (PDF_TILE_WITH_FILE_NAME=False)
                if fmt == "pdf":
                    title_ = mi.title.strip() if mi.title else ""
                    if not title_ or title_.find(_(u"下载工具")) >= 0 or title_ == "SSReader Print.":
                        mi.title = utils.remove_zlibrary_suffix(fname.replace("." + fmt, ""))
                    else:
                        mi.title = title_
                    if mi.authors is None or len(mi.authors) == 0 or mi.authors[0].lower() == "unknown":
                        mi.authors = [_(u"佚名")]

            row.title = mi.title
            row.author = mi.authors[0] if mi.authors else mi.author_sort
            row.publisher = mi.publisher
            row.tags = ", ".join(mi.tags)

            # Check duplicates and import
            try:
                ids = self.db.books_with_same_title(mi)
                existed_ebook = False
                logging.info("[IMPORT] Same title book ids: %s for file: %s", ids, fpath)
                if ids:
                    row.book_id = 0
                    for bid in ids:
                        b = self.db.get_metadata(bid, index_is_id=True)
                        if b.get(CALIBRE_COLUMN_BOOK_TYPE, BOOK_TYPE_EBOOK) == BOOK_TYPE_PHYSICAL:
                            continue
                        existed_ebook = True
                        row.book_id = bid
                        if fmt.upper() in b.formats:
                            row.status = ScanFile.EXIST
                            break
                    if existed_ebook and row.status != ScanFile.EXIST:
                        logging.info("[IMPORT] Adding format %s to existing book %d", fmt, row.book_id)
                        self.db.add_format(row.book_id, fmt.upper(), fpath, True)
                        row.status = ScanFile.IMPORTED

                if not existed_ebook:
                    logging.info("[IMPORT] Importing new book [%s] from %s", repr(mi.title), fpath)
                    mi.title_sort = utils.get_title_sort(mi.title)
                    row.book_id = self.db.import_book(mi, [fpath])
                    row.status = ScanFile.IMPORTED
                    logging.info("[IMPORT] Calibre import done, book_id=%d [%.3fs]", row.book_id, time.time() - start_time)

                    item = Item()
                    item.book_id = row.book_id
                    item.collector_id = user_id
                    item.src_path = fpath
                    try:
                        item.save()
                        imported.append(row.book_id)
                    except Exception as err:
                        logging.error("[IMPORT] save link error: %s", err)

                    if CONF.get("IMPORT_CATEGORY_WITH_FOLDER", False):
                        rel = os.path.relpath(os.path.realpath(fpath), scan_upload_path)
                        first_dir = rel.split(os.sep)[0] if os.sep in rel else ""
                        if first_dir and len(first_dir) < 10 and not any(c in first_dir for c in ',:;|/\\\'"\t '):
                            try:
                                self.db.new_api.set_field(CALIBRE_COLUMN_CATEGORY, {row.book_id: first_dir})
                                logging.info("[IMPORT] Set category '%s' for book_id=%d", first_dir, row.book_id)
                            except Exception as cat_err:
                                logging.warning("[IMPORT] Failed to set category for book_id=%d: %s", row.book_id, cat_err)
                        else:
                            logging.warning("[IMPORT] Skipping category for '%s': invalid dir name", first_dir)

                if CONF.get("REMOVE_IMPORTED_FILE", False) and (not existed_ebook or row.status == ScanFile.EXIST):
                    self._remove_imported_file(fpath)
            except Exception as err:
                row.status = ScanFile.INVALID
                logging.error("[IMPORT] Failed to process file %s: %s", fpath, err)
                logging.error(traceback.format_exc())

            self.save_or_rollback(row, session)
            logging.info("[IMPORT] File done, status=%s [total %.3fs]: %s", row.status, time.time() - start_time, fpath)

            # Batch commit every batch_size files
            if (index + 1) % batch_size == 0:
                try:
                    session.commit()
                    logging.info("[IMPORT] Batch committed at index %d", index + 1)
                except Exception as err:
                    logging.error("[IMPORT] Batch commit error: %s", err)
                    session.rollback()
                time.sleep(0.1)

        # Final commit
        try:
            session.commit()
            logging.info("[IMPORT] Final commit completed")
        except Exception as err:
            logging.error("[IMPORT] Final commit error: %s", err)
            session.rollback()

        if task_id:
            try:
                BackgroundService().update_progress(
                    task_id=task_id,
                    progress=100,
                    progress_data={"stage": "completed", "total": total_to_process, "imported": len(imported)}
                )
            except Exception as e:
                logging.error("[IMPORT] Failed to update final progress: %s", e)

        logging.info("[IMPORT] Done. Total queued: %d, Imported: %d", total_to_process, len(imported))

        if imported:
            logging.info("[IMPORT] Starting auto-fill for %d imported books", len(imported))
            AutoFillService().auto_fill_all(imported)

    @AsyncService.register_service
    def do_rename_category(self, old_dir_path, new_dir_path, scan_upload_path):
        """目录重命名/移动后，将 src_path 在旧目录下的书籍分类更新为新目录对应的一级子目录名"""
        old_dir_path = os.path.realpath(old_dir_path)
        new_dir_path = os.path.realpath(new_dir_path)
        scan_upload_path = os.path.realpath(scan_upload_path)

        # 计算新分类名：新路径在 scan_upload_path 下的第一级子目录名
        try:
            rel = os.path.relpath(new_dir_path, scan_upload_path)
        except ValueError:
            logging.warning("[RENAME DIR] 新目录不在 scan_upload_path 下: %s", new_dir_path)
            return

        parts = rel.split(os.sep)
        new_category = parts[0] if parts else ""

        if not new_category or new_category in ('.', '..'):
            logging.warning("[RENAME DIR] 无效的分类名: %s", new_category)
            return
        if len(new_category) >= 10 or any(c in new_category for c in ',:;|/\'"\t '):
            logging.warning("[RENAME DIR] 分类名含非法字符或过长，跳过: '%s'", new_category)
            return

        # 查找 src_path 在旧目录下的所有 Item
        sep = os.sep
        session = self.session
        all_items = session.query(Item).all()
        affected = [
            item for item in all_items
            if item.src_path and (
                os.path.realpath(item.src_path) == old_dir_path or os.path.realpath(item.src_path).startswith(old_dir_path + sep)
            )
        ]

        if not affected:
            logging.info("[RENAME DIR] Not found books which src_path in '%s', no need to update", old_dir_path)
            return

        logging.info("[RENAME DIR] Found %d books，update category to '%s'", len(affected), new_category)
        for item in affected:
            try:
                self.db.new_api.set_field(CALIBRE_COLUMN_CATEGORY, {item.book_id: new_category})
                # 同步更新 src_path 为新路径，方便后续重命名链式追踪
                suffix = os.path.realpath(item.src_path)[len(old_dir_path):]
                item.src_path = new_dir_path + suffix
                logging.info("[RENAME DIR] book_id=%d category->%s, src_path->%s",
                             item.book_id, new_category, item.src_path)
            except Exception as e:
                logging.error("[RENAME DIR] Failed to update book_id=%d,: %s", item.book_id, e)

        try:
            session.commit()
            logging.info("[RENAME DIR] category updated successfully")
        except Exception as e:
            logging.error("[RENAME DIR] Failed to commit: %s", e)
            session.rollback()

    @AsyncService.register_service
    def do_moved_file(self, old_file_path, new_file_path, scan_upload_path):
        """文件重命名/移动后，将 src_path 在旧目录下的书籍分类更新为新目录对应的一级子目录名"""
        old_file_path = os.path.realpath(old_file_path)
        new_file_path = os.path.realpath(new_file_path)
        scan_upload_path = os.path.realpath(scan_upload_path)

        if os.path.isdir(new_file_path):
            logging.warning("[RENAME FILE] 路径是目录，跳过: %s", new_file_path)
            return

        # 计算新分类名：新路径在 scan_upload_path 下的第一级子目录名
        try:
            rel = os.path.relpath(new_file_path, scan_upload_path)
        except ValueError:
            logging.warning("[RENAME FILE] 新目录不在 scan_upload_path 下: %s", new_file_path)
            return

        parts = rel.split(os.sep)
        new_category = parts[0] if parts else ""

        if not new_category or new_category in ('.', '..'):
            logging.warning("[RENAME FILE] 无效的分类名: %s", new_category)
            return
        if len(new_category) > 10 or any(c in new_category for c in ',:;|/\'"\t '):
            logging.warning("[RENAME FILE] 分类名含非法字符或过长，跳过: '%s'", new_category)
            return

        session = self.session
        affected = session.query(Item).filter(Item.src_path == old_file_path).all()
        if not affected:
            # 尝试使用ScanFile表中的路径进行匹配，兼容之前未设置src_path的情况
            logging.info("[RENAME FILE] 在 Item 表中未找到 src_path 为 '%s' 的书籍，尝试在 ScanFile 表中查找", old_file_path)
            scan_files = session.query(ScanFile).filter(ScanFile.path == old_file_path).all()
            if scan_files:
                book_ids = [sf.book_id for sf in scan_files if sf.book_id]
                affected = session.query(Item).filter(Item.book_id.in_(book_ids)).all()
        if not affected:
            logging.info("[RENAME FILE] 未找到 src_path 为 '%s' 的书籍，无需更新", old_file_path)
            return

        logging.info("[RENAME FILE] Found %d books，update category to '%s'", len(affected), new_category)
        for item in affected:
            try:
                self.db.new_api.set_field(CALIBRE_COLUMN_CATEGORY, {item.book_id: new_category})
                item.src_path = new_file_path
                logging.info("[RENAME FILE] book_id=%d category->%s, src_path->%s", item.book_id, new_category, item.src_path)
            except Exception as e:
                logging.error("[RENAME FILE] Failed to update book_id=%d, %s", item.book_id, e)

        try:
            session.commit()
            logging.info("[RENAME FILE] Succeed to update categories")
        except Exception as e:
            logging.error("[RENAME FILE] Failed to commit: %s", e)
            session.rollback()

# -*- coding: UTF-8 -*-
import os
import re
import logging
from wsgidav.dav_provider import DAVProvider, DAVCollection, DAVNonCollection
from wsgidav.dav_error import DAVError, HTTP_NOT_FOUND, HTTP_FORBIDDEN

def safe_filename(filename):
    """Make filename safe for filesystem by removing/replacing special characters"""
    # Replace various problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove control characters
    filename = ''.join(c for c in filename if ord(c) >= 32)
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename.strip()

class TalebookResource(DAVNonCollection):
    def __init__(self, path, environ, book, cache):
        super(TalebookResource, self).__init__(path, environ)
        self.book = book
        self.cache = cache
        self.formats = ["epub", "azw3", "mobi", "pdf"]
        self.fmt = None
        self.file_path = None

        for f in self.formats:
            key = "fmt_%s" % f
            if self.book.get(key):
                self.fmt = f
                self.file_path = self.book[key]
                break

        # If no format found, but book exists, maybe just list it?
        # But for download, we need a file.
        self.title = safe_filename(self.book.get('title', 'Unknown'))
        self.id = self.book['id']
        self.ext = self.fmt or "txt"

    def get_display_name(self):
        # Format: ID.书名.ext
        name = "%d.%s.%s" % (self.id, self.title, self.ext)
        return name

    def get_content_length(self):
        if self.file_path and os.path.exists(self.file_path):
            return os.path.getsize(self.file_path)
        return 0

    def get_content_type(self):
        types = {
            "epub": "application/epub+zip",
            "azw3": "application/x-mobi8-ebook",
            "mobi": "application/x-mobipocket-ebook",
            "pdf": "application/pdf",
        }
        return types.get(self.fmt, "application/octet-stream")

    def get_content(self):
        if self.file_path and os.path.exists(self.file_path):
            return open(self.file_path, "rb")
        return b""

class VirtualCollection(DAVCollection):
    def __init__(self, path, environ, title, provider, children=None):
        super(VirtualCollection, self).__init__(path, environ)
        self.title = title
        self.provider = provider
        self.fixed_children = children  # List of DAVResource objects

    def get_display_name(self):
        return self.title

    def get_member_list(self):
        if self.fixed_children is not None:
            return self.fixed_children
        return self.get_dynamic_members()

    def get_member_names(self):
        """Return list of (direct) collection member names (utf-8 byte strings)."""
        members = self.get_member_list()
        return [m.name for m in members]

    def get_dynamic_members(self):
        return []

class BooksCollection(VirtualCollection):
    def __init__(self, path, environ, title, provider, book_ids):
        super(BooksCollection, self).__init__(path, environ, title, provider)
        self.book_ids = book_ids

    def get_dynamic_members(self):
        books = []
        # Fetch book metadata in batch might be better, but Calibre cache is efficient
        # self.provider.cache.get_metadata(ids)
        # However, data access is via cache (new_api)
        # attributes in cache usually: cache.field_metadata
        # We need cache.get_proxy_metadata or similar?
        # Actually in handlers/book.py: self.get_book(id) uses cache.
        # We can implement a helper in Provider.

        # NOTE: getting all metadata for thousands of books is slow.
        # Ideally we paginate or just fetch basic info.
        # But WebDAV PROPFIND usually asks for children.

        # cache.get_data_as_dict is useful
        try:
            items = self.provider.cache.get_data_as_dict(ids=list(self.book_ids))
            for item in items:
                books.append(TalebookResource(
                    os.path.join(self.path, f"{item['id']}. {item['title']}"),
                    self.environ,
                    item,
                    self.provider.cache
                ))
        except Exception as e:
            logging.error(f"Error fetching books for {self.path}: {e}")

        return books

class LetterCollection(VirtualCollection):
    def __init__(self, path, environ, letter, provider):
        super(LetterCollection, self).__init__(path, environ, letter, provider)
        self.letter = letter.upper()

    def get_pinyin_initial(self, text):
        """Get pinyin initial from Chinese text"""
        import opencc

        # Simple pinyin initial mapping for common Chinese characters
        # This is a simplified approach. For production, consider using pypinyin library
        try:
            # Convert to simplified Chinese first
            converter = opencc.OpenCC('t2s')  # Traditional to Simplified
            text = converter.convert(text)

            # For basic implementation, just check first character
            if not text:
                return 'A'

            first_char = text[0].upper()
            # If it's already ASCII, return it
            if first_char.isalpha():
                return first_char

            # For Chinese characters, we need more sophisticated mapping
            # This is a placeholder - in production you'd use pypinyin
            # For now, return 'A' for non-ASCII
            return 'A'
        except:
            return 'A'

    def get_dynamic_members(self):
        # For better performance, we'll just search books with title_sort starting with the letter
        # title_sort is usually in ASCII format
        try:
            # Search by title_sort (which is ASCII)
            query = f'title_sort:~^{self.letter}'
            ids = self.provider.cache.search(query)

            # If no results and letter is valid, try all books and filter
            if not ids and len(self.letter) == 1 and self.letter.isalpha():
                # Get all books and filter by first letter of title_sort
                all_ids = list(self.provider.cache.all_book_ids())
                filtered_ids = []

                # Batch fetch to improve performance
                for book_id in all_ids[:1000]:  # Limit for performance
                    try:
                        title_sort = self.provider.cache.field_for('title_sort', book_id)
                        if title_sort and title_sort[0].upper() == self.letter:
                            filtered_ids.append(book_id)
                    except:
                        continue

                ids = filtered_ids

            return BooksCollection(self.path, self.environ, self.letter, self.provider, ids).get_dynamic_members()
        except Exception as e:
            logging.error(f"Error searching books for letter {self.letter}: {e}")
            return []


class TalebookProvider(DAVProvider):
    def __init__(self, cache):
        super(TalebookProvider, self).__init__()
        self.cache = cache
        self.sections = ["Custom Categories", "Tags", "Authors", "All Books"]

    def get_resource_inst(self, path, environ):
        path = path.strip("/")
        if not path:
            return VirtualCollection("/", environ, "root", self, [
                VirtualCollection("/" + s, environ, s, self) for s in self.sections
            ])

        parts = path.split("/")
        section = parts[0]

        if section == "Custom Categories":
            return self.handle_custom(path, environ, parts)
        elif section == "Tags":
            return self.handle_tags(path, environ, parts)
        elif section == "Authors":
            return self.handle_authors(path, environ, parts)
        elif section == "All Books":
            return self.handle_all(path, environ, parts)

        return None

    def handle_custom(self, path, environ, parts):
        # Custom Categories generally refers to User Categories (tags) or #category column
        # The prompt says: "From custom category... show system category list... click to show books"
        # Since 'category' is a custom column usually in Talebook (#category)
        if len(parts) == 1:
            # List categories
            # Metadata for #category
            try:
                # We need to find if #category exists and list values.
                # In book.py: self.calibre_db.field_metadata['#category']
                cats = self.cache.get_categories()
                # cats is dict {field: values} or similar
                # actually cache.get_categories() returns keys of categories?
                # No, look at opds.py: categories = self.calibre_db.get_categories() -> dict of category items
                # But we want specific values for the '#category' field.
                # If '#category' is not in standard categories, we might need other way.
                # In helper: self.calibre_db_cache.get_field_unique_values('#category')? Wait, check methods.
                pass
            except:
                pass

            # For now, let's assume we use what OPDS does or similar.
            # But specific Requirement: "Custom Category" -> "Classification List"
            # It implies the '#category' user column.

            # Let's try to get all values for '#category'.
            # cache.get_categories() should contain it if it's a category.
            # or getAllCategories()

            children = []
            try:
                 # Check if #category exists
                if '#category' in self.cache.field_metadata:
                    # Retrieve values.
                    # cache.get_categories() returns a dict of categories.
                    # Custom columns are usually keys like '#category'
                    all_cats = self.cache.get_categories()
                    if '#category' in all_cats:
                         for cat in all_cats['#category']:
                             # cat is a Tag object usually, with .name
                             name = cat.name if hasattr(cat, 'name') else str(cat)
                             children.append(VirtualCollection(os.path.join(path, name), environ, name, self))
            except Exception as e:
                logging.error(f"Error getting categories: {e}")

            return VirtualCollection(path, environ, "Custom Categories", self, children)

        elif len(parts) == 2:
            # List books in category
            cat_name = parts[1]
            try:
                # ids = cache.get_books_for_category('#category', cat_name)
                # But 'get_books_for_category' might expect query name?
                # Alternative: search(f'#category:"={cat_name}"')
                ids = self.cache.search(f'#category:"={cat_name}"')
                return BooksCollection(path, environ, cat_name, self, ids)
            except Exception as e:
                logging.error(f"Error searching category {cat_name}: {e}")
                return None

        elif len(parts) == 3:
            # Book file
            # parts[2] is "ID. Title.ext"
            # We need to extract ID
            try:
                book_id = int(parts[2].split(".")[0])
                book = self.cache.get_data_as_dict(ids=[book_id])[0]
                return TalebookResource(path, environ, book, self.cache)
            except:
                return None

        return None

    def handle_tags(self, path, environ, parts):
        if len(parts) == 1:
            children = []
            try:
                for tag in self.cache.all_tags():
                    children.append(VirtualCollection(os.path.join(path, tag), environ, tag, self))
            except:
                pass
            return VirtualCollection(path, environ, "Tags", self, children)
        elif len(parts) == 2:
            tag_name = parts[1]
            try:
                ids = self.cache.search(f'tags:"={tag_name}"')
                return BooksCollection(path, environ, tag_name, self, ids)
            except:
                return None
        elif len(parts) == 3:
            try:
                book_id = int(parts[2].split(".")[0])
                book = self.cache.get_data_as_dict(ids=[book_id])[0]
                return TalebookResource(path, environ, book, self.cache)
            except:
                return None
        return None

    def handle_authors(self, path, environ, parts):
        if len(parts) == 1:
            children = []
            try:
                for author in self.cache.all_authors():
                     # Author might be tuple or string? cache.all_authors() returns list of strings usually
                     children.append(VirtualCollection(os.path.join(path, author), environ, author, self))
            except:
                pass
            return VirtualCollection(path, environ, "Authors", self, children)
        elif len(parts) == 2:
            author_name = parts[1]
            try:
                ids = self.cache.search(f'authors:"={author_name}"')
                return BooksCollection(path, environ, author_name, self, ids)
            except:
                pass
        elif len(parts) == 3:
            try:
                book_id = int(parts[2].split(".")[0])
                book = self.cache.get_data_as_dict(ids=[book_id])[0]
                return TalebookResource(path, environ, book, self.cache)
            except:
                pass
        return None

    def handle_all(self, path, environ, parts):
        if len(parts) == 1:
            # A-Z
            import string
            letters = string.ascii_uppercase
            children = [VirtualCollection(os.path.join(path, l), environ, l, self) for l in letters]
            return VirtualCollection(path, environ, "All Books", self, children)
        elif len(parts) == 2:
            letter = parts[1]
            return LetterCollection(path, environ, letter, self)
        elif len(parts) == 3:
            try:
                book_id = int(parts[2].split(".")[0])
                book = self.cache.get_data_as_dict(ids=[book_id])[0]
                return TalebookResource(path, environ, book, self.cache)
            except:
                pass
        return None

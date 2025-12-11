import logging
from functools import wraps
import os
import xml.etree.ElementTree as ET

class FileHandlerException(Exception):
    """exception for all file handler errors"""
    pass


class FileNotFound(FileHandlerException):
    """exception when opening a file that does not exist"""
    def __init__(self, path):
        super().__init__(f"File not found at path: {path}")


class FileCorruptedError(FileHandlerException):
    """file corruption exception"""
    def __init__(self, path, original_error):
        super().__init__(f"Problem with file '{path}'. Original error: {original_error}")


def logged(exception_class):
    """
    Parameterized decorator.
    :param exception_class: exception class for logging
    :return: decorator function
    """
    LOG_FILE = 'file.operations.txt'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    logger = logging.getLogger('FileLogger')
    logger.setLevel(logging.INFO)

    if not logger.hasHandlers():
        handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                result = func(self, *args, **kwargs)
                logger.info(f"'{self.file_path}' - method {func.__name__} completed.")
                return result
            except exception_class as e:
                error_message = (
                    f"ERROR: '{self.file_path}' - method {func.__name__} caused "
                    f"{e.__class__.__name__}: {e}"
                )
                logger.error(error_message)
                raise
        return wrapper
    return decorator

class XMLHandler:
    def __init__(self, file_path):
        """
        constructor checks for file existence, stores path
        :param file_path: path to XML file
        :raises FileNotFound: if the file does not exist at the specified path
        """
        self.file_path = file_path

        if not os.path.exists(file_path):
            raise FileNotFound(file_path)

        print(f"File handler created: {file_path}. The file exists")

    @logged(FileHandlerException)
    def read_file(self):
        """
        Reads and parses an XML file
        :return: root element
        """
        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
            return root

        except ET.ParseError as e:
            raise FileCorruptedError(self.file_path, f"Incorrect XML: {e}")
        except IOError as e:
            raise FileCorruptedError(self.file_path, f"Access/read error: {e}")

    @logged(FileHandlerException)
    def write_file(self, root_element):
        """
        Rewrite the XML file using the root element
        :param root_element: An ET.Element object that is the new document root.
        """
        try:
            tree = ET.ElementTree(root_element)
            tree.write(self.file_path, encoding="utf-8", xml_declaration=True)

        except IOError as e:
            raise FileCorruptedError(self.file_path, f"Write error: {e}")

    @logged(FileHandlerException)
    def append_to_file(self, new_element_tag, attributes=None, text_content=None):

        attributes = attributes if attributes is not None else {}
        root = self.read_file()

        new_element = ET.Element(new_element_tag, attributes)
        if text_content is not None:
            new_element.text = text_content

        root.append(new_element)

        self.write_file(root)


xml_content = """<?xml version="1.0" encoding="utf-8"?>
<settings>
    <param name="version">1.0</param>
</settings>"""

bad_content = "This is not valid XML data <tag_without_closing_tag"


def main():
    log_file_path = 'file.operations.txt'
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    try:
        with open('config.xml', 'w', encoding='utf-8') as f:
            f.write(xml_content)

        with open('bad.txt', 'w', encoding='utf-8') as f:
            f.write(bad_content)


        print("[TEST 1]: Successfully reading and appending an element...")
        xml_handler = XMLHandler('config.xml')

        print(">> Call read_file (Logged to file)")
        xml_handler.read_file()

        print(">> Call append_to_file (Logged to file)")
        xml_handler.append_to_file("data_item", attributes={"id": "1"}, text_content="New Value")

        new_root = xml_handler.read_file()
        print(f"Number of elements after adding: {len(new_root)}")

        try:
            print("[TEST 2]: Attempting to read malformed XML...")
            bad_handler = XMLHandler('bad.txt')
            bad_handler.read_file()

        except FileCorruptedError as e:
            print(f"Success: Caught {e.__class__.__name__}: {e}")

        for handler in logging.getLogger('FileLogger').handlers:
            handler.flush()

    except Exception as e:
        print(f"Critical error in test block execution: {e}")

if __name__ == "__main__":
    main()
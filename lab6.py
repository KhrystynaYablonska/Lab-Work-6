import logging
from functools import wraps
import os
import xml.etree.ElementTree as ET

if os.path.exists('file.operations.txt'):
    os.remove('file.operations.txt')

class FileHandlerException(Exception):
    """
    exception for all file handler errors
    """
    pass


class FileNotFound(FileHandlerException):
    """
    exception when opening a file that does not exist
    """

    def __init__(self, path):
        super().__init__(f"Файл не знайдено за шляхом: {path}")


class FileCorruptedError(FileHandlerException):
    """
    file corruption exception
    """

    LOG_FILE = 'file.operations.txt'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    def __init__(self, path, original_error):
        super().__init__(f"Проблема з файлом '{path}'. Оригінальна помилка: {original_error}")


def setup_logger(mode):
    """
    налаштовуєм логер відповідно до режиму
    :param mode: console або file
    :return: об'єкт логера, готовий до використання
    """

    logger = logging.getLogger('FileLogger')
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    if mode == 'console':
        handler = logging.StreamHandler()
    handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')

    formatter = logging.Formatter(LOG_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def logged(exception_class, mode):
    """
    Параметризований декоратор.
    :param exception_class: клас винятку для логування
    :param mode: режим логування
    :return: функція-декоратор
    """

    logger = setup_logger(mode)

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                result = func(self, *args, **kwargs)
                logger.info(f"'{self.file_path}' - Метод {func.__name__} виконано.")
                return result
            except exception_class as e:
                error_message = (
                    f"ПОМИЛКА: '{self.file_path}' - Метод {func.__name__} викликав "
                    f"{e.__class__.__name__}: {e}"
                )
                logger.error(error_message)
                raise

        return wrapper

    return decorator


class XMLHandler:
    def __init__(self, file_path):
        """
        конструктор перевіряє існування файлу, зберігає шлях
        :param file_path: шлях до XML-файлу
        :raises FileNotFound: якщо файл не існує за вказаним шляхом
        """
        self.file_path = file_path

        if not os.path.exists(file_path):
            raise FileNotFound(file_path)

        print(f"Створено обробник для файлу: {file_path}. Файл існує")

    @logged(FileHandlerException, 'console')
    def read_file(self):
        """
        Читає та парсить XML-файл
        :return: кореневий елемент
        """
        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
            return root

        except ET.ParseError as e:
            raise FileCorruptedError(self.file_path, f"Некоректний XML: {e}")
        except IOError as e:
            raise FileCorruptedError(self.file_path, f"Помилка доступу/читання: {e}")

    @logged(FileHandlerException, "file")
    def write_file(self, root_element):
        """
        Перезаписуємо XML-файл, використовуючи кореневий елемент
        :param root_element: Об'єкт ET.Element, що є новим коренем документа.
        """
        try:
            tree = ET.ElementTree(root_element)
            tree.write(self.file_path, encoding="utf-8", xml_declaration=True)

        except IOError as e:
            raise FileCorruptedError(self.file_path, f"Помилка запису: {e}")

    @logged(FileHandlerException, "file")
    def append_to_file(self, new_element_tag, attributes=None, text_content=None):
        """
        Додаємо новий елемент до кореня поточного XML-документа.
        """
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

try:
    with open('config.xml', 'w', encoding='utf-8') as f:
        f.write(xml_content)

    with open('bad.txt', 'w', encoding='utf-8') as f:
        f.write(bad_content)


    try:
        print("\n[ТЕСТ 1]: Спроба відкрити неіснуючий файл...")
        handler = XMLHandler("non_existent_file.xml")
    except FileHandlerException as e:
        print(f"Успіх: Зловлено виняток {e.__class__.__name__}: {e}")

    print("\n[ТЕСТ 2]: Успішне читання та дописування елемента...")
    xml_handler = XMLHandler('config.xml')

    print(">> Виклик read_file (Логується в консоль)")
    xml_handler.read_file()

    print(">> Виклик append_to_file (Логується в консоль + у файл)")
    xml_handler.append_to_file("data_item", attributes={"id": "1"}, text_content="New Value")

    new_root = xml_handler.read_file()
    print(f"Кількість елементів після дописування: {len(new_root)}")

    try:
        print("\n[ТЕСТ 3]: Спроба читання некоректного XML...")
        bad_handler = XMLHandler('bad.txt')
        bad_handler.read_file()

    except FileCorruptedError as e:
        print(f"Успіх: Зловлено {e.__class__.__name__}: {e}")
    except FileNotFound:
        pass

    for handler in logging.getLogger('FileLogger').handlers:
        handler.flush()

    print(f"\n--- ВМІСТ ЛОГ-ФАЙЛУ (file.operations.txt) ---")
    if os.path.exists('file.operations.txt'):
        with open('file.operations.txt', 'r', encoding='utf-8') as f:
            print(f.read())
    else:
        print("Лог-файл не було створено!")

except Exception as e:
    print(f"Критична помилка виконання тестового блоку: {e}")
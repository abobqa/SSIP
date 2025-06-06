import socket
import threading
import os
from datetime import datetime

# --- НАСТРОЙКИ СЕРВЕРА ---
# Мы вынесли настройки в константы для удобства.
# Это частично выполняет дополнительное задание о файле настроек.
HOST = 'localhost'  # Адрес для привязки. 'localhost' или '127.0.0.1'
PORT = 8080         # Порт для прослушивания.
WEB_ROOT = 'www'    # Название папки с файлами сайта.
LOG_FILE = 'server.log' # Файл для логирования запросов.

def log_request(addr, path, status_code):
    """Функция для записи логов в файл."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{now}] {addr[0]}:{addr[1]} - запросил '{path}' - статус {status_code}\n"
    with open(LOG_FILE, 'a') as f:
        f.write(log_message)
    print(log_message, end='') # Также выводим в консоль для наглядности

def handle_client(conn, addr):
    """
    Эта функция будет выполняться в отдельном потоке для каждого клиента.
    Она обрабатывает запрос и отправляет ответ.
    """
    print(f"Новое подключение от {addr}")

    try:
        # Принимаем данные от клиента (запрос)
        request_data = conn.recv(8192)
        if not request_data:
            # Если запрос пустой, ничего не делаем
            return

        # Декодируем запрос из байтов в строку
        request = request_data.decode('utf-8')

        # --- Парсинг (разбор) HTTP-запроса ---
        # Нас интересует только первая строка, например: "GET /index.html HTTP/1.1"
        first_line = request.split('\n')[0]
        method, path, version = first_line.split(' ')

        # Если запрошен корень сайта "/", отдаем index.html
        if path == '/':
            path = '/index.html'

        # Формируем полный путь к запрашиваемому файлу
        # os.path.join - безопасный способ соединения путей для разных ОС
        # path.lstrip('/') - убираем начальный слэш, чтобы join сработал корректно
        filepath = os.path.join(WEB_ROOT, path.lstrip('/'))

        # --- Проверка файла и формирование ответа ---
        if os.path.isfile(filepath):
            # Если файл существует, читаем его
            with open(filepath, 'rb') as f: # 'rb' - читаем в бинарном режиме, это важно для картинок и др.
                body = f.read()

            # Определяем Content-Type по расширению файла (упрощенный вариант)
            content_type = 'text/html'
            if filepath.endswith('.css'):
                content_type = 'text/css'
            elif filepath.endswith('.js'):
                content_type = 'application/javascript'
            elif filepath.endswith('.jpg') or filepath.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif filepath.endswith('.png'):
                content_type = 'image/png'

            # Формируем успешный HTTP-ответ (200 OK)
            status_line = 'HTTP/1.1 200 OK\r\n'
            headers = [
                f'Content-Type: {content_type}',
                f'Content-Length: {len(body)}',
                'Server: MySimpleServer',
                'Connection: close', # Сообщаем браузеру, что закроем соединение после ответа
                '\r\n' # Пустая строка, отделяющая заголовки от тела
            ]
            response = status_line.encode('utf-8') + '\r\n'.join(headers).encode('utf-8') + body
            log_request(addr, path, 200)

        else:
            # Если файл не найден, готовим ответ 404 Not Found
            status_line = 'HTTP/1.1 404 Not Found\r\n'
            body = b"<html><body><h1>404 Not Found</h1></body></html>"
            headers = [
                'Content-Type: text/html',
                f'Content-Length: {len(body)}',
                'Server: MySimpleServer',
                'Connection: close',
                '\r\n'
            ]
            response = status_line.encode('utf-8') + '\r\n'.join(headers).encode('utf-8') + body
            log_request(addr, path, 404)

        # Отправляем сформированный ответ клиенту
        conn.sendall(response)

    except Exception as e:
        print(f"Ошибка при обработке клиента {addr}: {e}")
    finally:
        # В любом случае закрываем соединение с клиентом
        conn.close()
        print(f"Соединение с {addr} закрыто.")


def start_server():
    """Основная функция запуска сервера."""
    # Создаем TCP/IP сокет
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Эта опция позволяет переиспользовать порт сразу после закрытия сервера
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Привязываем сокет к адресу и порту
    try:
        sock.bind((HOST, PORT))
        print(f"Сервер запущен на http://{HOST}:{PORT}")
        print(f"Корневая папка сайта: '{os.path.abspath(WEB_ROOT)}'")
        print("Для остановки сервера нажмите Ctrl+C")
    except OSError as e:
        print(f"Ошибка: не удалось привязаться к порту {PORT}. {e}")
        return

    # Начинаем прослушивать входящие подключения
    sock.listen(5)

    # --- Основной цикл сервера ---
    while True:
        try:
            # Ожидаем нового подключения
            conn, addr = sock.accept()
            # Создаем новый поток для обработки клиента.
            # Это позволяет серверу одновременно принимать новые подключения,
            # пока старые еще обрабатываются.
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()
        except KeyboardInterrupt:
            # Если пользователь нажал Ctrl+C, выходим из цикла
            print("\nСервер останавливается...")
            break
        except Exception as e:
            print(f"Произошла ошибка в основном цикле: {e}")

    # Закрываем главный сокет
    sock.close()
    print("Сервер успешно остановлен.")

# Запускаем наш сервер
start_server()

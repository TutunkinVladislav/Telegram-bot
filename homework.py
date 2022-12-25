import json
import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from constants import ENDPOINT

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем доступность переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]) is False:
        return False


def send_message(bot, message):
    """Отправляем сообщение в Telegram."""
    try:
        logging.debug('Началась отправка сообщения в Telegram')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Сообщение успешно отправлено')
    except Exception as TelegramError:
        logging.error(
            f'Сообщение в Telegram не удалось отправить: {TelegramError}'
        )


def get_api_answer(timestamp):
    """Делаем запрос к API-сервису."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
    except Exception as error:
        logging.error(f'Ошибка при запросе к API-сервису: {error}')

    if response.status_code != HTTPStatus.OK:
        raise Exception(
            f'Код запроса не равен 200. Код запроса {response.status_code}'
        )
    try:
        return response.json()
    except json.decoder.JSONDecodeError:
        logging.error('Запрос не преобразован в формат json')


def check_response(response):
    """Проверяем ответ API на соответсвие."""
    logging.debug('Проверяется ответ сервера')
    if not isinstance(response, dict):
        raise TypeError('Ответ API по структуре данных не является словарём')
    homework = response.get('homeworks')
    try:
        return homework[0]
    except Exception as error:
        logging.error(f'API не возвращает необходимые значения: {error}')
    if not isinstance(homework, list):
        raise TypeError('Ответ API по ключу "homeworks" не является списком')


def parse_status(homework):
    """Извлекаем информацию о статусе работы.
    Возвращаем строку для отправки в Telegram.
    """
    if ('homework_name' or 'status') not in homework:
        raise KeyError('Отсутствует значение "homework_name" или "status"')
    if ('homework_name' or 'status') is None:
        raise TypeError('Значение "homework_name" или "status" вернуло None')
    if ('homework_name' or 'status') == '':
        raise TypeError(
            'Значение "homework_name" или "status" вернуло пустую строку'
        )
    try:
        status = homework.get('status')
        verdict = HOMEWORK_VERDICTS[status]
        homework_name = homework.get('homework_name')
        if status in HOMEWORK_VERDICTS:
            return (
                f'Изменился статус проверки работы '
                f'"{homework_name}". {verdict}'
            )
    except Exception as error:
        logging.error(
            f'Ошибка при получении информации о статусе работы: {error}'
        )
    if status not in HOMEWORK_VERDICTS:
        raise Exception(f'Неизвестный статус: {status}')


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
    )

    if check_tokens() is False:
        logging.critical('Отсутствует обязательная переменная окружения')
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    message_verdict = ''
    message_error = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if message != message_verdict:
                send_message(bot, message)
                message_verdict = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if message != message_error:
                send_message(bot, message)
                message_error = message

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

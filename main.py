# ПЛАН ПРОЕКТА
#  OK:запрос геолокации
#  OK:погода по клику
#  OK:погода по предложенному времени
#  OK:погода по указанному времени
#  OK:кнопка настроек
#  NO:показывать что надеть
#  OK:показывать котиков и собачек
#  OK:автоотправка сообщений
#  OK:отправка погоды одной функцией
#  OK:докстринги
#  OK:Красивый вывод сообщений
#  OK:логирование
#  OK:создание базы данных
#  OK:кнопка отключения оповещения
#  OK:кнопка новой геолокации
#  --:разбить по файлам
#  --:написать README


#-------------Импорты--------------

import os
import time
import schedule
import aioschedule
import asyncio
import datetime
import requests
import sqlite3
import logging


from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Text
from aiogram.types import Message, Location,  ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from datetime import datetime, date, timedelta

import aiogram.utils.markdown as md
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext

#-------------Настройки бота--------------


"""Настройка чат-бота"""
API_TOKEN = '5455050294:AAErOf5q80ZKp2Op5ETCaVt14ZQgxTeaUKE'
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
user_id = None

base_button = ReplyKeyboardMarkup(resize_keyboard=True).row(KeyboardButton(text='🐱'), KeyboardButton(text='🐶'), KeyboardButton(text='🦊')).row(KeyboardButton(text='Сегодня'),KeyboardButton(text='Завтра')).add(KeyboardButton(text='Настройки'))

base_button_msg = 'Добро пожаловать в основное меню! Вам доступны: \nКнопки 🐱🐶🦊 отвечают за отправку случайной картинки. \nКнопки "Сегодня" и "Завтра" покажут тебе соответствующую погоду. \nКнопка настроек позволит сменить геолокацию и активировать ежедневную отправку погоды.'

"""Все Токены"""
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEATHER_APP_ID = os.getenv('WEATHER_APP_ID')

"""Все URLs"""
URL_WEATHER = "http://api.openweathermap.org/data/2.5/weather"
URL_FORECAST = "http://api.openweathermap.org/data/2.5/forecast"
URL_CAT = 'https://api.thecatapi.com/v1/images/search'
URL_DOG = 'https://dog.ceo/api/breeds/image/random'
URL_FOX = 'https://randomfox.ca/floof'

#----------База данных-----------

# Функция для создания базы данных
def create_database():
    """ Создание базы данных. """
    if os.path.exists('users_database.db'):
        os.remove('users_database.db')
        logging.info("База данных удалена")
    else:
        logging.info("Файл базы данных не найден")
    # Создание БД    
    conn = sqlite3.connect('users_database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE users
                 (user_id INT NOT NULL,
                 user_name TEXT NOT NULL,
                 lat REAL NULL,
                 lon REAL NULL,
                 time_msg TEXT NULL);''')
    logging.info("База данных создана")
    conn.close()


async def create_user(user_id, user_name):
    """ Создаёт пользователя. """
    conn = sqlite3.connect('users_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, user_name)
        VALUES (?, ?)
    ''', (user_id, user_name))
    conn.commit()


async def update_geo_user(user_id, lat, lon):
    """ Обновляет геоданные пользователя. """
    conn = sqlite3.connect('users_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users
        SET lat=?, lon=?
        WHERE user_id=?
    ''', (lat, lon, user_id))
    conn.commit()


async def update_time_user(user_id, time_msg):
    """ Обновляет время оповещения пользователя. """
    conn = sqlite3.connect('users_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users
        SET time_msg=?
        WHERE user_id=?
    ''', (time_msg, user_id))
    conn.commit()


async def get_user(user_id):
    """ Чтение данных пользователя. """
    conn = sqlite3.connect('users_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
    return cursor.fetchone()


#-------------Кнопки--------------


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    """Обработка стартового сообщения."""
    """ При запуске бота сохраняет его данные в БД и отправляет текст приветствия в зависимости от наличия записи времени опевещения в БД. """
#   Логи о запуске бота и добавлении пользователя
    global user_id
    user_id = message.from_user.id
    user_name = message.from_user.username
    await create_user(user_id = user_id, user_name=user_name)
    logging.info(f'Пользователь добавлен: {user_name}')
    start_text = 'Привет! Я погодный бот. Я могу показать погоду и отправить тебе её в указанное тобой время! А так же показать тебе зверушек.\n'
    is_geo = 'Если Вам нужно обновить или изменить свою геолокацию, перейдите в настройки.'
    not_is_geo = 'Давай сперва узнаем, из какого ты города.'
    user = await get_user(user_id)
    if user[3] == None:
        await message.answer(start_text + not_is_geo, reply_markup=get_keyboard())
    else:
        await message.answer(start_text + is_geo, reply_markup=base_button)
   

@dp.message_handler(content_types = ['location'])
async def handle_location(message: types.Message):
   """Определение местоположения"""
   """Посредством встроенного интструмента Telegramm получает координаты пользователя и записывает в БД"""
   user_id = message.from_user.id
   lat = message.location.latitude
   lon = message.location.longitude
   await update_geo_user(user_id = user_id, lat = lat, lon = lon)
   user = await get_user(user_id)
   logging.info(f'Пользователь {user[1]} обновил геоданные на: {lat}, {lon}') 
   await message.answer(base_button_msg, reply_markup =base_button)


def get_keyboard():
   """Обработка кнопки геолокации"""
   keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
   button = types.KeyboardButton('Указать геолокацию', request_location = True)
   keyboard.add(button)
   return keyboard


@dp.message_handler(text=['Назад'])
async def settings_back(message: types.Message):
    """Выход на главную панель"""
    await message.answer(base_button_msg, reply_markup=base_button)


@dp.message_handler(text=['Настройки'])
async def settings(message: types.Message):
    """Выход на настройки"""
    user = await get_user(user_id)
    user_time = user[4]
    if user_time == None:
        button = KeyboardButton(text='Указать время ежедневного оповещения')
    else:
        button = KeyboardButton(text='Выключить ежедневное оповещение')
    markup = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton(text='Указать геолокацию', request_location = True)).add(button).add(KeyboardButton(text='Назад'))
    await message.answer("Для смены геолокации нажмите /start \nДля ежедневной отправки погоды выберете соответствующее меню", reply_markup=markup)


#-------------Отправка погоды--------------
     

@dp.message_handler(text=['Сегодня','Завтра'])
async def weather_man(message: types.Message):
    """ Функция отправки погоды по запросу. """
    msg_text = await weather(message.text)
    user = await get_user(user_id)
    logging.info(f'Пользователь {user[1]} запросил погоду')
    await message.answer(''. join(msg_text))
    
async def weather_auto():
    """ Функция отправки погоды по расписанию. """
    user = await get_user(user_id)
    logging.info(f'Пользователю {user[1]} отправлена погода по расписанию')
    msg_text = await weather()
    await bot.send_message(user_id, ''. join(msg_text))   
                                            
async def weather(day = 'Сегодня'):    
    """ Формирует сообщение о погоде. """
    user = await get_user(user_id)
    PARAMS_WEATHER = {'lat': user[2],'lon': user[3], 'units': 'metric', 'lang': 'ru', 'APPID': WEATHER_APP_ID}
    msg_weather = 'Прогноз погоды на:\n'
    try:
        res = requests.get(URL_FORECAST, params=PARAMS_WEATHER)
        first_day_month = 1
        if day == 'Сегодня':
            data = res.json()['list'][0:5]
        elif day == 'Завтра':
            data = res.json()['list'][6:13]
        time_shift = 0
        for i in data:
            date = datetime.strptime(i['dt_txt'], "%Y-%m-%d %H:%M:%S")
            real_date = datetime.strptime(i['dt_txt'], "%Y-%m-%d %H:%M:%S")+timedelta(seconds=time_shift)
            if first_day_month != real_date.day <= datetime.now().day:
                today_text = f'{emoji_time(real_date)}' +'Сегодня в'
            else:
                today_text = f'{emoji_time(real_date)}' +'Завтра в'
            w_time =  f'{real_date.hour}:00'
            w_temp =  '🌡Температура:' + '{0:+6.0f}'.format(i['main']['temp']) + '°'
            w_wind = '💨Ветер: '+ str(i['wind']['speed']) + ' м/с'
            w_feels = '🌡Ощущается как: ' + str(i['main']['feels_like']) + '°'
            w_desc = emoji_desc(i['weather'][0]['description'])
            msg_weather += (f' {today_text} {w_time}\n {w_temp}\n {w_feels}\n {w_wind}\n {w_desc}\n\n')
        return msg_weather
    except Exception as e:
        print("Ошибка отображения погоды:", e)
        pass      

def emoji_time(real_date):
     """ Подбирает необходмый emoji в зависимости от времни. """
     time = real_date.hour
     if time == 12 or time == 0:
         return '🕛'
     elif time == 15 or time == 3:
         return '🕒'
     elif time == 18 or time == 6:
         return '🕕'
     elif time == 21 or time == 9:
         return '🕘'

def emoji_desc(description):
    """ Возвращает отформатированное состояние погоды. """
    if description == 'ясно':
        return '☀️Ясно'
    elif description == 'переменная облачность':
        return '⛅️Переменная облачность️'
    elif description == 'небольшая облачность':
        return '⛅️Небольшая облачность️'
    elif description == 'пасмурно':
        return '☁Пасмурно'
    elif description == 'облачно с прояснениями':
        return '🌥Облачно с прояснениями'
    elif description == 'небольшой дождь':
        return '🌧Небольшой дождь'
    elif description == 'дождь':
        return '🌧Дождь'
    elif description == 'туман':
        return '🌫Туман'
    elif description == 'небольшой снег':
        return '🌨Небольшой снег'
    elif description == 'снег':
        return '🌨Снег'
    else:
        return '🔴' + description

#-------------Котики собачки--------------


@dp.message_handler(text=['🐱', '🐶', '🦊'])
async def send_image(message: types.Message):
    """ Присылает фотографию запрошенной зверушки. """
    user = await get_user(user_id)
    if message.text == '🐱':
        response = requests.get(URL_CAT).json()[0]
        text = 'url'
        logging.info(f'Пользователь {user[1]} запросил котиков')
    elif message.text == '🐶':
        response = requests.get(URL_DOG).json()
        text = 'message'
        logging.info(f'Пользователь {user[1]} запросил собачек')
    elif message.text == '🦊':
        response = requests.get(URL_FOX).json()
        text = 'image'
        logging.info(f'Пользователь {user[1]} запросил лисичек')
    await bot.send_photo(user_id, response.get(text))


#-------------Ввод времени--------------


@dp.message_handler(text='Указать время ежедневного оповещения')
async def specify_time(message: types.Message):
    """Установка времени оповещения"""
    button_1 = KeyboardButton(text='07:00')
    button_2 = KeyboardButton(text='08:00')
    button_3 = KeyboardButton(text='09:00')
    markup = ReplyKeyboardMarkup(resize_keyboard=True).row(button_1, button_2, button_3)
    await message.reply("Введите время в формате ЧЧ:ММ (например 07:30), в которое Вам будет присылаться ежедневное сообщение или используйте уже заготовленные варианты",reply_markup = markup)


# Включение ежедневного оповещения
@dp.message_handler()
async def save_message(message: types.Message):
    """Включение времени оповещения."""
    """ Проверяет введеный текст пользователем, если написано 'Выключить ежедневное оповещение' то отключает время оповещения, если указано время, то записывает его в БД, если время указано неверно, то указывает на это пользователю."""
    time_msg = message.text   
    user = await get_user(user_id)
    if time_msg != "Выключить ежедневное оповещение":
        try:
            new_time = datetime.strptime(time_msg, "%H:%M")
            logging.info(f'Пользователь {user[1]} изменил время оповещения на {time_msg}')
            await update_time_user(user_id, time_msg)
            await start_scheduler()
            await bot.send_message(message.from_user.id, f"Время установленно на {time_msg}", reply_markup = base_button)
        except ValueError:
            # Не забыть убрать принт
            print('oops')
            markup = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton(text='Указать время оповещения'))
            return await message.reply("Время указано неверно! Пожалуйста, попробуйте еще раз.", reply_markup = markup)
    else:
        time_msg = None
        await update_time_user(user_id, time_msg)
        await stop_scheduler()
        logging.info(f'Пользователь {user[1]} отключил функцию оповещения')
        await message.reply("Функция ежедневного оповещения выключена.",reply_markup = base_button)

#-------------Автоотправка--------------

async def scheduler():
    """ Автоотправка сообщений. """
    user = await get_user(user_id)
    if user != None:
        user_time = user[4]
        aioschedule.every().day.at(f'{user_time}').do(weather_auto)
        while True:
            await aioschedule.run_pending()
            await asyncio.sleep(5)

async def start_scheduler():
    """ Запуск автоотправки. """
    global task
    task = asyncio.create_task(scheduler())
    user = await get_user(user_id)
    logging.info(f'Пользователь {user[1]} запустил автоотправку оповещений!')
        
async def stop_scheduler():
    """ Остановка автоотправки. """
    schedule.CancelJob
    user = await get_user(user_id)
    logging.info(f'Пользователь {user[1]} остановил автоотправку оповещений!')   


#-------------Main--------------

if __name__ == '__main__':
    print('start')
    logging.basicConfig(filename='logger.txt',level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    executor.start_polling(dp, skip_updates=False)

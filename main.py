import telebot
import requests
import json
import time
import schedule
from threading import Thread
from telebot import types
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('BOT_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
USER_DATA_FILE = 'user_data.json'

if not TELEGRAM_BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    exit(1)

if not WEATHER_API_KEY:
    print("❌ ОШИБКА: WEATHER_API_KEY не найден!")
    exit(1)

print(f"✅ BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:10]}...")
print(f"✅ WEATHER_API_KEY: {WEATHER_API_KEY[:10]}...")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def load_user_data():
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_user_data(user_data):
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

def get_user_city(user_id):
    user_data = load_user_data()
    return user_data.get(str(user_id), {}).get('city')

def set_user_city(user_id, city):
    user_data = load_user_data()
    user_id_str = str(user_id)
    
    if user_id_str not in user_data:
        user_data[user_id_str] = {}
    
    user_data[user_id_str]['city'] = city
    user_data[user_id_str]['subscribed'] = True
    save_user_data(user_data)

def get_subscribed_users():
    user_data = load_user_data()
    subscribed_users = []
    
    for user_id, data in user_data.items():
        if data.get('subscribed'):
            subscribed_users.append({'user_id': user_id, 'city': data.get('city')})
    return subscribed_users

def unsubscribe_user(user_id):
    user_data = load_user_data()
    user_id_str = str(user_id)
    
    if user_id_str in user_data:
        user_data[user_id_str]['subscribed'] = False
        save_user_data(user_data)
        return True
    return False

def create_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    botton_weather = types.KeyboardButton('🌤️ Узнать погоду')
    botton_subscribe = types.KeyboardButton('📅 Подписаться на рассылку')
    botton_change_city = types.KeyboardButton('🏙️ Сменить город')
    botton_unsubscribe = types.KeyboardButton('❌ Отписаться от рассылки')
    botton_help = types.KeyboardButton('❓ Помощь')
    
    markup.add(botton_weather, botton_change_city, botton_unsubscribe, botton_subscribe, botton_help)
    return markup

@bot.message_handler(commands=['id'])
def show_id(message):
    bot.reply_to(message, f"🆔 Твой ID: {message.from_user.id}\n📱 Username: @{message.from_user.username}")

@bot.message_handler(commands=['site', 'website'])
def site(message):
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("🌐 Открыть Яндекс.Погоду", url='https://yandex.ru/pogoda/ru?lon=37.5438&lat=55.4315&ysclid=mhkm56bnt2614528838&ll=37.5427_55.3971&z=12')
    markup.add(button)
    bot.send_message(message.chat.id, "Нажми на кнопку ниже чтобы открыть сайт погоды:", reply_markup=markup)

@bot.message_handler(commands=['start', 'hello', 'Hello', 'Guten tag', 'Halo'])
def main(message):
    welcome_text = f"""
Привет, {message.from_user.first_name}! 👋

Я бот погоды, который поможет тебе:
• Узнать текущую погоду в любом городе 🌤️
• Получать ежедневный прогноз в 5:00 утра 📅

Выбери действие или просто напиши название города!
    """
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_keyboard())
    bot.send_message(message.chat.id, "Хочешь получать погоду каждый день? Нажми '📅 Подписаться на рассылку'!")

@bot.message_handler(func=lambda message: message.text == '🌤️ Узнать погоду')
def ask_weather_button(message):
    msg = bot.send_message(message.chat.id, "Введите название города:")
    bot.register_next_step_handler(msg, process_weather_request)

def process_weather_request(message):
    city = message.text.strip()
    get_weather_data(message, city)

@bot.message_handler(func=lambda message: message.text == "📅 Подписаться на рассылку")
def ask_subscribe_city(message):
    print("🟢 КНОПКА НАЖАТА: Подписаться на рассылку")
    msg = bot.send_message(message.chat.id, "Введите город для ежедневной рассылки:")
    bot.register_next_step_handler(msg, progress_subscription)

def progress_subscription(message):
    print("=" * 50)
    print("🟢 ФУНКЦИЯ progress_subscription ВЫЗВАНА")
    
    city = message.text.strip()
    user_id = message.chat.id
    
    print(f"🔍 Получен город: '{city}'")
    print(f"🔍 User ID: {user_id}")
    print(f"🔍 API Key: {WEATHER_API_KEY[:10]}...")
    
    if not city:
        print("❌ Город пустой!")
        bot.send_message(user_id, "❌ Вы не ввели город. Попробуйте снова.")
        return
    
    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru'
    print(f"🔍 URL запроса: {url}")
    
    try:
        print("🟡 Делаем запрос к API...")
        test_response = requests.get(url, timeout=10)
        
        print(f"🟡 Статус ответа: {test_response.status_code}")
        print(f"🟡 Текст ответа: {test_response.text[:200]}...")
        
        if test_response.status_code == 200:
            print("🟢 Город найден! Сохраняем...")
            set_user_city(user_id, city)
            bot.send_message(user_id, f"✅ Ты подписан на ежедневную рассылку погоды для города {city}!")
        else:
            print("❌ Город не найден в API")
            bot.send_message(user_id, f"❌ Город '{city}' не найден. Попробуйте:\n• Москва\n• London\n• Paris")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {e}")
        bot.send_message(user_id, "❌ Ошибка соединения. Попробуйте позже.")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        bot.send_message(user_id, "❌ Произошла ошибка. Попробуйте другой город.")

@bot.message_handler(func=lambda message: message.text == '🏙️ Сменить город')
def ask_new_city(message):
    current_city = get_user_city(message.chat.id)
    if current_city:
        msg = bot.send_message(message.chat.id,
                               f"Твой текущий город: {current_city} \nВведите новый город для рассылки.")
    else:
        msg = bot.send_message(message.chat.id, "Введите город для рассылки:")
    bot.register_next_step_handler(msg, progress_city_change)

def progress_city_change(message):
    city = message.text.strip()
    user_id = message.chat.id
    
    try:
        text_response = requests.get(
            f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru',
            timeout=10)
        
        if text_response.status_code == 200:
            set_user_city(user_id, city)
            bot.send_message(user_id, f"✅ Город изменен на {city}!")
        else:
            bot.send_message(user_id, "❌ Город не найден. Проверь название и попробуй снова.")
    
    except requests.exceptions.RequestException as e:
        bot.send_message(user_id, "❌ Ошибка соединения. Попробуйте позже.")
    except Exception as e:
        bot.send_message(user_id, "❌ Произошла ошибка. Попробуйте другой город.")

@bot.message_handler(func=lambda message: message.text == '❌ Отписаться от рассылки')
def handle_unsubscribe(message):
    user_id = message.chat.id
    if unsubscribe_user(user_id):
        bot.send_message(user_id, "❌ Ты отписался от ежедневной рассылки.")
    else:
        bot.send_message(user_id, "🤔 Ты не был подписан на рассылку.")

@bot.message_handler(func=lambda message: message.text == '❓ Помощь')
def show_help(message):
    help_text = """
📖 **Помощь по боту:**

**Основные команды:**
• *Просто напиши город* - узнать погоду
• 🌤️ *Узнать погоду* - запросить погоду для любого города
• 📅 *Подписаться на рассылку* - получать погоду каждый день в 5:00
• 🏙️ *Сменить город* - изменить город для рассылки
• ❌ *Отписаться от рассылки* - остановить ежедневные уведомления
• `/id` - показать твой ID и username

**Примеры использования:**
`Москва` - погода в Москве
`/weather Лондон` - погода в Лондоне"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['weather'])
def weather_command(message):
    try:
        city = message.text.split(' ', 1)[1].strip()
        get_weather_data(message, city)
    except IndexError:
        bot.reply_to(message, "Пожалуйста, укажите город: /weather 'город' ")

@bot.message_handler(content_types=['text'])
def text_message(message):
    if message.text.startswith('/'):
        return None
    
    button_texts = [
        '🌤️ Узнать погоду',
        '📅 Подписаться на рассылку',
        '🏙️ Сменить город',
        '❌ Отписаться от рассылки',
        '❓ Помощь'
    ]
    if message.text in button_texts:
        return None
    
    city = message.text.strip()
    get_weather_data(message, city)

def get_weather_data(message, city):
    if not os.path.exists('Weather_bot_photos'):
        print("⚠️ Папка 'Weather_bot_photos' не найдена! Создайте папку и добавьте изображения.")
    
    res = requests.get(f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru')
    
    if res.status_code == 200:
        data = json.loads(res.text)
        weather_main = data['weather'][0]['main'].lower()
        weather_desc = data['weather'][0]['description'].lower()
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = str(data['main']['humidity']) + '%'
        city_name = data.get('name', city.title())
        
        if ('снег' in weather_desc and 'дождь' in weather_desc) or ('snow' in weather_main and 'rain' in weather_desc):
            image = 'Снег с дождём.png'
            weather_comment = "❄️🌧️ Снег с дождем! Одевайся теплее и бери зонт."
        elif 'thunderstorm' in weather_main or 'гроза' in weather_desc:
            image = 'Молнии.png'
            weather_comment = "⚡ Осторожно! Возможна гроза. Лучше остаться в помещении."
        elif 'snow' in weather_main or 'снег' in weather_desc:
            image = 'Снег.png'
            weather_comment = "❄️ Сегодня снег! Одевайся теплее."
        elif 'rain' in weather_main or 'drizzle' in weather_main or 'дождь' in weather_desc:
            image = 'Дождик.png'
            weather_comment = "🌧️ Не забудь зонтик! Сегодня ожидается дождь."
        elif 'clouds' in weather_main or 'облачно' in weather_desc:
            image = 'Облачно.png'
            weather_comment = "☁️ Сегодня облачно."
        elif 'clear' in weather_main or 'ясно' in weather_desc:
            image = 'Солнечно.jpg'
            weather_comment = "☀️ Сегодня солнечно! Отличный день для прогулки."
        elif 'mist' in weather_main or 'fog' in weather_main or 'туман' in weather_desc:
            image = 'туман.png'
            weather_comment = "🌫️ Сегодня туман. Будь осторожен на дороге."
        else:
            image = 'Солнечно.jpg'
            weather_comment = f"Погода: {weather_desc}"
        
        weather_message = f"""
🌍 Погода в городе {city_name}:
🌡️ Температура: {temp}°C (ощущается как {feels_like}°C)
💧 Влажность: {humidity}
📝 {weather_comment}
        """
        
        bot.reply_to(message, weather_message)
        
        try:
            image_path = os.path.join('Weather_bot_photos', image)
            with open(image_path, 'rb') as file:
                bot.send_photo(message.chat.id, file)
        except FileNotFoundError:
            pass
    
    else:
        bot.reply_to(message, '❌ Такого города не существует! Введите существующий город')

def send_daily_weather():
    subscribed_users = get_subscribed_users()
    
    for user in subscribed_users:
        try:
            city = user['city']
            user_id = user['user_id']
            
            res = requests.get(
                f'https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru')
            
            if res.status_code == 200:
                data = json.loads(res.text)
                city_name = data['city']['name']
                forecast_data = data['list'][:8]
                
                day_temperatures = []
                rain_periods = []
                snow_periods = []
                
                for forecast in forecast_data:
                    forecast_time = datetime.fromtimestamp(forecast['dt']).strftime('%H:%M')
                    temp = forecast['main']['temp']
                    weather_main = forecast['weather'][0]['main'].lower()
                    weather_desc = forecast['weather'][0]['description'].lower()
                    
                    day_temperatures.append(temp)
                    
                    if 'rain' in weather_main or 'дождь' in weather_desc:
                        rain_periods.append(forecast_time)
                    if 'snow' in weather_main or 'снег' in weather_desc:
                        snow_periods.append(forecast_time)
                
                avg_temp = round(sum(day_temperatures) / len(day_temperatures), 1)
                max_temp = max(day_temperatures)
                min_temp = min(day_temperatures)
                
                morning_message = f"""
🌅 Доброе утро!
🌍 Прогноз погоды в городе {city_name} на сегодня:

📊 Общая картина:
• Средняя температура: {avg_temp}°C
• Максимальная: {max_temp}°C
• Минимальная: {min_temp}°C
"""
                
                if rain_periods:
                    rain_times = ", ".join(rain_periods)
                    morning_message += f"\n🌧️ Ожидается дождь в периоды: {rain_times}"
                    morning_message += "\n🚨 Не забудь зонтик! ☂️"
                
                if snow_periods:
                    snow_times = ", ".join(snow_periods)
                    morning_message += f"\n❄️ Ожидается снег в периоды: {snow_times}"
                    morning_message += "\n🧤 Одевайся теплее!"
                
                if not rain_periods and not snow_periods:
                    morning_message += "\n✅ Осадков не ожидается. Хорошего дня! ☀️"
                
                bot.send_message(user_id, morning_message)
            
            else:
                bot.send_message(user_id, f"❌ Не удалось получить прогноз для города {city}. Попробуйте позже.")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка сети при отправке пользователю {user['user_id']}: {e}")
        except Exception as e:
            print(f"❌ Неожиданная ошибка при отправке пользователю {user['user_id']}: {e}")

def schedule_daily_messages():
    schedule.every().day.at("05:00").do(send_daily_weather)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_scheduler():
    scheduler_thread = Thread(target=schedule_daily_messages)
    scheduler_thread.daemon = True
    scheduler_thread.start()

start_scheduler()

if __name__ == "__main__":
    print("🤖 Бот запущен и работает...")
    bot.polling(none_stop=True)

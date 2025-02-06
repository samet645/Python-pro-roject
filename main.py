import telebot
import requests
from bs4 import BeautifulSoup
import re
from settings import TOKEN

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Словарь для хранения данных о странах
countries_data = {}

def scrape_country_data():
    """Сбор информации о странах из Википедии"""
    url = "https://ru.wikipedia.org/wiki/Список_столиц_государств"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    tables = soup.find_all('table', 'wikitable sortable')
    
    if not tables:
        print("Не удалось найти таблицу на странице")
        return
        
    for table in tables:
        for row in table.find_all('tr')[1:]:  # Пропускаем заголовок таблицы
            cols = row.find_all('td')
            if len(cols) >= 2:
                country = cols[1].text.strip()
                country = re.sub(r'[d+]', '', country)
                capital = cols[2].text.strip()
                # Получаем дополнительную информацию
                country_url = f"https://ru.wikipedia.org/wiki/{country.replace(' ', '_')}"
                try:
                    country_response = requests.get(country_url)
                    country_soup = BeautifulSoup(country_response.content, 'html.parser')
                    info_box = country_soup.find('table', 'infobox')
                    
                    population = "Нет данных"
                    region = "Нет данных"
                    summary = "Нет данных"
                    area = "Нет данных"
                    currency = "Нет данных"
                    language = "Нет данных"
                    
                    if info_box:
                        # Поиск населения
                        pop_row = info_box.find(string=lambda t: t and 'Население' in t)
                        if pop_row:
                            pop_cell = pop_row.find_next('td')
                            if pop_cell:
                                population = pop_cell.text.strip()
                        
                        # Поиск региона/континента
                        region_row = info_box.find(string=lambda t: t and ('Часть света' in t or 'Континент' in t))
                        if region_row:
                            region_cell = region_row.find_next('td')
                            if region_cell:
                                region = region_cell.text.strip()

                        # Поиск площади
                        area_row = info_box.find(string=lambda t: t and 'Площадь' in t)
                        if area_row:
                            area_cell = area_row.find_next('td')
                            if area_cell:
                                area = area_cell.text.strip()

                        # Поиск валюты
                        currency_row = info_box.find(string=lambda t: t and 'Валюта' in t)
                        if currency_row:
                            currency_cell = currency_row.find_next('td')
                            if currency_cell:
                                currency = currency_cell.text.strip()
                                

                        # Поиск языка
                        lang_row = info_box.find(string=lambda t: t and 'Официальный язык' in t)
                        if lang_row:
                            lang_cell = lang_row.find_next('td')
                            if lang_cell:
                                language = lang_cell.text.strip()
                    
                    # Получаем первый абзац как краткое описание
                    first_p = country_soup.find('div', {'class': 'mw-parser-output'}).find('p', recursive=False)
                    if first_p:
                        summary = first_p.text.strip()[:300] + "..."
                    
                    countries_data[country.lower()] = {
                        'capital': capital,
                        'population': population,
                        'region': region,
                        'area': area,
                        'currency': currency,
                        'language': language,
                        'summary': summary
                    }
                    
                    # Добавляем столицу как ключ для обратного поиска
                    countries_data[capital.lower()] = {
                        'country': country,
                        'is_capital': True
                    }
                    
                except Exception as e:
                    print(f"Ошибка при обработке {country}: {e}\n\n")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if not countries_data:
        bot.reply_to(message, "Пожалуйста, подождите. Загружаю информацию о странах...")
        scrape_country_data()
    
    bot.reply_to(message, 
                 "Привет! Я могу помочь найти:\n"
                 "1. Столицу по названию страны\n"
                 "2. Страну по названию города/столицы\n\n"
                 "Просто отправьте название страны или города.")

@bot.message_handler(func=lambda message: True)
def handle_query(message):
    if not countries_data:
        scrape_country_data()
    
    query = message.text.strip().lower()
    
    if query in countries_data:
        data = countries_data[query]
        if 'is_capital' in data:
            # Это столица
            bot.reply_to(message, f"Город {query.title()} является столицей страны: {data['country']}")
        else:
            # Это страна
            response = (f"Страна: {query.title()}\n"
                       f"Столица: {data['capital']}\n"
                       f"Население: {data['population']}\n"
                       f"Регион: {data['region']}\n"
                       f"Площадь: {data['area']}\n"
                       f"Валюта: {data['currency']}\n"
                       f"Официальный язык: {data['language']}\n\n"
                       f"Краткая информация:\n{data['summary']}")
            bot.reply_to(message, response)
    else:
        bot.reply_to(message, "Извините, не могу найти информацию об этой стране или городе. "
                             "Проверьте правильность написания.")

# Запуск бота
bot.polling(none_stop=True)
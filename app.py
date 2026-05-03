import json
import re
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# ------------------------------------------------------------
# БАЗА ЗАМЕН (универсальные + специализированные)
# ------------------------------------------------------------
UNIVERSAL = {
    'яйцо': [
        '1 яйцо = 1 ст. ложка молотого льна + 3 ст. ложки воды (замочить на 5 минут)',
        '1 яйцо = ¼ стакана (60 г) яблочного пюре',
        '1 яйцо = ½ спелого банана, размятого в пюре',
        '1 яйцо = 3 ст. ложки нутовой муки + 3 ст. ложки воды',
        '1 яйцо = ¼ стакана веганского йогурта или сметаны'
    ],
    'сахар': [
        'Мёд: ½ стакана (100 г) + уменьшить жидкость на ¼ стакана',
        'Кленовый сироп: ¾ стакана (150 мл) + уменьшить жидкость на 3 ст. ложки',
        'Кокосовый сахар: 1:1',
        'Эритрит / Стевия: по инструкции на упаковке (обычно в 2-3 раза слаще)'
    ],
    'мука пшеничная': [
        'Миндальная мука: 75 г на 100 г пшеничной',
        'Овсяная мука: 1:1 (тесто будет плотнее)',
        'Рисовая мука: 80 г на 100 г пшеничной',
        'Нутовая мука: 1:1 (ореховый привкус)'
    ],
    'сливочное масло': [
        'Растительное масло: 80 г на 100 г сливочного',
        'Маргарин: 1:1',
        'Яблочное пюре: 1:1 (для кексов, маффинов)',
        'Кокосовое масло: 1:1',
        'Авокадо (пюре): 1:1'
    ],
    'молоко': [
        'Растительное молоко (миндальное, соевое, овсяное): 1:1',
        'Вода + растительное масло: 1 стакан воды + 2 ст. ложки масла',
        'Сливки 10% + вода: 1:1',
        'Сметана + вода: смешать 1:1 до консистенции молока'
    ],
    'панировочные сухари': [
        'Измельчённые овсяные хлопья (геркулес)',
        'Манная крупа',
        'Тёртый сыр',
        'Молотые грецкие орехи'
    ],
    'разрыхлитель': [
        '1 ч. ложка разрыхлителя = ½ ч. ложки соды + ½ ч. ложки уксуса',
        '1 ч. ложка разрыхлителя = 120 г кефира + ¼ ч. ложки соды',
        'Взбитые белки (для пышности)'
    ]
}

SPECIAL = {
    ('сливочное масло', 'печенье'): [
        '75% растительного масла от веса сливочного',
        'Яблочное пюре 1:1 (тесто будет влажнее)'
    ],
    ('куриное яйцо', 'кекс'): [
        '1 ст. ложка льняной муки + 3 ст. ложки воды на 1 яйцо',
        '60 г яблочного пюре',
        'Половина банана'
    ],
    ('пшеничная мука', 'блины'): [
        'Гречневая мука 1:1',
        'Кукурузная мука 1:1',
        'Смесь 70 г рисовой муки + 30 г крахмала'
    ]
}

# Таблица пересчёта для ингредиентов (для показа альтернативных единиц)
# Значения примерные, округлены для удобства
CONVERSION = {
    'мука пшеничная': {
        '1 ст.л.': 15,    # граммов
        '1 ч.л.': 5,
        '1 стакан (250 мл)': 160
    },
    'сахар': {
        '1 ст.л.': 25,
        '1 ч.л.': 8,
        '1 стакан (250 мл)': 200
    },
    'сливочное масло': {
        '1 ст.л.': 20,
        '1 ч.л.': 7,
        '1 стакан (250 мл)': 220
    },
    'молоко': {
        '1 ст.л.': 15,
        '1 ч.л.': 5,
        '1 стакан (250 мл)': 250
    },
    'яйцо': {
        '1 шт': 50    # среднее яйцо 50 г
    }
}

# ------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ------------------------------------------------------------
def normalize(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s\.]', ' ', text)
    return re.sub(r'\s+', ' ', text)

def extract_quantity(text):
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*((?:ст\.?л\.?|ч\.?л\.?|шт|гр?\.?|грамм|мл|кг|л|стакан|ложк[аи]?))', text)
    if not match:
        # пробуем без единицы измерения (только число)
        match = re.search(r'(\d+(?:[.,]\d+)?)', text)
        if match:
            num = float(match.group(1).replace(',', '.'))
            return num, None
        return None, None
    num = float(match.group(1).replace(',', '.'))
    unit = match.group(2).lower()
    # нормализуем единицы
    if unit.startswith('ст'):
        unit = 'ст.л.'
    elif unit.startswith('ч'):
        unit = 'ч.л.'
    elif unit.startswith('гр') or unit == 'грамм':
        unit = 'г'
    elif unit == 'мл':
        unit = 'мл'
    elif unit == 'л':
        unit = 'л'
    elif unit == 'кг':
        unit = 'кг'
    elif unit in ['штук', 'шт']:
        unit = 'шт'
    elif unit == 'стакан':
        unit = 'стакан'
    return num, unit

def convert_quantity(ingredient, qty, unit):
    """Возвращает строку с альтернативной мерой (например '≈ 4 ст.л.')."""
    if not unit or ingredient not in CONVERSION:
        return ''
    data = CONVERSION[ingredient]
    # Сначала пробуем перевести в граммы
    if unit in ['г', 'мл']:   # мл для молока считаем как г
        grams = qty
        # ищем эквивалент в ложках
        for measure, g in data.items():
            if 'ст.л.' in measure and g > 0:
                spoons = round(grams / g, 1)
                if spoons >= 0.5:
                    return f'≈ {spoons} ст.л.'
        for measure, g in data.items():
            if 'ч.л.' in measure and g > 0:
                spoons = round(grams / g, 1)
                if spoons >= 0.5:
                    return f'≈ {spoons} ч.л.'
    elif unit == 'ст.л.':
        grams = qty * data.get('1 ст.л.', 0)
        if grams:
            return f'≈ {grams:.0f} г'
    elif unit == 'ч.л.':
        grams = qty * data.get('1 ч.л.', 0)
        if grams:
            return f'≈ {grams:.0f} г'
    elif unit == 'стакан':
        grams = qty * data.get('1 стакан (250 мл)', 0)
        if grams:
            return f'≈ {grams:.0f} г'
    elif unit == 'шт' and ingredient == 'яйцо':
        grams = qty * data['1 шт']
        return f'≈ {grams:.0f} г'
    return ''

def find_dish(text):
    match = re.search(r'(?:в|для)\s+(\w+)', text)
    if match:
        return match.group(1)
    words = text.split()
    if len(words) > 1:
        return words[-1]
    return None

def get_substitutions(ingredient, dish=None):
    ing_norm = normalize(ingredient)
    if dish:
        dish_norm = normalize(dish)
        for (k_ing, k_dish), subs in SPECIAL.items():
            if k_ing in ing_norm and k_dish in dish_norm:
                return subs
    for key, subs in UNIVERSAL.items():
        if key in ing_norm:
            return subs
    return []

# ------------------------------------------------------------
# ОСНОВНОЙ ОБРАБОТЧИК
# ------------------------------------------------------------
@app.route('/', methods=['POST'])
def handle_alice():
    data = request.json
    session = data.get('session', {})
    user_input = data.get('request', {}).get('original_utterance', '').strip()
    is_new = session.get('new', False)

    # Приветствие
    if is_new or user_input.lower() in ['привет', 'старт', 'помощь']:
        return jsonify({
            'session': session,
            'version': data.get('version'),
            'response': {
                'text': 'Привет! Я кулинарный помощник. Назовите, что хотите заменить, например: "яйцо" или "200 г сливочного масла для печенья". Можете указывать граммы, миллилитры, столовые или чайные ложки.',
                'end_session': False
            }
        })

    if not user_input:
        return jsonify({
            'session': session,
            'version': data.get('version'),
            'response': {
                'text': 'Повторите, пожалуйста, какой ингредиент заменить.',
                'end_session': False
            }
        })

    normalized = normalize(user_input)
    # Извлекаем количество и единицу
    qty, unit = extract_quantity(normalized)

    # Пытаемся найти ингредиент
    found_ingredient = None
    for ing in UNIVERSAL.keys():
        if ing in normalized:
            found_ingredient = ing
            break

    if not found_ingredient:
        return jsonify({
            'session': session,
            'version': data.get('version'),
            'response': {
                'text': 'Не поняла, что вы хотите заменить. Скажите, например: "замени яйцо" или "чем заменить муку".',
                'end_session': False
            }
        })

    # Блюдо
    dish = find_dish(normalized)

    # Получаем замены
    subs = get_substitutions(found_ingredient, dish)

    if not subs:
        text = f"Для «{found_ingredient}» у меня пока нет замен. Попробуйте спросить иначе."
    else:
        text = f"Вот чем можно заменить {found_ingredient}"
        if dish:
            text += f" для блюда «{dish}»"
        if qty and unit:
            alt = convert_quantity(found_ingredient, qty, unit)
            if alt:
                text += f" (на {qty} {unit}, {alt})"
            else:
                text += f" (на {qty} {unit})"
        elif qty and not unit:
            text += f" (на {qty} частей — ориентируйтесь на пропорции)"
        text += ":\n" + "\n".join(f"• {s}" for s in subs)

    return jsonify({
        'session': session,
        'version': data.get('version'),
        'response': {
            'text': text,
            'end_session': False
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

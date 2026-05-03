import json
import re
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# База замен: (ингредиент, блюдо) -> список замен
SUBSTITUTIONS = {
    ("сливочное масло", "печенье"): [
        "180 г растительного масла",
        "200 г яблочного пюре",
        "200 г пюре из авокадо"
    ],
    ("куриное яйцо", "кекс"): [
        "1 ст. ложку льняной муки + 3 ст. ложки воды",
        "60 г яблочного пюре",
        "½ банана, размятого в пюре"
    ],
    ("пшеничная мука", "кекс"): [
        "150 г овсяной муки",
        "120 г миндальной муки"
    ],
    ("панировочные сухари", "котлеты"): [
        "измельчённые овсяные хлопья",
        "тёртый сыр",
        "молотые грецкие орехи"
    ],
    ("разрыхлитель", "бисквит"): [
        "1 ч. ложку соды + 1 ст. ложку уксуса",
        "минеральную воду с газом"
    ]
}

def extract_ingredient_and_dish(text):
    """Извлекает ингредиент и блюдо из запроса."""
    text = text.lower().strip()
    # Удаляем слова-паразиты: замени, чем заменить, нужно
    text = re.sub(r'(замени|чем заменить|нужно|помоги|пожалуйста)', '', text)
    # Ищем конструкцию "что-то в что-то"
    match = re.search(r'(.+?)\s+в\s+(.+)', text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    # Конструкция "что-то для чего-то"
    match = re.search(r'(.+?)\s+для\s+(.+)', text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    # Если нет предлогов: последнее слово — блюдо, остальное — ингредиент
    parts = text.split()
    if len(parts) >= 2:
        return ' '.join(parts[:-1]), parts[-1]
    return None, None

def find_substitution(ingredient, dish):
    """Ищет замену в базе (с частичным совпадением)."""
    # Прямое совпадение
    key = (ingredient, dish)
    if key in SUBSTITUTIONS:
        subs = ', '.join(SUBSTITUTIONS[key])
        return f"Для замены {ingredient} в {dish} можно использовать: {subs}."
    # Частичное совпадение
    for (k_ing, k_dish), subs_list in SUBSTITUTIONS.items():
        if (k_ing in ingredient or ingredient in k_ing) and (k_dish in dish or dish in k_dish):
            subs = ', '.join(subs_list)
            return f"Похоже, вы хотите заменить {k_ing} в {k_dish}. Можно использовать: {subs}."
    return None

@app.route('/', methods=['POST'])
def handle_alice():
    data = request.json
    session = data.get('session', {})
    version = data.get('version')
    user_text = data.get('request', {}).get('original_utterance', '').lower().strip()
    is_new = session.get('new', False)

    # Приветствие
    if is_new or user_text in ['привет', 'старт', 'помощь']:
        return jsonify({
            'session': session,
            'version': version,
            'response': {
                'text': "Здравствуйте! Я подскажу, чем заменить продукт. Назовите ингредиент и блюдо, например: 'сливочное масло в печенье' или '200 г муки для кекса'.",
                'end_session': False
            }
        })

    if not user_text:
        return jsonify({
            'session': session,
            'version': version,
            'response': {
                'text': "Скажите, что вы хотите заменить и в каком блюде. Например: 'сливочное масло печенье'.",
                'end_session': False
            }
        })

    ingredient, dish = extract_ingredient_and_dish(user_text)
    if not ingredient or not dish:
        return jsonify({
            'session': session,
            'version': version,
            'response': {
                'text': "Не поняла. Уточните: сначала ингредиент, потом блюдо. Пример: 'сливочное масло печенье'.",
                'end_session': False
            }
        })

    answer = find_substitution(ingredient, dish)
    if not answer:
        answer = f"Извините, я пока не знаю, чем заменить {ingredient} в {dish}. Попробуйте другой продукт или блюдо."

    return jsonify({
        'session': session,
        'version': version,
        'response': {
            'text': answer,
            'end_session': False
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

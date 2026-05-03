import json
import logging
import os

from flask import Flask, request, jsonify

app = Flask(__name__)

# База данных замен
SUBSTITUTIONS = {
    ("сливочное масло", "печенье"): [
        "180 г растительного масла",
        "200 г яблочного пюре",
        "200 г пюре из авокадо"
    ],
    ("куриное яйцо", "кекс"): [
        "1 столовую ложку льняной муки, смешанную с 3 ст ложками воды",
        "60 г яблочного пюре",
        "½ банана, размятого в пюре"
    ],
    ("пшеничная мука", "кекс"): [
        "150 г овсяной муки (текстура будет плотнее)",
        "120 г миндальной муки (тесто будет более влажным)"
    ],
    ("панировочные сухари", "котлеты"): [
        "измельченные овсяные хлопья",
        "тёртый сыр",
        "молотые грецкие орехи"
    ],
    ("разрыхлитель", "бисквит"): [
        "1 ч ложку соды, смешанную с 1 ст ложкой уксуса",
        "минеральную воду с газом"
    ]
}

@app.route('/', methods=['POST'])
def main():
    # Получаем запрос от Алисы
    alice_request = request.json
    # Извлекаем текст, который сказал пользователь
    user_text = alice_request['request']['original_utterance'].lower()

    # Логирование для отладки
    app.logger.info(f"Получен запрос: {user_text}")

    # Формируем базовый шаблон ответа
    response = {
        'session': alice_request['session'],
        'version': alice_request['version'],
        'response': {
            'end_session': False
        }
    }

    # Обрабатываем команду помощи
    if user_text in ["помощь", "что ты умеешь"]: 
        response['response']['text'] = (
            "Я помогу найти замену продукту. Просто назовите одним сообщением ингредиент и блюдо. "
            "Например, 'сливочное масло печенье'."
        )
        return jsonify(response)

    # Ищем пробел, чтобы разделить строку на ингредиент и блюдо
    space_index = user_text.find(' ')
    if space_index == -1:
        # Если пробела нет, значит, мы не смогли распознать запрос
        response['response']['text'] = (
            "Пожалуйста, уточните запрос. Назовите ингредиент и блюдо через пробел. "
            "Например: 'сливочное масло печенье' или скажите 'Помощь'."
        )
        return jsonify(response)

    # Разделяем сообщение на две части: ингредиент и блюдо
    ingredient = user_text[:space_index].strip()
    dish = user_text[space_index:].strip()

    # Ищем замену в нашей базе данных
    key = (ingredient, dish)
    if key in SUBSTITUTIONS:
        substitutes_list = SUBSTITUTIONS[key]
        response_text = f"Для замены {ingredient} в {dish} можно использовать: {', '.join(substitutes_list)}."
    else:
        response_text = f"Извините, я не знаю, чем заменить {ingredient} в {dish}. Попробуйте другой запрос."

    # Отправляем ответ Алисе
    response['response']['text'] = response_text
    return jsonify(response)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

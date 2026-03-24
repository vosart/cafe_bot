from openai import OpenAI
from config import YANDEX_CLOUD_API_KEY, YANDEX_CLOUD_MODEL, YANDEX_CLOUD_FOLDER

client = OpenAI(
        api_key=YANDEX_CLOUD_API_KEY,
        base_url="https://ai.api.cloud.yandex.net/v1",
        )

def load_cafe_info():
    with open("cafe_info.txt", "r", encoding="utf-8") as f:
        return f.read()

def ask_ai(user_question: str) -> str:
    cafe_info = load_cafe_info()

    try:


        response = client.chat.completions.create(
            model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
            messages=[
                {
                    "role": "system",
                    "content": f"""Ты вежливый помощник кафе.
Отвечай ТОЛЬКО на основе информации о кафе ниже.
Вежливо скажи, что не знаешь и предложи позвонить.
Отвечай кратко и по делу.
Информация о кафе:
    {cafe_info}"""
                },
                {
                    "role": "user",
                    "content": user_question
                }
            ],
            max_tokens=500,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Ошибка AI: {e}")
        return "Извините, сейчас не могу ответить. Позвоните нам: +7 (923) 000-00-00"
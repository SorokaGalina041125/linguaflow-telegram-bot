"""Скрипт для заполнения базы данных начальными данными"""

import asyncio

from sqlalchemy import select

from bot.database.database import Base, async_session_maker, engine
from bot.database.models import Achievement, Category, Word

# Начальные категории
INITIAL_CATEGORIES = [
    {"category_name": "Разработка ПО (Software Development)"},
    {"category_name": "Базы данных (Databases)"},
    {"category_name": "Искусственный интеллект (Artificial Intelligence)"},
]

# Начальные слова
INITIAL_WORDS = [
    # Разработка ПО (Software Development)
    {
        "english_word": "Framework",
        "russian_translation": "Фреймворк",
        "category_name": "Разработка ПО (Software Development)",
        "example_sentence": "Django is a popular Python framework for web development.",
        "example_sentence_ru": "Django — популярный фреймворк на Python для веб-разработки.",
    },
    {
        "english_word": "Repository",
        "russian_translation": "Репозиторий",
        "category_name": "Разработка ПО (Software Development)",
        "example_sentence": "The team stores all project code in a Git repository.",
        "example_sentence_ru": "Команда хранит весь код проекта в Git репозитории.",
    },
    {
        "english_word": "Debugging",
        "russian_translation": "Отладка",
        "category_name": "Разработка ПО (Software Development)",
        "example_sentence": "Debugging this complex algorithm took several hours.",
        "example_sentence_ru": "Отладка этого сложного алгоритма заняла несколько часов.",
    },
    {
        "english_word": "Deployment",
        "russian_translation": "Развёртывание",
        "category_name": "Разработка ПО (Software Development)",
        "example_sentence": "The deployment of the new application version is scheduled for Friday.",
        "example_sentence_ru": "Развёртывание новой версии приложения запланировано на пятницу.",
    },
    {
        "english_word": "Agile",
        "russian_translation": "Гибкая методология разработки",
        "category_name": "Разработка ПО (Software Development)",
        "example_sentence": "Our team follows Agile principles and works in two-week sprints.",
        "example_sentence_ru": "Наша команда следует принципам гибкой методологии и работает двухнедельными спринтами.",
    },
    # Базы данных (Databases)
    {
        "english_word": "Query",
        "russian_translation": "Запрос",
        "category_name": "Базы данных (Databases)",
        "example_sentence": "This SQL query retrieves all users registered last month.",
        "example_sentence_ru": "Этот SQL запрос выбирает всех пользователей, зарегистрированных в прошлом месяце.",
    },
    {
        "english_word": "Index",
        "russian_translation": "Индекс",
        "category_name": "Базы данных (Databases)",
        "example_sentence": "Adding an index to the 'email' column significantly improved search performance.",
        "example_sentence_ru": "Добавление индекса к столбцу 'email' значительно улучшило скорость поиска.",
    },
    {
        "english_word": "Transaction",
        "russian_translation": "Транзакция",
        "category_name": "Базы данных (Databases)",
        "example_sentence": "The money transfer is processed within a single database transaction.",
        "example_sentence_ru": "Перевод денег обрабатывается в рамках одной транзакции базы данных.",
    },
    {
        "english_word": "Replication",
        "russian_translation": "Репликация",
        "category_name": "Базы данных (Databases)",
        "example_sentence": "Replication ensures high availability and fault tolerance of the database.",
        "example_sentence_ru": "Репликация обеспечивает высокую доступность и отказоустойчивость базы данных.",
    },
    {
        "english_word": "NoSQL",
        "russian_translation": "Нереляционная база данных",
        "category_name": "Базы данных (Databases)",
        "example_sentence": "For storing unstructured JSON data, we chose a NoSQL database like MongoDB.",
        "example_sentence_ru": "Для хранения неструктурированных JSON-данных мы выбрали NoSQL базу данных, такую как MongoDB.",
    },
    # Искусственный интеллект (Artificial Intelligence)
    {
        "english_word": "Neural Network",
        "russian_translation": "Нейронная сеть",
        "category_name": "Искусственный интеллект (Artificial Intelligence)",
        "example_sentence": "A convolutional neural network is often used for image recognition tasks.",
        "example_sentence_ru": "Сверточная нейронная сеть часто используется для задач распознавания изображений.",
    },
    {
        "english_word": "Training",
        "russian_translation": "Обучение модели",
        "category_name": "Искусственный интеллект (Artificial Intelligence)",
        "example_sentence": "The training of the large language model required enormous computational power.",
        "example_sentence_ru": "Обучение большой языковой модели потребовало колоссальных вычислительных мощностей.",
    },
    {
        "english_word": "Overfitting",
        "russian_translation": "Переобучение",
        "category_name": "Искусственный интеллект (Artificial Intelligence)",
        "example_sentence": "Regularization techniques help to prevent overfitting of the model.",
        "example_sentence_ru": "Методы регуляризации помогают предотвратить переобучение модели.",
    },
    {
        "english_word": "Chatbot",
        "russian_translation": "Чат-бот",
        "category_name": "Искусственный интеллект (Artificial Intelligence)",
        "example_sentence": "The company uses an AI-powered chatbot for handling customer inquiries.",
        "example_sentence_ru": "Компания использует ИИ-чат-бот для обработки запросов клиентов.",
    },
    {
        "english_word": "Computer Vision",
        "russian_translation": "Компьютерное зрение",
        "category_name": "Искусственный интеллект (Artificial Intelligence)",
        "example_sentence": "Computer vision algorithms enable self-driving cars to detect pedestrians.",
        "example_sentence_ru": "Алгоритмы компьютерного зрения позволяют беспилотным автомобилям обнаруживать пешеходов.",
    },
    # Дополнительные слова - Разработка ПО (Software Development)
    {
        "english_word": "Refactoring",
        "russian_translation": "Рефакторинг",
        "category_name": "Разработка ПО (Software Development)",
        "example_sentence": "Before adding new features, we need to do some refactoring of the old module.",
        "example_sentence_ru": "Прежде чем добавлять новые функции, нам нужно провести рефакторинг старого модуля.",
    },
    {
        "english_word": "API",
        "russian_translation": "Интерфейс программирования приложений",
        "category_name": "Разработка ПО (Software Development)",
        "example_sentence": "Our service provides a public API for third-party developers.",
        "example_sentence_ru": "Наш сервис предоставляет публичный API для сторонних разработчиков.",
    },
    {
        "english_word": "Commit",
        "russian_translation": "Коммит",
        "category_name": "Разработка ПО (Software Development)",
        "example_sentence": "Every commit should have a clear message describing the changes.",
        "example_sentence_ru": "Каждый коммит должен содержать понятное сообщение, описывающее изменения.",
    },
    {
        "english_word": "Scalability",
        "russian_translation": "Масштабируемость",
        "category_name": "Разработка ПО (Software Development)",
        "example_sentence": "When designing the architecture, we prioritize scalability to handle future growth.",
        "example_sentence_ru": "При проектировании архитектуры мы уделяем приоритетное внимание масштабируемости, чтобы справиться с будущим ростом.",
    },
    {
        "english_word": "Syntax",
        "russian_translation": "Синтаксис",
        "category_name": "Разработка ПО (Software Development)",
        "example_sentence": "A missing bracket is a common syntax error in many programming languages.",
        "example_sentence_ru": "Пропущенная скобка — это распространенная синтаксическая ошибка во многих языках программирования.",
    },
    # Дополнительные слова - Базы данных (Databases)
    {
        "english_word": "Normalization",
        "russian_translation": "Нормализация",
        "category_name": "Базы данных (Databases)",
        "example_sentence": "Normalization helps to avoid data anomalies during updates.",
        "example_sentence_ru": "Нормализация помогает избежать аномалий данных при обновлениях.",
    },
    {
        "english_word": "Stored Procedure",
        "russian_translation": "Хранимая процедура",
        "category_name": "Базы данных (Databases)",
        "example_sentence": "Complex business logic is often implemented as a stored procedure.",
        "example_sentence_ru": "Сложная бизнес-логика часто реализуется в виде хранимой процедуры.",
    },
    {
        "english_word": "ACID",
        "russian_translation": "ACID (Атомарность, Согласованность, Изоляция, Долговечность)",
        "category_name": "Базы данных (Databases)",
        "example_sentence": "Relational databases guarantee ACID compliance for transactions.",
        "example_sentence_ru": "Реляционные базы данных гарантируют соответствие принципам ACID для транзакций.",
    },
    {
        "english_word": "Data Warehouse",
        "russian_translation": "Хранилище данных",
        "category_name": "Базы данных (Databases)",
        "example_sentence": "All historical sales data is consolidated in the data warehouse for BI tools.",
        "example_sentence_ru": "Все исторические данные о продажах консолидируются в хранилище данных для BI-инструментов.",
    },
    {
        "english_word": "ORM",
        "russian_translation": "ORM (Объектно-реляционное отображение)",
        "category_name": "Базы данных (Databases)",
        "example_sentence": "Using an ORM like SQLAlchemy simplifies database interactions in Python applications.",
        "example_sentence_ru": "Использование ORM, такой как SQLAlchemy, упрощает взаимодействие с базой данных в Python-приложениях.",
    },
    # Дополнительные слова - Искусственный интеллект (Artificial Intelligence)
    {
        "english_word": "Supervised Learning",
        "russian_translation": "Обучение с учителем",
        "category_name": "Искусственный интеллект (Artificial Intelligence)",
        "example_sentence": "Image classification is a classic task for supervised learning.",
        "example_sentence_ru": "Классификация изображений — это классическая задача для обучения с учителем.",
    },
    {
        "english_word": "Inference",
        "russian_translation": "Инференс, Вывод",
        "category_name": "Искусственный интеллект (Artificial Intelligence)",
        "example_sentence": "After training, the model's inference speed is critical for the real-time application.",
        "example_sentence_ru": "После обучения скорость инференса модели критически важна для работы приложения в реальном времени.",
    },
    {
        "english_word": "Bias",
        "russian_translation": "Смещение, Смещённость",
        "category_name": "Искусственный интеллект (Artificial Intelligence)",
        "example_sentence": "It's crucial to audit the dataset for bias before training an AI model for hiring.",
        "example_sentence_ru": "Крайне важно проверить набор данных на смещённость перед обучением ИИ-модели для найма сотрудников.",
    },
    {
        "english_word": "Token",
        "russian_translation": "Токен",
        "category_name": "Искусственный интеллект (Artificial Intelligence)",
        "example_sentence": "In language models, the sentence is split into tokens before processing.",
        "example_sentence_ru": "В языковых моделях предложение разбивается на токены перед обработкой.",
    },
    {
        "english_word": "Generative AI",
        "russian_translation": "Генеративный ИИ",
        "category_name": "Искусственный интеллект (Artificial Intelligence)",
        "example_sentence": "Generative AI tools can create realistic images from text descriptions.",
        "example_sentence_ru": "Инструменты генеративного ИИ могут создавать реалистичные изображения по текстовым описаниям.",
    },
]

# Начальные достижения
INITIAL_ACHIEVEMENTS = [
    {
        "name": "Первые шаги",
        "description": "Пройдите первую тренировку",
        "icon": "🎯",
        "condition": {"type": "first_training"},
    },
    {
        "name": "Словарный запас",
        "description": "Добавьте 10 слов в словарь",
        "icon": "📚",
        "condition": {"type": "words_added", "count": 10},
    },
    {
        "name": "Мастер точности",
        "description": "Достигните 90% точности в тренировке",
        "icon": "🎯",
        "condition": {"type": "accuracy", "threshold": 90},
    },
    {
        "name": "Неделя обучения",
        "description": "Тренируйтесь 7 дней подряд",
        "icon": "🔥",
        "condition": {"type": "streak", "days": 7},
    },
    {
        "name": "Сто слов",
        "description": "Изучите 100 слов",
        "icon": "💯",
        "condition": {"type": "words_mastered", "count": 100},
    },
]


async def init_database():
    """Инициализация базы данных - создание таблиц"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Таблицы базы данных созданы успешно.")


async def fill_categories():
    """Заполнение категорий"""
    async with async_session_maker() as session:
        for cat_data in INITIAL_CATEGORIES:
            # Проверяем, существует ли категория
            result = await session.execute(
                select(Category).where(Category.category_name == cat_data["category_name"])
            )
            existing = result.scalar_one_or_none()

            if not existing:
                category = Category(**cat_data)
                session.add(category)

        await session.commit()
        print(f"Категории заполнены: {len(INITIAL_CATEGORIES)} шт.")


async def fill_words():
    """Заполнение слов"""
    async with async_session_maker() as session:
        # Получаем все категории для маппинга
        result = await session.execute(select(Category))
        categories = {cat.category_name: cat.id for cat in result.scalars().all()}

        added_count = 0
        for word_data in INITIAL_WORDS:
            # Создаем копию словаря, чтобы не изменять оригинал
            word_dict = word_data.copy()
            category_name = word_dict.pop("category_name")
            category_id = categories.get(category_name)

            if not category_id:
                print(f"Ошибка: категория '{category_name}' не найдена!")
                continue

            # Проверяем, существует ли слово (общие слова, user_id=None)
            result = await session.execute(
                select(Word).where(
                    Word.english_word == word_dict["english_word"], Word.user_id.is_(None)
                )
            )
            existing = result.scalar_one_or_none()

            if not existing:
                word = Word(
                    english_word=word_dict["english_word"],
                    russian_translation=word_dict["russian_translation"],
                    category_id=category_id,
                    example_sentence=word_dict.get("example_sentence"),
                    example_sentence_ru=word_dict.get("example_sentence_ru"),
                    user_id=None,  # Общие слова для всех пользователей
                    is_public=True,
                )
                session.add(word)
                added_count += 1

        await session.commit()
        print(f"Слова заполнены: {added_count} шт.")


async def fill_achievements():
    """Заполнение достижений"""
    async with async_session_maker() as session:
        for ach_data in INITIAL_ACHIEVEMENTS:
            # Проверяем, существует ли достижение
            result = await session.execute(
                select(Achievement).where(Achievement.name == ach_data["name"])
            )
            existing = result.scalar_one_or_none()

            if not existing:
                achievement = Achievement(
                    name=ach_data["name"],
                    description=ach_data["description"],
                    icon=ach_data["icon"],
                    condition=ach_data["condition"],  # JSONB автоматически обрабатывает dict
                )
                session.add(achievement)

        await session.commit()
        print(f"Достижения заполнены: {len(INITIAL_ACHIEVEMENTS)} шт.")


async def main():
    """Основная функция инициализации"""
    print("Начало инициализации базы данных...")

    try:
        # Создаем таблицы
        await init_database()

        # Заполняем данными
        await fill_categories()
        await fill_words()
        await fill_achievements()

        print("\nИнициализация базы данных завершена успешно!")

    except Exception as e:
        print(f"Ошибка при инициализации: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

# Схема базы данных LinguaFlow_Bot

База данных: `linguaflow_db`

## Описание

База данных предназначена для хранения информации о пользователях, словах, тренировках, статистике и достижениях в Telegram-боте для изучения английского языка.

## Таблицы (отношения)

### 1. Таблица `users` - Пользователи

Хранит информацию о пользователях бота.

| Атрибут        | Тип     | Ограничения                 | Описание                        |
|----------------|---------|-----------------------------|---------------------------------|
| `id`           | INTEGER | PRIMARY KEY, AUTO_INCREMENT | Уникальный ID пользователя в БД |
| `telegram_id`  | BIGINT  | UNIQUE, NOT NULL, INDEX     | ID пользователя в Telegram      |

**Связи:**

- Один ко многим с `training_sessions` (user_id → users.telegram_id)
- Один ко многим с `user_dictionary` (user_id → users.telegram_id)
- Один ко многим с `answers` (user_id → users.telegram_id)
- Один ко многим с `statistics` (user_id → users.telegram_id)
- Один ко многим с `user_achievements` (user_id → users.telegram_id)
- Один ко многим с `words` (user_id → users.id)

---

### 2. Таблица `categories` - Категории слов

Хранит категории слов (базовые: Разработка ПО, Базы данных, Искусственный интеллект + пользовательские).

| Атрибут         | Тип          | Ограничения                 | Описание                |
|-----------------|--------------|-----------------------------|-------------------------|
| `id`            | INTEGER      | PRIMARY KEY, AUTO_INCREMENT | Уникальный ID категории |
| `category_name` | VARCHAR(255) | UNIQUE, NOT NULL            | Название категории      |

**Связи:**

- Один ко многим с `words` (category_id → categories.id)

---

### 3. Таблица `words` - Слова

Основная таблица для хранения слов и их переводов.

| Атрибут               | Тип          | Ограничения                           | Описание                                 |
|-----------------------|--------------|---------------------------------------|------------------------------------------|
| `id`                  | INTEGER      | PRIMARY KEY, AUTO_INCREMENT           | Уникальный ID слова                      |
| `english_word`        | VARCHAR(255) | NOT NULL                              | Слово на английском языке                |
| `russian_translation` | VARCHAR(255) | NOT NULL                              | Перевод на русский язык                  |
| `category_id`         | INTEGER      | FOREIGN KEY → categories.id, NOT NULL | ID категории слова                       |
| `example_sentence`    | TEXT         | NULL                                  | Пример использования слова на английском |
| `example_sentence_ru` | TEXT         | NULL                                  | Пример использования слова на русском    |
| `user_id`             | INTEGER      | FOREIGN KEY → users.id, NULL          | ID пользователя (NULL для общих слов)    |
| `is_public`           | BOOLEAN      | DEFAULT TRUE, NOT NULL                | Видимо ли слово другим пользователям     |

**Ограничения:**

- `UNIQUE(english_word, user_id)` - уникальность комбинации слова и пользователя

**Связи:**

- Многие к одному с `categories` (category_id → categories.id)
- Многие к одному с `users` (user_id → users.id)
- Один ко многим с `user_dictionary` (word_id → words.id)
- Один ко многим с `answers` (word_id → words.id)
- Один ко многим с `statistics` (word_id → words.id)

**Примечания:**

- Если `user_id` = NULL, то слово является общим для всех пользователей
- Если `user_id` != NULL, то слово является личным для конкретного пользователя
- `is_public` = FALSE означает, что слово видно только создавшему его пользователю

---

### 4. Таблица `user_dictionary` - Пользовательские слова

Хранит пользовательские переводы и настройки для слов.

| Атрибут              | Тип          | Ограничения                               | Описание                   |
|----------------------|--------------|-------------------------------------------|----------------------------|
| `id`                 | INTEGER      | PRIMARY KEY, AUTO_INCREMENT               | Уникальный ID записи       |
| `user_id`            | BIGINT       | FOREIGN KEY → users.telegram_id, NOT NULL | ID пользователя в Telegram |
| `word_id`            | INTEGER      | FOREIGN KEY → words.id, NOT NULL          | ID слова                   |
| `custom_translation` | VARCHAR(255) | NULL                                      | Пользовательский перевод   |

**Ограничения:**

- `UNIQUE(user_id, word_id)` - уникальность комбинации пользователя и слова

**Связи:**

- Многие к одному с `users` (user_id → users.telegram_id)
- Многие к одному с `words` (word_id → words.id)

---

### 5. Таблица `training_sessions` - Тренировки

Хранит информацию о сессиях тренировок пользователей.

| Атрибут           | Тип           | Ограничения                               | Описание                                                  |
|-------------------|---------------|-------------------------------------------|-----------------------------------------------------------|
| `id`              | INTEGER       | PRIMARY KEY, AUTO_INCREMENT               | Уникальный ID сессии                                      |
| `user_id`         | BIGINT        | FOREIGN KEY → users.telegram_id, NOT NULL | ID пользователя в Telegram                                |
| `session_type`    | VARCHAR(50)   | NOT NULL                                  | Тип тренировки: "flashcards", "multiple_choice", "typing" |
| `total_questions` | INTEGER       | DEFAULT 0                                 | Общее количество вопросов                                 |
| `correct_answers` | INTEGER       | DEFAULT 0                                 | Количество правильных ответов                             |
| `accuracy`        | DECIMAL(5, 2) | DEFAULT 0.0                               | Точность в процентах                                      |
| `created_at`      | TIMESTAMP     | DEFAULT NOW()                             | Время создания сессии                                     |

**Связи:**

- Многие к одному с `users` (user_id → users.telegram_id)
- Один ко многим с `answers` (session_id → training_sessions.id)

---

### 6. Таблица `answers` - Ответы

Хранит информацию об ответах пользователей на вопросы в тренировках.

| Атрибут         | Тип          | Ограничения                                  | Описание                                      |
|-----------------|--------------|----------------------------------------------|-----------------------------------------------|
| `id`            | INTEGER      | PRIMARY KEY, AUTO_INCREMENT                  | Уникальный ID ответа                          |
| `session_id`    | INTEGER      | FOREIGN KEY → training_sessions.id, NOT NULL | ID сессии тренировки                          |
| `user_id`       | BIGINT       | FOREIGN KEY → users.telegram_id, NOT NULL    | ID пользователя в Telegram                    |
| `word_id`       | INTEGER      | FOREIGN KEY → words.id, NOT NULL             | ID слова                                      |
| `question_type` | VARCHAR(50)  | NOT NULL                                     | Тип вопроса                                   |
| `user_answer`   | VARCHAR(255) | NULL                                         | Ответ пользователя                            |
| `is_correct`    | BOOLEAN      | NOT NULL                                     | Правильность ответа                           |
| `time_spent_ms` | INTEGER      | NULL                                         | Время, затраченное на ответ (в миллисекундах) |
| `answered_at`   | TIMESTAMP    | DEFAULT NOW()                                | Время ответа                                  |

**Связи:**

- Многие к одному с `training_sessions` (session_id → training_sessions.id)
- Многие к одному с `users` (user_id → users.telegram_id)
- Многие к одному с `words` (word_id → words.id)

---

### 7. Таблица `statistics` - Статистика

Хранит статистику изучения слов пользователями (алгоритм интервального повторения).

| Атрибут          | Тип       | Ограничения                                  | Описание                                             |
|------------------|-----------|----------------------------------------------|------------------------------------------------------|
| `user_id`        | BIGINT    | PRIMARY KEY, FOREIGN KEY → users.telegram_id | ID пользователя в Telegram                           |
| `word_id`        | INTEGER   | PRIMARY KEY, FOREIGN KEY → words.id          | ID слова                                             |
| `mastered_level` | INTEGER   | DEFAULT 0                                    | Уровень освоения слова (0-5)                         |
| `next_review`    | TIMESTAMP | NULL                                         | Когда повторить слово (для интервального повторения) |

**Ограничения:**

- `PRIMARY KEY (user_id, word_id)` - составной первичный ключ

**Связи:**

- Многие к одному с `users` (user_id → users.telegram_id)
- Многие к одному с `words` (word_id → words.id)

**Примечания:**

- `mastered_level` = 0 означает, что слово не изучено
- `mastered_level` = 5 означает, что слово полностью освоено
- `next_review` используется для алгоритма интервального повторения (Spaced Repetition)

---

### 8. Таблица `achievements` - Достижения

Хранит информацию о доступных достижениях в системе.

| Атрибут       | Тип          | Ограничения                 | Описание                                      |
|---------------|--------------|-----------------------------|-----------------------------------------------|
| `id`          | INTEGER      | PRIMARY KEY, AUTO_INCREMENT | Уникальный ID достижения                      |
| `name`        | VARCHAR(255) | NOT NULL                    | Название достижения                           |
| `description` | TEXT         | NULL                        | Описание достижения                           |
| `icon`        | VARCHAR(50)  | NULL                        | Эмодзи или код иконки                         |
| `condition`   | JSONB        | NULL                        | Условие получения достижения (в формате JSON) |

**Связи:**

- Один ко многим с `user_achievements` (achievement_id → achievements.id)

**Примечания:**

- `condition` хранится в формате JSON и может содержать различные условия, например:
  - `{"type": "first_training"}` - первая тренировка
  - `{"type": "words_added", "count": 10}` - добавлено 10 слов
  - `{"type": "accuracy", "threshold": 90}` - точность 90%
  - `{"type": "streak", "days": 7}` - серия из 7 дней
  - `{"type": "words_mastered", "count": 100}` - освоено 100 слов

---

### 9. Таблица `user_achievements` - Пользовательские достижения

Хранит информацию о разблокированных достижениях пользователей.

| Атрибут          | Тип       | Ограничения                                  | Описание                             |
|------------------|-----------|----------------------------------------------|--------------------------------------|
| `user_id`        | BIGINT    | PRIMARY KEY, FOREIGN KEY → users.telegram_id | ID пользователя в Telegram           |
| `achievement_id` | INTEGER   | PRIMARY KEY, FOREIGN KEY → achievements.id   | ID достижения                        |
| `unlocked_at`    | TIMESTAMP | DEFAULT NOW()                                | Время разблокировки достижения       |
| `progress`       | JSONB     | NULL                                         | Прогресс выполнения (в формате JSON) |

**Ограничения:**

- `PRIMARY KEY (user_id, achievement_id)` - составной первичный ключ

**Связи:**

- Многие к одному с `users` (user_id → users.telegram_id)
- Многие к одному с `achievements` (achievement_id → achievements.id)

**Примечания:**

- `progress` может хранить промежуточный прогресс для достижений, требующих нескольких шагов

---

## Диаграмма связей

users (1) ──< (N) training_sessions
users (1) ──< (N) user_dictionary
users (1) ──< (N) answers
users (1) ──< (N) statistics
users (1) ──< (N) user_achievements
users (1) ──< (N) words

categories (1) ──< (N) words

words (1) ──< (N) user_dictionary
words (1) ──< (N) answers
words (1) ──< (N) statistics

training_sessions (1) ──< (N) answers

achievements (1) ──< (N) user_achievements

## Индексы

- `users.telegram_id` - индекс для быстрого поиска пользователей по Telegram ID
- `words.english_word` и `words.user_id` - для уникальности комбинации
- `user_dictionary.user_id` и `user_dictionary.word_id` - для уникальности комбинации
- `statistics.user_id` и `statistics.word_id` - составной первичный ключ
- `user_achievements.user_id` и `user_achievements.achievement_id` - составной первичный ключ

## Начальные данные

При инициализации базы данных автоматически добавляются:

1. **Категории:**
   - Разработка ПО (Software Development)
   - Базы данных (Databases)
   - Искусственный интеллект (Artificial Intelligence)

2. **Слова (15 IT-терминов):**
   - 5 слов в категории "Разработка ПО"
   - 5 слов в категории "Базы данных"
   - 5 слов в категории "Искусственный интеллект"

3. **Достижения (5 штук):**
   - Первые шаги
   - Словарный запас
   - Мастер точности
   - Неделя обучения
   - Сто слов

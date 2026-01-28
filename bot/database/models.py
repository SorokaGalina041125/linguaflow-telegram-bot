"""SQLAlchemy модели для базы данных"""

from sqlalchemy import (
    DECIMAL,
    TIMESTAMP,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from bot.database.database import Base


class User(Base):
    """Модель пользователя"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Связи
    training_sessions = relationship("TrainingSession", back_populates="user")
    user_dictionary = relationship("UserDictionary", back_populates="user")
    answers = relationship("Answer", back_populates="user")
    statistics = relationship("Statistics", back_populates="user")
    user_achievements = relationship("UserAchievement", back_populates="user")
    words = relationship("Word", back_populates="user")


class Category(Base):
    """Модель категории слов"""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(255), nullable=False, unique=True)

    # Связи
    words = relationship("Word", back_populates="category")


class Word(Base):
    """Модель слова"""

    __tablename__ = "words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    english_word = Column(String(255), nullable=False)
    russian_translation = Column(String(255), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    example_sentence = Column(Text)  # Пример на английском
    example_sentence_ru = Column(Text)  # Пример на русском
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_public = Column(Boolean, default=True, nullable=False)

    # Связи
    category = relationship("Category", back_populates="words")
    user = relationship("User", back_populates="words")
    user_dictionary = relationship("UserDictionary", back_populates="word")
    answers = relationship("Answer", back_populates="word")
    statistics = relationship("Statistics", back_populates="word")

    # Уникальность комбинации слова и пользователя
    __table_args__ = (UniqueConstraint("english_word", "user_id", name="unique_user_word"),)


class UserDictionary(Base):
    """Модель пользовательского словаря"""

    __tablename__ = "user_dictionary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    custom_translation = Column(String(255))

    # Связи
    user = relationship("User", back_populates="user_dictionary")
    word = relationship("Word", back_populates="user_dictionary")

    # Уникальность комбинации пользователя и слова
    __table_args__ = (UniqueConstraint("user_id", "word_id", name="unique_user_word_dict"),)


class TrainingSession(Base):
    """Модель тренировки"""

    __tablename__ = "training_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    session_type = Column(String(50), nullable=False)  # "flashcards", "multiple_choice", "typing"
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    accuracy = Column(DECIMAL(5, 2), default=0.0)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Связи
    user = relationship("User", back_populates="training_sessions")
    answers = relationship("Answer", back_populates="session")


class Answer(Base):
    """Модель ответа"""

    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("training_sessions.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    question_type = Column(String(50), nullable=False)
    user_answer = Column(String(255))
    is_correct = Column(Boolean, nullable=False)
    time_spent_ms = Column(Integer)
    answered_at = Column(TIMESTAMP, server_default=func.now())

    # Связи
    session = relationship("TrainingSession", back_populates="answers")
    user = relationship("User", back_populates="answers")
    word = relationship("Word", back_populates="answers")


class Statistics(Base):
    """Модель статистики"""

    __tablename__ = "statistics"

    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), primary_key=True)
    word_id = Column(Integer, ForeignKey("words.id"), primary_key=True)
    mastered_level = Column(Integer, default=0)  # 0-5
    next_review = Column(TIMESTAMP)

    # Связи
    user = relationship("User", back_populates="statistics")
    word = relationship("Word", back_populates="statistics")


class Achievement(Base):
    """Модель достижения"""

    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    icon = Column(String(50))  # эмодзи или код иконки
    condition = Column(JSONB)  # условие получения

    # Связи
    user_achievements = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    """Модель пользовательского достижения"""

    __tablename__ = "user_achievements"

    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), primary_key=True)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), primary_key=True)
    unlocked_at = Column(TIMESTAMP, server_default=func.now())
    progress = Column(JSONB)  # прогресс выполнения

    # Связи
    user = relationship("User", back_populates="user_achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")

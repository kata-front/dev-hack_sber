from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import os
import random
from typing import Any, Literal

from app.models.domain import GameDifficulty, GeneratedQuestion

GenerationSource = Literal["ai", "fallback"]


@dataclass(slots=True)
class QuestionGenerationResult:
    questions: list[GeneratedQuestion]
    source: GenerationSource
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReserveQuestion:
    text: str
    options: tuple[str, str, str, str]
    correct_option: int
    tags: tuple[str, ...] = ()


RESERVE_QUESTIONS: tuple[ReserveQuestion, ...] = (
    ReserveQuestion(
        text="В каком году Юрий Гагарин совершил первый полет человека в космос?",
        options=("1959", "1961", "1963", "1965"),
        correct_option=1,
        tags=("космос", "история", "ссср"),
    ),
    ReserveQuestion(
        text="Какой океан является самым большим на Земле?",
        options=("Атлантический", "Индийский", "Северный Ледовитый", "Тихий"),
        correct_option=3,
        tags=("география", "природа"),
    ),
    ReserveQuestion(
        text="Кто написал роман «Война и мир»?",
        options=("Федор Достоевский", "Лев Толстой", "Антон Чехов", "Иван Тургенев"),
        correct_option=1,
        tags=("литература", "русская литература"),
    ),
    ReserveQuestion(
        text="Какая река самая длинная в России?",
        options=("Волга", "Обь", "Лена", "Енисей"),
        correct_option=1,
        tags=("география", "россия"),
    ),
    ReserveQuestion(
        text="Какой химический символ у золота?",
        options=("Ag", "Au", "Go", "Gd"),
        correct_option=1,
        tags=("химия", "наука"),
    ),
    ReserveQuestion(
        text="Сколько градусов в прямом угле?",
        options=("45", "60", "90", "120"),
        correct_option=2,
        tags=("математика",),
    ),
    ReserveQuestion(
        text="Как называется столица Японии?",
        options=("Пекин", "Сеул", "Токио", "Осака"),
        correct_option=2,
        tags=("география", "страны"),
    ),
    ReserveQuestion(
        text="Кто является автором периодической таблицы химических элементов?",
        options=("Ломоносов", "Менделеев", "Кюри", "Пастер"),
        correct_option=1,
        tags=("химия", "наука"),
    ),
    ReserveQuestion(
        text="Какое число является простым?",
        options=("21", "27", "29", "33"),
        correct_option=2,
        tags=("математика",),
    ),
    ReserveQuestion(
        text="Как называется самая высокая гора в мире над уровнем моря?",
        options=("Килиманджаро", "Эльбрус", "Эверест", "Монблан"),
        correct_option=2,
        tags=("география", "природа"),
    ),
    ReserveQuestion(
        text="Какой газ преобладает в атмосфере Земли?",
        options=("Кислород", "Азот", "Углекислый газ", "Водород"),
        correct_option=1,
        tags=("наука", "природа"),
    ),
    ReserveQuestion(
        text="Сколько континентов принято выделять в школьной географии России?",
        options=("5", "6", "7", "8"),
        correct_option=1,
        tags=("география",),
    ),
    ReserveQuestion(
        text="Какой композитор создал балет «Щелкунчик»?",
        options=("Прокофьев", "Моцарт", "Чайковский", "Рахманинов"),
        correct_option=2,
        tags=("музыка", "культура"),
    ),
    ReserveQuestion(
        text="Как называется устройство для измерения атмосферного давления?",
        options=("Термометр", "Барометр", "Гигрометр", "Манометр"),
        correct_option=1,
        tags=("физика", "наука"),
    ),
    ReserveQuestion(
        text="Какой язык программирования известен как язык веб-разметки страниц?",
        options=("Python", "Java", "HTML", "Go"),
        correct_option=2,
        tags=("it", "программирование"),
    ),
    ReserveQuestion(
        text="Сколько планет в Солнечной системе по современной классификации?",
        options=("7", "8", "9", "10"),
        correct_option=1,
        tags=("астрономия", "космос"),
    ),
    ReserveQuestion(
        text="Кто написал «Преступление и наказание»?",
        options=("Пушкин", "Гоголь", "Достоевский", "Булгаков"),
        correct_option=2,
        tags=("литература", "русская литература"),
    ),
    ReserveQuestion(
        text="Какой инструмент обычно измеряет силу электрического тока?",
        options=("Вольтметр", "Омметр", "Амперметр", "Спидометр"),
        correct_option=2,
        tags=("физика", "наука"),
    ),
    ReserveQuestion(
        text="Какая валюта используется в Японии?",
        options=("Юань", "Иена", "Вона", "Доллар"),
        correct_option=1,
        tags=("экономика", "страны"),
    ),
    ReserveQuestion(
        text="Какой город является столицей Франции?",
        options=("Лион", "Марсель", "Париж", "Ницца"),
        correct_option=2,
        tags=("география", "страны"),
    ),
    ReserveQuestion(
        text="Какой орган человека отвечает за перекачивание крови?",
        options=("Легкие", "Печень", "Сердце", "Почки"),
        correct_option=2,
        tags=("биология", "медицина"),
    ),
    ReserveQuestion(
        text="Сколько бит в одном байте?",
        options=("4", "8", "16", "32"),
        correct_option=1,
        tags=("it",),
    ),
    ReserveQuestion(
        text="Какой материк является самым жарким?",
        options=("Южная Америка", "Африка", "Австралия", "Евразия"),
        correct_option=1,
        tags=("география",),
    ),
    ReserveQuestion(
        text="В каком виде спорта используется термин «офсайд»?",
        options=("Баскетбол", "Теннис", "Футбол", "Волейбол"),
        correct_option=2,
        tags=("спорт",),
    ),
    ReserveQuestion(
        text="Как называется главная площадь Москвы, расположенная у Кремля?",
        options=("Дворцовая", "Манежная", "Красная", "Соборная"),
        correct_option=2,
        tags=("россия", "история"),
    ),
    ReserveQuestion(
        text="Какой процесс превращает жидкость в пар?",
        options=("Конденсация", "Испарение", "Плавление", "Кристаллизация"),
        correct_option=1,
        tags=("физика",),
    ),
    ReserveQuestion(
        text="Сколько сторон у правильного шестиугольника?",
        options=("5", "6", "7", "8"),
        correct_option=1,
        tags=("математика",),
    ),
    ReserveQuestion(
        text="Какой язык является официальным в Бразилии?",
        options=("Испанский", "Португальский", "Английский", "Французский"),
        correct_option=1,
        tags=("страны", "география"),
    ),
)


class QuestionGenerator:
    def __init__(self) -> None:
        self._api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self._model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
        self._timeout_seconds = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "35"))

    async def generate_questions(
        self,
        *,
        topic: str,
        difficulty: GameDifficulty,
        questions_per_team: int,
    ) -> QuestionGenerationResult:
        total = questions_per_team * 2

        if not self._api_key:
            return QuestionGenerationResult(
                questions=self._fallback_questions(topic=topic, difficulty=difficulty, total=total),
                source="fallback",
                reason="Gemini API key отсутствует, использованы запасные вопросы.",
            )

        try:
            from google import genai
            from google.genai import types
        except Exception:
            return QuestionGenerationResult(
                questions=self._fallback_questions(topic=topic, difficulty=difficulty, total=total),
                source="fallback",
                reason="Gemini SDK недоступен, использованы запасные вопросы.",
            )

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(
                    self._generate_gemini_content,
                    genai,
                    types,
                    topic,
                    difficulty,
                    total,
                ),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError:
            return QuestionGenerationResult(
                questions=self._fallback_questions(topic=topic, difficulty=difficulty, total=total),
                source="fallback",
                reason="Gemini не ответил вовремя, использованы запасные вопросы.",
            )
        except Exception:
            return QuestionGenerationResult(
                questions=self._fallback_questions(topic=topic, difficulty=difficulty, total=total),
                source="fallback",
                reason="Ошибка Gemini, использованы запасные вопросы.",
            )

        if not content:
            return QuestionGenerationResult(
                questions=self._fallback_questions(topic=topic, difficulty=difficulty, total=total),
                source="fallback",
                reason="Gemini вернул пустой ответ, использованы запасные вопросы.",
            )

        parsed = self._load_json(content)
        if parsed is None:
            return QuestionGenerationResult(
                questions=self._fallback_questions(topic=topic, difficulty=difficulty, total=total),
                source="fallback",
                reason="Gemini вернул невалидный формат, использованы запасные вопросы.",
            )

        normalized_questions, ai_valid_count = self._normalize_generated(
            parsed,
            total=total,
            topic=topic,
            difficulty=difficulty,
        )
        if ai_valid_count == 0:
            return QuestionGenerationResult(
                questions=normalized_questions,
                source="fallback",
                reason="Gemini не сгенерировал валидные вопросы, использованы запасные.",
            )

        if ai_valid_count < total:
            return QuestionGenerationResult(
                questions=normalized_questions,
                source="fallback",
                reason="Часть вопросов заменена на запасные из-за ошибок генерации.",
            )

        return QuestionGenerationResult(questions=normalized_questions, source="ai", reason=None)

    def _generate_gemini_content(
        self,
        genai_module: Any,
        genai_types: Any,
        topic: str,
        difficulty: GameDifficulty,
        total: int,
    ) -> str | None:
        client = genai_module.Client(api_key=self._api_key)
        response = client.models.generate_content(
            model=self._model,
            contents=self._build_prompt(topic=topic, difficulty=difficulty, total=total),
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )

        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text

        candidates = getattr(response, "candidates", None)
        if not candidates:
            return None

        first = candidates[0]
        content = getattr(first, "content", None)
        parts = getattr(content, "parts", None) if content is not None else None
        if isinstance(parts, list):
            chunks: list[str] = []
            for part in parts:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    chunks.append(part_text)
            return "\n".join(chunks).strip() or None

        return None

    def _build_prompt(self, *, topic: str, difficulty: GameDifficulty, total: int) -> str:
        difficulty_label = {
            GameDifficulty.EASY: "легкий",
            GameDifficulty.MEDIUM: "средний",
            GameDifficulty.HARD: "сложный",
        }[difficulty]
        return (
            "Сгенерируй набор вопросов для командной викторины.\n"
            f"Тема: {topic}\n"
            f"Сложность: {difficulty_label}\n"
            f"Количество вопросов: {total}\n"
            "Требования:\n"
            "- язык строго русский\n"
            "- каждый вопрос содержит поле text (строка)\n"
            "- каждый вопрос содержит поле options (массив ровно из 4 непустых строк)\n"
            "- каждый вопрос содержит поле correctOption (число 0..3)\n"
            "- нельзя использовать английские слова, если это не общепринятый термин\n"
            "- нельзя добавлять пояснения, markdown или текст вне JSON\n"
            "Верни строго JSON формата:\n"
            '{"questions":[{"text":"...","options":["...","...","...","..."],"correctOption":0}]}\n'
        )

    def _load_json(self, content: str) -> dict[str, Any] | None:
        raw = content.strip()
        if not raw:
            return None

        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                return loaded
        except json.JSONDecodeError:
            pass

        cleaned = raw
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or start >= end:
            return None

        candidate = cleaned[start : end + 1]
        try:
            loaded = json.loads(candidate)
            if isinstance(loaded, dict):
                return loaded
        except json.JSONDecodeError:
            return None
        return None

    def _normalize_generated(
        self,
        payload: dict[str, Any],
        *,
        total: int,
        topic: str,
        difficulty: GameDifficulty,
    ) -> tuple[list[GeneratedQuestion], int]:
        raw_items = payload.get("questions", [])
        if not isinstance(raw_items, list):
            raw_items = []

        fallback = self._fallback_questions(topic=topic, difficulty=difficulty, total=total)
        result: list[GeneratedQuestion] = []
        ai_valid_count = 0

        for index in range(total):
            base = fallback[index]
            item = raw_items[index] if index < len(raw_items) else {}

            if not isinstance(item, dict):
                item = {}

            raw_text = str(item.get("text", "")).strip()
            text = raw_text or base.text

            options = item.get("options", [])
            if not isinstance(options, list):
                options = []

            cleaned_options: list[str] = []
            local_valid = bool(raw_text)
            for option_index in range(4):
                fallback_option = base.options[option_index]
                candidate = options[option_index] if option_index < len(options) else fallback_option
                normalized_option = str(candidate).strip() or fallback_option
                if option_index < len(options) and str(candidate).strip():
                    pass
                else:
                    local_valid = False
                cleaned_options.append(normalized_option)

            raw_correct_option = item.get("correctOption", base.correct_option)
            if not isinstance(raw_correct_option, int) or raw_correct_option < 0 or raw_correct_option > 3:
                correct_option = base.correct_option
                local_valid = False
            else:
                correct_option = raw_correct_option

            if local_valid:
                ai_valid_count += 1

            result.append(
                GeneratedQuestion(
                    text=text,
                    options=cleaned_options,
                    correct_option=correct_option,
                )
            )
        return result, ai_valid_count

    def _fallback_questions(
        self,
        *,
        topic: str,
        difficulty: GameDifficulty,
        total: int,
    ) -> list[GeneratedQuestion]:
        normalized_topic = topic.casefold().strip()
        preferred = [item for item in RESERVE_QUESTIONS if self._matches_difficulty(item, difficulty)]
        topical_pool = [
            item
            for item in preferred
            if item.tags and any(tag in normalized_topic for tag in item.tags)
        ]
        neutral_pool = [item for item in preferred if item not in topical_pool]
        spillover_pool = [item for item in RESERVE_QUESTIONS if item not in preferred]

        random.shuffle(topical_pool)
        random.shuffle(neutral_pool)
        random.shuffle(spillover_pool)

        merged_pool = topical_pool + neutral_pool + spillover_pool
        if not merged_pool:
            raise RuntimeError("Reserve question bank is empty.")

        selected: list[ReserveQuestion] = []
        while len(selected) < total:
            next_item = merged_pool[len(selected) % len(merged_pool)]
            selected.append(next_item)

        return [
            GeneratedQuestion(
                text=item.text,
                options=list(item.options),
                correct_option=item.correct_option,
            )
            for item in selected
        ]

    def _matches_difficulty(self, item: ReserveQuestion, difficulty: GameDifficulty) -> bool:
        hard_tags = {"астрономия", "физика", "химия", "экономика"}
        easy_tags = {"география", "спорт", "россия", "страны"}
        item_tags = set(item.tags)
        if difficulty == GameDifficulty.EASY:
            return bool(item_tags.intersection(easy_tags)) or len(item.text) <= 62
        if difficulty == GameDifficulty.HARD:
            return bool(item_tags.intersection(hard_tags)) or len(item.text) >= 68
        return True

import streamlit as st
import os
import re
import random
import sys
from PIL import Image
import pandas as pd

# Настройка страницы
st.set_page_config(
    page_title="Программа тестирования",
    page_icon="📝",
    layout="wide"
)


class TestProgram:
    def __init__(self):
        """Инициализация программы тестирования"""
        # Настройка путей к файлам
        self.app_path = os.path.dirname(os.path.abspath(__file__))
        self.questions_file = os.path.join(self.app_path, "вопросы.txt")
        self.answers_file = os.path.join(self.app_path, "ответы.txt")
        self.correct_file = os.path.join(self.app_path, "правильные ответы.txt")
        self.images_folder = os.path.join(self.app_path, "картинки")

        # Инициализация состояния сессии
        self.init_session_state()

    def init_session_state(self):
        """Инициализация переменных в session_state"""
        if 'questions' not in st.session_state:
            st.session_state.questions = []
            st.session_state.original_questions = []
            st.session_state.question_mapping = {}
            st.session_state.current_question = 0
            st.session_state.score = 0
            st.session_state.user_answers = []
            st.session_state.user_answers_text = []
            st.session_state.correct_answers = []
            st.session_state.correct_answers_text = []
            st.session_state.saved_answers = {}
            st.session_state.test_started = False
            st.session_state.test_finished = False
            st.session_state.answer = None
            st.session_state.test_completed_early = False  # Флаг досрочного завершения

    def check_files_exist(self):
        """Проверка наличия всех файлов"""
        missing_files = []

        if not os.path.exists(self.questions_file):
            missing_files.append("вопросы.txt")
        if not os.path.exists(self.answers_file):
            missing_files.append("ответы.txt")
        if not os.path.exists(self.correct_file):
            missing_files.append("правильные ответы.txt")

        return missing_files

    def load_all_files(self):
        """Загрузка всех файлов"""
        missing_files = self.check_files_exist()

        if missing_files:
            return False, f"❌ Не найдены файлы: {', '.join(missing_files)}"

        try:
            with open(self.questions_file, 'r', encoding='utf-8') as f:
                questions_lines = f.readlines()

            with open(self.answers_file, 'r', encoding='utf-8') as f:
                answers_lines = f.readlines()

            with open(self.correct_file, 'r', encoding='utf-8') as f:
                correct_lines = f.readlines()

            st.session_state.original_questions = self.parse_files(
                questions_lines, answers_lines, correct_lines
            )

            if st.session_state.original_questions:
                self.shuffle_all()
                return True, f"✅ Загружено {len(st.session_state.original_questions)} вопросов"
            else:
                return False, "❌ Не удалось загрузить вопросы"

        except Exception as e:
            return False, f"❌ Ошибка загрузки: {str(e)}"

    def parse_files(self, questions_lines, answers_lines, correct_lines):
        """Парсинг файлов"""
        questions = []

        # Парсим вопросы
        question_texts = []
        question_numbers = []
        for line in questions_lines:
            line = line.strip()
            if line and re.match(r'^\d+\.', line):
                match = re.match(r'^(\d+)\.', line)
                if match:
                    num = int(match.group(1))
                    question_numbers.append(num)
                text = re.sub(r'^\d+\.\s*', '', line)
                question_texts.append(text)

        # Парсим ответы
        answer_groups = []
        current_group = []
        in_question = False

        for line in answers_lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('Вопрос'):
                if current_group:
                    answer_groups.append(current_group)
                current_group = []
                in_question = True
            elif in_question and re.match(r'^[a-e]\.', line.lower()):
                text = re.sub(r'^[a-e]\.\s*', '', line)
                current_group.append(text)

        if current_group:
            answer_groups.append(current_group)

        # Парсим правильные ответы
        correct_answers = []
        for line in correct_lines:
            line = line.strip()
            if line and re.match(r'^\d+\.', line):
                text = re.sub(r'^\d+\.\s*', '', line)
                answers = [ans.strip().lower() for ans in text.split(',')]
                formatted_answers = []
                for ans in answers:
                    if ans in ['a', 'а']:
                        formatted_answers.append('A')
                    elif ans in ['b', 'б']:
                        formatted_answers.append('B')
                    elif ans in ['c', 'в']:
                        formatted_answers.append('C')
                    elif ans in ['d', 'г']:
                        formatted_answers.append('D')
                    elif ans in ['e', 'д']:
                        formatted_answers.append('E')
                    elif '-' in ans:
                        formatted_answers.append(ans.upper())
                correct_answers.append(formatted_answers)

        # Объединяем
        num_questions = min(len(question_texts), len(answer_groups), len(correct_answers))

        for i in range(num_questions):
            question_text = question_texts[i]
            original_num = question_numbers[i] if i < len(question_numbers) else i + 1
            options = []

            answer_options = answer_groups[i] if i < len(answer_groups) else []

            # Проверяем наличие картинок (упрощенно)
            has_image = False
            image_path = None

            # Формируем варианты ответов
            for j, ans_text in enumerate(answer_options):
                option_letter = chr(ord('А') + j)
                options.append(f"{option_letter}. {ans_text}")

            correct = correct_answers[i] if i < len(correct_answers) else []

            questions.append({
                'question': question_text,
                'options': options,
                'answer': correct,
                'multiple': len(correct) > 1,
                'original_index': original_num,
                'has_image': has_image,
                'image_path': image_path
            })

        return questions

    def shuffle_all(self):
        """Перемешивает вопросы"""
        questions = st.session_state.original_questions.copy()

        # Перемешиваем вопросы
        indices = list(range(len(questions)))
        random.shuffle(indices)
        st.session_state.questions = [questions[i] for i in indices]

        # Сохраняем маппинг
        st.session_state.question_mapping = {}
        for new_idx, old_idx in enumerate(indices):
            st.session_state.question_mapping[new_idx] = old_idx

        # Перемешиваем ответы внутри каждого вопроса
        for q in st.session_state.questions:
            options_with_flags = []
            correct_answers = q['answer']

            for i, opt in enumerate(q['options']):
                option_letter = chr(ord('A') + i)
                was_correct = option_letter in correct_answers
                options_with_flags.append((opt, was_correct))

            random.shuffle(options_with_flags)

            new_options = []
            new_correct = []

            for j, (opt_text, was_correct) in enumerate(options_with_flags):
                new_letter = chr(ord('А') + j)
                clean_text = re.sub(r'^[А-Я]\.\s*', '', opt_text)
                new_options.append(f"{new_letter}. {clean_text}")

                if was_correct:
                    new_correct.append(chr(ord('A') + j))

            new_correct.sort()
            q['options'] = new_options
            q['answer'] = new_correct

    def finish_test_early(self):
        """Досрочное завершение теста и подсчет результатов"""
        # Сохраняем текущий ответ, если он есть
        if st.session_state.answer and st.session_state.current_question < len(st.session_state.questions):
            self.save_answer(st.session_state.current_question,
                             st.session_state.questions[st.session_state.current_question])

        # Устанавливаем флаг досрочного завершения
        st.session_state.test_completed_early = True
        st.session_state.test_finished = True
        st.session_state.test_started = False
        st.session_state.rerun = True

    def render_start_page(self):
        """Страница начала теста"""
        st.title("📝 Программа тестирования")
        st.markdown("---")

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown("### Добро пожаловать!")
            st.markdown("""
            Эта программа поможет вам проверить свои знания.

            **Как это работает:**
            - Вам будет предложено несколько вопросов
            - Выберите правильный ответ (один или несколько)
            - В конце вы увидите свои результаты
            - Можно досрочно завершить тест кнопкой **Завершить**

            **Форматы вопросов:**
            - ✅ Один правильный ответ
            - ✅ Несколько правильных ответов
            """)

            # Загружаем вопросы
            success, message = self.load_all_files()

            if success:
                st.success(message)
                if st.button("🚀 Начать тест", type="primary", use_container_width=True):
                    st.session_state.test_started = True
                    st.session_state.test_finished = False
                    st.session_state.test_completed_early = False
                    st.session_state.current_question = 0
                    st.session_state.score = 0
                    st.session_state.user_answers = []
                    st.session_state.user_answers_text = []
                    st.session_state.correct_answers = []
                    st.session_state.correct_answers_text = []
                    st.session_state.rerun = True
            else:
                st.error(message)

                # Инструкция по загрузке файлов
                with st.expander("📁 Как загрузить файлы с вопросами"):
                    st.markdown(f"""
                    **Требуемые файлы:**
                    1. `вопросы.txt` - список вопросов
                    2. `ответы.txt` - варианты ответов
                    3. `правильные ответы.txt` - правильные ответы

                    **Папка с картинками:** `картинки/` (опционально)

                    **Как добавить файлы:**
                    Эти файлы должны быть в одной папке с приложением на GitHub.
                    """)

    def render_question_page(self):
        """Страница с вопросом"""
        total = len(st.session_state.questions)
        current = st.session_state.current_question
        q = st.session_state.questions[current]

        original_idx = st.session_state.question_mapping.get(current, current)
        original_num = st.session_state.original_questions[original_idx]['original_index']

        # Верхняя панель с кнопкой завершения
        col_top1, col_top2, col_top3 = st.columns([3, 1, 1])
        with col_top1:
            st.title(f"📝 Вопрос {current + 1} из {total}")
        with col_top2:
            st.metric("Правильных ответов", st.session_state.score)
        with col_top3:
            # Кнопка досрочного завершения
            if st.button("🏁 Завершить", type="secondary", use_container_width=True):
                self.finish_test_early()

        # Прогресс-бар
        progress = (current) / total
        st.progress(progress)

        st.markdown(f"**Оригинальный номер вопроса:** {original_num}")
        st.markdown("---")

        # Текст вопроса
        st.markdown(f"### {q['question']}")

        # Информация о типе вопроса
        if q.get('multiple', False):
            st.info("📌 Можно выбрать несколько вариантов")
        else:
            st.info("📌 Выберите один вариант")

        # Варианты ответов
        st.markdown("#### Варианты ответа:")

        # Ключ для unique widget
        widget_key = f"q_{current}"

        if q.get('multiple', False):
            # Множественный выбор
            options = q['options']
            selected = st.multiselect(
                "Выберите правильные ответы:",
                options=options,
                key=widget_key
            )
            st.session_state.answer = selected
        else:
            # Одиночный выбор
            options = q['options']
            selected = st.radio(
                "Выберите правильный ответ:",
                options=options,
                key=widget_key,
                index=None
            )
            st.session_state.answer = selected

        st.markdown("---")

        # Кнопки навигации
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

        with col1:
            if current > 0:
                if st.button("← Назад", use_container_width=True):
                    # Сохраняем текущий ответ перед переходом
                    if st.session_state.answer:
                        self.save_answer(current, q)
                    st.session_state.current_question -= 1
                    st.session_state.rerun = True

        with col2:
            # Пустое место для баланса
            st.empty()

        with col3:
            if current < total - 1:
                if st.button("Далее →", type="primary", use_container_width=True):
                    if st.session_state.answer:
                        self.save_answer(current, q)
                    st.session_state.current_question += 1
                    st.session_state.rerun = True
            else:
                if st.button("Завершить тест", type="primary", use_container_width=True):
                    if st.session_state.answer:
                        self.save_answer(current, q)
                    st.session_state.test_finished = True
                    st.session_state.test_started = False
                    st.session_state.rerun = True

        with col4:
            # Дублируем кнопку завершения для удобства
            if st.button("🏁 Завершить сейчас", type="secondary", use_container_width=True):
                self.finish_test_early()

    def save_answer(self, question_idx, q):
        """Сохранение ответа"""
        answer = st.session_state.answer

        if not answer:
            return

        # Проверяем, не был ли уже сохранен ответ на этот вопрос
        # (чтобы избежать дублирования при возврате к вопросу)
        if question_idx < len(st.session_state.user_answers):
            # Если ответ уже был, обновляем его
            st.session_state.user_answers[question_idx] = self.format_answer_for_save(answer, q)
            st.session_state.user_answers_text[question_idx] = self.format_answer_for_display(answer, q)

            # Пересчитываем общий счет
            self.recalculate_score()
        else:
            # Если ответа еще не было, добавляем новый
            answer_str = self.format_answer_for_save(answer, q)
            answer_text = self.format_answer_for_display(answer, q)

            st.session_state.user_answers.append(answer_str)
            st.session_state.user_answers_text.append(answer_text)

            correct_str = ','.join(sorted(q['answer']))

            # Получаем текст правильных ответов
            correct_texts = []
            for c in q['answer']:
                idx = ord(c) - ord('A')
                if 0 <= idx < len(q['options']):
                    correct_texts.append(q['options'][idx])

            # Добавляем правильные ответы в соответствующие списки
            while len(st.session_state.correct_answers) <= question_idx:
                st.session_state.correct_answers.append('')
                st.session_state.correct_answers_text.append('')

            st.session_state.correct_answers[question_idx] = correct_str
            st.session_state.correct_answers_text[question_idx] = '; '.join(correct_texts)

            # Проверяем правильность и обновляем счет
            if self.check_answer_correctness(answer, q):
                st.session_state.score += 1

    def format_answer_for_save(self, answer, q):
        """Форматирует ответ для сохранения"""
        if q.get('multiple', False):
            answer_letters = []
            for a in answer:
                idx = q['options'].index(a)
                answer_letters.append(chr(ord('A') + idx))
            return ','.join(sorted(answer_letters))
        else:
            if answer:
                idx = q['options'].index(answer)
                return chr(ord('A') + idx)
            return ''

    def format_answer_for_display(self, answer, q):
        """Форматирует ответ для отображения"""
        if q.get('multiple', False):
            return '; '.join(answer)
        else:
            return answer if answer else ''

    def check_answer_correctness(self, answer, q):
        """Проверяет правильность ответа"""
        if not answer:
            return False

        if q.get('multiple', False):
            answer_letters = []
            for a in answer:
                idx = q['options'].index(a)
                answer_letters.append(chr(ord('A') + idx))
            return set(answer_letters) == set(q['answer'])
        else:
            if answer:
                idx = q['options'].index(answer)
                return chr(ord('A') + idx) in q['answer']
            return False

    def recalculate_score(self):
        """Пересчитывает общий счет на основе всех сохраненных ответов"""
        st.session_state.score = 0
        for i in range(len(st.session_state.user_answers)):
            if i < len(st.session_state.questions):
                q = st.session_state.questions[i]
                if i < len(st.session_state.user_answers):
                    answer_str = st.session_state.user_answers[i]
                    if answer_str:
                        if q.get('multiple', False):
                            if set(answer_str.split(',')) == set(q['answer']):
                                st.session_state.score += 1
                        else:
                            if answer_str in q['answer']:
                                st.session_state.score += 1

    def render_results_page(self):
        """Страница с результатами"""
        st.title("📊 Результаты теста")

        # Информация о досрочном завершении
        if st.session_state.get('test_completed_early', False):
            st.info("🏁 Тест завершен досрочно")

        st.markdown("---")

        total = len(st.session_state.questions)
        answered = len(st.session_state.user_answers)
        score = st.session_state.score
        percent = (score / total) * 100 if total > 0 else 0

        # Основная статистика
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Всего вопросов", total)
        with col2:
            st.metric("Отвечено", answered)
        with col3:
            st.metric("Правильных", f"{score}/{total}")
        with col4:
            st.metric("Процент", f"{percent:.1f}%")

        # Оценка
        col1, col2, col3 = st.columns(3)
        with col2:
            if percent >= 90:
                grade = "5 (Отлично)"
                grade_color = "green"
            elif percent >= 75:
                grade = "4 (Хорошо)"
                grade_color = "blue"
            elif percent >= 60:
                grade = "3 (Удовлетворительно)"
                grade_color = "orange"
            else:
                grade = "2 (Нужно повторить)"
                grade_color = "red"

            st.markdown(f"## :{grade_color}[{grade}]")

        st.markdown("---")

        # Детальный разбор ответов
        if answered > 0:
            st.markdown("### 📋 Детализация ответов")

            # Создаем DataFrame для удобного отображения
            results_data = []
            for i in range(total):
                original_idx = st.session_state.question_mapping.get(i, i)
                original_num = st.session_state.original_questions[original_idx]['original_index']

                if i < len(st.session_state.user_answers) and st.session_state.user_answers[i]:
                    user_answer = st.session_state.user_answers_text[i]
                    correct_answer = st.session_state.correct_answers_text[i]
                    is_correct = (st.session_state.user_answers[i] == st.session_state.correct_answers[i])
                else:
                    user_answer = "❌ Не отвечен"
                    correct_answer = st.session_state.correct_answers_text[i] if i < len(
                        st.session_state.correct_answers_text) else "Неизвестно"
                    is_correct = False

                results_data.append({
                    "№": i + 1,
                    "Оригинал №": original_num,
                    "Вопрос": st.session_state.questions[i]['question'][:50] + "...",
                    "Ваш ответ": user_answer,
                    "Правильный ответ": correct_answer,
                    "Результат": "✅" if is_correct else "❌"
                })

            df = pd.DataFrame(results_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Вопросы с ошибками
            mistakes = [r for r in results_data if r["Результат"] == "❌"]
            if mistakes:
                st.markdown("### ❌ Вопросы с ошибками")
                for mistake in mistakes:
                    with st.expander(f"Вопрос {mistake['№']} (оригинал №{mistake['Оригинал №']})"):
                        full_question = st.session_state.questions[mistake['№'] - 1]['question']
                        st.markdown(f"**{full_question}**")
                        st.markdown(f"❌ **Ваш ответ:** {mistake['Ваш ответ']}")
                        st.markdown(f"✅ **Правильный ответ:** {mistake['Правильный ответ']}")
            else:
                st.success("🎉 Поздравляем! Все ответы правильные!")
        else:
            st.warning("Вы не ответили ни на один вопрос")

        st.markdown("---")

        # Кнопка для нового теста
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔄 Пройти тест заново", type="primary", use_container_width=True):
                # Сброс состояния
                st.session_state.test_started = True
                st.session_state.test_finished = False
                st.session_state.test_completed_early = False
                st.session_state.current_question = 0
                st.session_state.score = 0
                st.session_state.user_answers = []
                st.session_state.user_answers_text = []
                st.session_state.correct_answers = []
                st.session_state.correct_answers_text = []
                st.session_state.saved_answers = {}
                st.session_state.rerun = True

                # Перемешиваем заново
                self.shuffle_all()

    def run(self):
        """Запуск приложения"""
        # Принудительный rerun при необходимости
        if st.session_state.get('rerun', False):
            st.session_state.rerun = False
            st.rerun()

        # Отображение соответствующей страницы
        if not st.session_state.test_started and not st.session_state.test_finished:
            self.render_start_page()
        elif st.session_state.test_started:
            if st.session_state.questions:
                self.render_question_page()
            else:
                st.error("Ошибка загрузки вопросов")
        elif st.session_state.test_finished:
            self.render_results_page()


# Запуск приложения
if __name__ == "__main__":
    app = TestProgram()
    app.run()
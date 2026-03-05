import streamlit as st
import os
import re
import random
import sys
from PIL import Image
import pandas as pd
import base64
from io import BytesIO

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
            st.session_state.test_completed_early = False
            # Кэш для картинок
            st.session_state.image_cache = {}

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

    def get_image_for_question(self, original_index, part=None):
        """Получить картинку для вопроса"""
        image_path = None

        if part is not None:
            base_name = f"{original_index}-{part}"
        else:
            base_name = str(original_index)

        # Проверяем различные возможные имена файлов
        possible_names = [
            f"{base_name}.png",
            f"{base_name}.jpg",
            f"{base_name}.jpeg",
            f"{base_name}.gif",
            f"вопрос_{base_name}.png",
            f"вопрос_{base_name}.jpg",
            f"img_{base_name}.png",
            f"image_{base_name}.jpg"
        ]

        # Проверяем в папке с картинками
        if os.path.exists(self.images_folder):
            for name in possible_names:
                test_path = os.path.join(self.images_folder, name)
                if os.path.exists(test_path):
                    image_path = test_path
                    break

        return image_path

    def load_and_display_image(self, image_path, caption=None, max_width=400, max_height=300):
        """Загружает и отображает изображение в Streamlit"""
        try:
            # Проверяем кэш
            cache_key = f"{image_path}_{max_width}_{max_height}"
            if cache_key in st.session_state.image_cache:
                return st.session_state.image_cache[cache_key]

            # Загружаем изображение
            if os.path.exists(image_path):
                image = Image.open(image_path)

                # Изменяем размер при необходимости
                width, height = image.size
                if width > max_width or height > max_height:
                    ratio = min(max_width / width, max_height / height)
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Сохраняем в кэш
                st.session_state.image_cache[cache_key] = image
                return image
            else:
                return None
        except Exception as e:
            st.warning(f"Не удалось загрузить изображение: {str(e)}")
            return None

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
        """Парсинг файлов с поддержкой картинок"""
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

            # Определяем тип вопроса с картинками
            image_as_question = False
            image_as_answer = False
            question_images = []
            answer_images = []

            # Специальные вопросы с картинками
            if original_num == 144:
                image_as_question = True
                for part in [1, 2]:
                    img_path = self.get_image_for_question(original_num, part)
                    if img_path:
                        question_images.append({
                            'path': img_path,
                            'part': part
                        })

            elif original_num == 129:
                image_as_answer = True
                for part in [1, 2, 3]:
                    img_path = self.get_image_for_question(original_num, part)
                    if img_path:
                        answer_images.append({
                            'path': img_path,
                            'part': part,
                            'text': f"Вариант {part}"
                        })

            # Формируем варианты ответов
            if not image_as_answer:
                for j, ans_text in enumerate(answer_options):
                    option_letter = chr(ord('А') + j)
                    options.append(f"{option_letter}. {ans_text}")
            else:
                options = answer_images

            correct = correct_answers[i] if i < len(correct_answers) else []

            # Основная картинка вопроса
            main_image_path = self.get_image_for_question(original_num)

            questions.append({
                'question': question_text,
                'options': options,
                'answer': correct,
                'multiple': len(correct) > 1,
                'original_index': original_num,
                'has_image': main_image_path is not None or len(question_images) > 0,
                'image_path': main_image_path,
                'image_as_question': image_as_question,
                'image_as_answer': image_as_answer,
                'question_images': question_images
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
            if q.get('image_as_answer', False):
                continue  # Не перемешиваем варианты с картинками

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
            - 🖼️ Вопросы с картинками
            """)

            # Информация о папке с картинками
            if os.path.exists(self.images_folder):
                images_count = len([f for f in os.listdir(self.images_folder)
                                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))])
                st.info(f"📁 Папка с картинками: {self.images_folder} ({images_count} изображений)")
            else:
                st.warning("📁 Папка с картинками не найдена")

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

                    **Папка с картинками:** `{self.images_folder}/` 

                    **Формат картинок:**
                    - Для вопроса №5: `5.png`, `5.jpg` и т.д.
                    - Для вопроса с несколькими картинками: `144-1.png`, `144-2.png`
                    """)

    def render_question_page(self):
        """Страница с вопросом с поддержкой картинок"""
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
            if st.button("🏁 Завершить", type="secondary", use_container_width=True):
                self.finish_test_early()

        # Прогресс-бар
        progress = (current) / total
        st.progress(progress)

        st.markdown(f"**Оригинальный номер вопроса:** {original_num}")
        st.markdown("---")

        # Отображение картинок вопроса (для вопроса 144)
        if q.get('image_as_question', False) and q.get('question_images'):
            st.markdown("### 📷 Изображения к вопросу:")

            # Создаем колонки для картинок
            num_images = len(q['question_images'])
            cols = st.columns(num_images)

            for idx, (col, img_data) in enumerate(zip(cols, q['question_images'])):
                with col:
                    image = self.load_and_display_image(img_data['path'], max_width=400, max_height=300)
                    if image:
                        st.image(image, caption=f"Часть {img_data['part']}", use_container_width=True)
                    else:
                        st.warning(f"Не удалось загрузить часть {img_data['part']}")

            st.markdown("---")

        # Отображение основной картинки вопроса
        elif q.get('has_image', False) and q.get('image_path'):
            st.markdown("### 📷 Изображение к вопросу:")
            image = self.load_and_display_image(q['image_path'], max_width=500, max_height=300)
            if image:
                st.image(image, use_container_width=True)
            st.markdown("---")

        # Текст вопроса
        st.markdown(f"### {q['question']}")

        # Информация о типе вопроса
        if q.get('image_as_answer', False):
            st.info("🖼️ Выберите правильную картинку")
        elif q.get('multiple', False):
            st.info("📌 Можно выбрать несколько вариантов")
        else:
            st.info("📌 Выберите один вариант")

        # Варианты ответов
        st.markdown("#### Варианты ответа:")

        if q.get('image_as_answer', False):
            # Варианты ответов в виде картинок
            num_options = len(q['options'])
            cols = st.columns(num_options)

            for idx, (col, opt) in enumerate(zip(cols, q['options'])):
                with col:
                    if isinstance(opt, dict) and 'path' in opt:
                        image = self.load_and_display_image(opt['path'], max_width=250, max_height=200)
                        if image:
                            st.image(image, caption=f"Вариант {opt['part']}", use_container_width=True)

                            # Кнопка выбора варианта
                            if st.button(f"Выбрать вариант {opt['part']}", key=f"img_opt_{current}_{idx}"):
                                st.session_state.answer = chr(ord('A') + idx)
                                self.save_answer(current, q)
                                st.rerun()
                        else:
                            st.warning(f"Вариант {opt['part']} не загружен")

        else:
            # Текстовые варианты ответов
            widget_key = f"q_{current}"

            if q.get('multiple', False):
                selected = st.multiselect(
                    "Выберите правильные ответы:",
                    options=q['options'],
                    key=widget_key
                )
                st.session_state.answer = selected
            else:
                selected = st.radio(
                    "Выберите правильный ответ:",
                    options=q['options'],
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
                    if st.session_state.answer:
                        self.save_answer(current, q)
                    st.session_state.current_question -= 1
                    st.session_state.rerun = True

        with col2:
            st.empty()

        with col3:
            if current < total - 1:
                if st.button("Далее →", type="primary", use_container_width=True):
                    if st.session_state.answer and not q.get('image_as_answer', False):
                        self.save_answer(current, q)
                    st.session_state.current_question += 1
                    st.session_state.rerun = True
            else:
                if st.button("Завершить тест", type="primary", use_container_width=True):
                    if st.session_state.answer and not q.get('image_as_answer', False):
                        self.save_answer(current, q)
                    st.session_state.test_finished = True
                    st.session_state.test_started = False
                    st.session_state.rerun = True

        with col4:
            if st.button("🏁 Завершить сейчас", type="secondary", use_container_width=True):
                self.finish_test_early()

    def save_answer(self, question_idx, q):
        """Сохранение ответа"""
        answer = st.session_state.answer

        if not answer:
            return

        # Для вопросов с картинками
        if q.get('image_as_answer', False):
            if isinstance(answer, str):
                answer_idx = ord(answer) - ord('A')
                if 0 <= answer_idx < len(q['options']):
                    opt = q['options'][answer_idx]
                    if isinstance(opt, dict):
                        answer_text = f"Вариант {opt['part']}"
                        answer_str = answer
                    else:
                        answer_text = answer
                        answer_str = answer
                else:
                    return
            else:
                return
        else:
            # Для текстовых вопросов
            if q.get('multiple', False):
                answer_letters = []
                answer_texts = []
                for a in answer:
                    idx = q['options'].index(a)
                    answer_letters.append(chr(ord('A') + idx))
                    answer_texts.append(a)

                answer_str = ','.join(sorted(answer_letters))
                answer_text = '; '.join(answer_texts)
            else:
                if answer:
                    idx = q['options'].index(answer)
                    answer_str = chr(ord('A') + idx)
                    answer_text = answer
                else:
                    return

        # Сохраняем ответ
        if question_idx < len(st.session_state.user_answers):
            st.session_state.user_answers[question_idx] = answer_str
            st.session_state.user_answers_text[question_idx] = answer_text
            self.recalculate_score()
        else:
            st.session_state.user_answers.append(answer_str)
            st.session_state.user_answers_text.append(answer_text)

            correct_str = ','.join(sorted(q['answer']))

            correct_texts = []
            for c in q['answer']:
                idx = ord(c) - ord('A')
                if 0 <= idx < len(q['options']):
                    if q.get('image_as_answer', False):
                        if idx < len(q['options']) and isinstance(q['options'][idx], dict):
                            correct_texts.append(f"Вариант {q['options'][idx]['part']}")
                        else:
                            correct_texts.append(c)
                    else:
                        correct_texts.append(q['options'][idx])

            while len(st.session_state.correct_answers) <= question_idx:
                st.session_state.correct_answers.append('')
                st.session_state.correct_answers_text.append('')

            st.session_state.correct_answers[question_idx] = correct_str
            st.session_state.correct_answers_text[question_idx] = '; '.join(correct_texts)

            if self.check_answer_correctness(answer, q):
                st.session_state.score += 1

    def check_answer_correctness(self, answer, q):
        """Проверяет правильность ответа"""
        if not answer:
            return False

        if q.get('image_as_answer', False):
            if isinstance(answer, str):
                return answer in q['answer']
            return False
        elif q.get('multiple', False):
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

        if st.session_state.get('test_completed_early', False):
            st.info("🏁 Тест завершен досрочно")

        st.markdown("---")

        total = len(st.session_state.questions)
        answered = len(st.session_state.user_answers)
        score = st.session_state.score
        percent = (score / total) * 100 if total > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Всего вопросов", total)
        with col2:
            st.metric("Отвечено", answered)
        with col3:
            st.metric("Правильных", f"{score}/{total}")
        with col4:
            st.metric("Процент", f"{percent:.1f}%")

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

        if answered > 0:
            st.markdown("### 📋 Детализация ответов")

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

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔄 Пройти тест заново", type="primary", use_container_width=True):
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
                self.shuffle_all()

    def run(self):
        """Запуск приложения"""
        if st.session_state.get('rerun', False):
            st.session_state.rerun = False
            st.rerun()

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
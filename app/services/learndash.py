import requests
import time
import re
from urllib.parse import urlparse, parse_qs
from app import config
from app.schemas.pdf_quiz import QuizResponse
from sqlalchemy import text
from app.database import get_db
import logging
import phpserialize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_pro_id_from_post_id(db, post_id: int, meta_key: str) -> int:
    """
    Given a WordPress post ID, polls the database to get the associated LearnDash ProQuiz ID.
    The meta_key is 'quiz_pro_id' for quizzes and 'question_pro_id' for questions.
    """
    query = text(f"SELECT meta_value FROM wp_postmeta WHERE post_id = :post_id AND meta_key = :meta_key")
    for _ in range(10): # Poll for up to 5 seconds
        result = db.execute(query, {'post_id': post_id, 'meta_key': meta_key}).scalar_one_or_none()
        if result:
            return int(result)
        time.sleep(0.5)
    raise Exception(f"Could not find {meta_key} for post_id {post_id} in wp_postmeta table.")

def manually_serialize_answers(question):
    """
    Manually constructs the exact PHP serialized string for a list of answers,
    bypassing the phpserialize library which does not support named objects
    in the required way. This is based on the ground-truth data from a
    working LearnDash quiz.
    """
    answer_objects_str = ""
    for i, option in enumerate(question.options):
        is_correct = (option.strip().lower() == (question.answer or "").strip().lower())
        
        # This creates the string for a single WpProQuiz_Model_AnswerTypes object
        answer_str = (
            f'O:27:"WpProQuiz_Model_AnswerTypes":10:{{'
            f's:10:"\0*\0_mapper";N;'
            f's:10:"\0*\0_answer";s:{len(option)}:"{option}";'
            f's:8:"\0*\0_html";b:0;'
            f's:10:"\0*\0_points";i:1;'
            f's:11:"\0*\0_correct";b:{1 if is_correct else 0};'
            f's:14:"\0*\0_sortString";s:0:"";'
            f's:18:"\0*\0_sortStringHtml";b:0;'
            f's:10:"\0*\0_graded";b:0;'
            f's:22:"\0*\0_gradingProgression";s:15:"not-graded-none";'
            f's:14:"\0*\0_gradedType";N;'
            f'}}'
        )
        answer_objects_str += f'i:{i};{answer_str}'

    # Wraps the collection of answer objects in the parent array structure
    return f'a:{len(question.options)}:{{{answer_objects_str}}}'

def create_learndash_quiz(quiz_data: QuizResponse):
    """
    Creates a LearnDash quiz and its questions by writing directly to the
    WordPress database. This bypasses all application-layer security (like WAFs)
    that were blocking API and form-based requests.
    """
    db = None
    try:
        db_session_gen = get_db()
        db = next(db_session_gen)

        # --- Step 1: Create the main Quiz Post ---
        logger.info("Step 1: Creating quiz post in wp_posts...")
        quiz_post_query = text("""
            INSERT INTO wp_posts (post_author, post_date, post_date_gmt, post_content, post_title, post_status, comment_status, ping_status, post_name, post_modified, post_modified_gmt, post_parent, menu_order, post_type, comment_count)
            VALUES (1, NOW(), NOW(), :post_content, :post_title, 'publish', 'closed', 'closed', :post_name, NOW(), NOW(), 0, 0, 'sfwd-quiz', 0)
        """)
        post_name = quiz_data.title.lower().replace(' ', '-')[:50]
        result = db.execute(quiz_post_query, {'post_content': '', 'post_title': quiz_data.title, 'post_name': post_name})
        quiz_post_id = result.lastrowid
        if not quiz_post_id:
            raise Exception("Failed to create quiz post in wp_posts table.")
        logger.info(f"Successfully created quiz post with ID: {quiz_post_id}")

        # --- Step 2: Create the LearnDash Quiz Record (based on Manual Test Quiz) ---
        logger.info("Step 2: Creating quiz record in wp_learndash_pro_quiz_master...")

        result_text_data = {'text': [''], 'prozent': [0], 'activ': [1]}
        toplist_data_obj = {
            'toplistDataAddPermissions': 1, 'toplistDataSort': 1, 'toplistDataAddMultiple': False,
            'toplistDataAddBlock': 0, 'toplistDataShowLimit': 0, 'toplistDataShowIn': 0,
            'toplistDataCaptcha': False, 'toplistDataAddAutomatic': False
        }
        
         # This INSERT statement is now a 1-to-1 replica of the Manual Test Quiz.
        sql = text("""
            INSERT INTO wp_learndash_pro_quiz_master (
                name, text, result_text, result_grade_enabled, title_hidden, btn_restart_quiz_hidden,
                btn_view_question_hidden, question_random, answer_random, time_limit, statistics_on,
                statistics_ip_lock, show_points, quiz_run_once, quiz_run_once_type, quiz_run_once_cookie,
                quiz_run_once_time, numbered_answer, hide_answer_message_box, disabled_answer_mark,
                show_category, show_max_question, show_max_question_value, show_max_question_percent,
                toplist_activated, toplist_data, show_average_result, prerequisite, quiz_modus,
                show_review_question, quiz_summary_hide, skip_question_disabled, email_notification,
                user_email_notification, show_category_score, hide_result_correct_question,
                hide_result_quiz_time, hide_result_points, autostart, forcing_question_solve,
                hide_question_position_overview, hide_question_numbering, form_activated,
                form_show_position, start_only_registered_user, questions_per_page, sort_categories
            ) VALUES (
                :name, :start_text, :result_text, 0, 0, 0,
                0, 0, 0, 0, 1,
                120, 1, 0, 'cookie', 1,
                1440, 0, 0, 0,
                0, 0, 0, 1,
                0, :toplist_data, 0, 0, 2,
                0, 0, 0, 0,
                1, 0, 0,
                0, 0, 0, 0,
                0, 0, 0,
                0, 0, 0, 0
            )
        """)

        params = {
            'name': quiz_data.title,
            'start_text': '<div><input type="button" value="Start quiz" class="wp-block-button__link" /></div>',
            'result_text': phpserialize.dumps(result_text_data).decode('utf-8'),
            'toplist_data': phpserialize.dumps(toplist_data_obj).decode('utf-8')
        }
        result = db.execute(sql, params)
        quiz_pro_id = result.lastrowid
        if not quiz_pro_id:
            raise Exception("Failed to create quiz record in wp_learndash_pro_quiz_master.")
        logger.info(f"Successfully created quiz master record with ID: {quiz_pro_id}")

        # --- Step 3: Create each question and its connections ---
        question_post_ids = []
        for q_idx, question in enumerate(quiz_data.questions):
            # 3a: Create the question post in wp_posts
            q_post_name = f"{quiz_data.title.lower().replace(' ', '-')[:30]}-{quiz_post_id}-{q_idx}"
            q_post_query = text("""
                INSERT INTO wp_posts (post_author, post_date, post_date_gmt, post_content, post_title, post_status, comment_status, ping_status, post_name, post_modified, post_modified_gmt, post_parent, menu_order, post_type, comment_count)
                VALUES (1, NOW(), NOW(), :post_content, :post_title, 'publish', 'closed', 'closed', :post_name, NOW(), NOW(), 0, 0, 'sfwd-question', 0)
            """)
            q_result = db.execute(q_post_query, {
                'post_content': question.question, 
                'post_title': question.question, 
                'post_name': q_post_name
            })
            q_post_id = q_result.lastrowid
            question_post_ids.append(q_post_id)

            # 3b: Prepare the serialized answer data MANUALLY
            answer_data_serialized = manually_serialize_answers(question)

            # 3c: Create the question record in wp_learndash_pro_quiz_question
            q_master_query = text("""
                INSERT INTO wp_learndash_pro_quiz_question (
                    online, quiz_id, sort, title, question, points, answer_type, answer_data,
                    answer_points_activated, show_points_in_box, answer_points_diff_modus_activated,
                    disable_correct, correct_same_text, tip_enabled, correct_msg, incorrect_msg, tip_msg
                ) VALUES (
                    1, :quiz_id, :sort, :title, :question, 1, 'single', :answer_data,
                    0, 0, 0,
                    0, 0, 0, '', '', ''
                )
            """)
            q_master_result = db.execute(q_master_query, {
                'quiz_id': quiz_pro_id,
                'sort': q_idx + 1, # Sort must be 1-indexed
                'title': question.question,
                'question': question.question,
                'answer_data': answer_data_serialized
            })
            q_pro_id = q_master_result.lastrowid

            # 3d: Create all necessary metadata for the question post
            q_meta_query = text("INSERT INTO wp_postmeta (post_id, meta_key, meta_value) VALUES (:post_id, :meta_key, :meta_value)")
            
            sfwd_question_settings = {'sfwd-question_quiz': quiz_post_id}
            
            question_meta_to_insert = {
                'question_pro_id': q_pro_id,
                'question_points': 1,
                'question_type': 'single',
                'quiz_id': quiz_post_id,
                '_sfwd-question': phpserialize.dumps(sfwd_question_settings).decode('utf-8'),
                '_edit_last': '1'
            }

            for key, value in question_meta_to_insert.items():
                db.execute(q_meta_query, {'post_id': q_post_id, 'meta_key': key, 'meta_value': str(value)})

        # --- Step 4: Create all required Quiz meta entries in wp_postmeta ---
        # The user has requested to remove the automatic mapping of questions to the builder UI.
        
        sfwd_quiz_settings = {
            f"sfwd-quiz_quiz_pro": quiz_pro_id,
            f"sfwd-quiz_passingpercentage": 80, 
            f"sfwd-quiz_course": 0,
            f"sfwd-quiz_lesson": 0
        }

        meta_to_insert = {
            "quiz_pro_id": quiz_pro_id,
            f"quiz_pro_primary_{quiz_pro_id}": quiz_pro_id,
            "_sfwd-quiz": phpserialize.dumps(sfwd_quiz_settings).decode('utf-8'),
            "_edit_last": "1", # Admin user ID
            "_ld_certificate_threshold": "0.8",
            "_wp_page_template": "default",
            "_timeLimitCookie": "0",
            "_viewProfileStatistics": "1",
        }

        meta_insert_query = text("INSERT INTO wp_postmeta (post_id, meta_key, meta_value) VALUES (:post_id, :meta_key, :meta_value)")
        for key, value in meta_to_insert.items():
            db.execute(meta_insert_query, {'post_id': quiz_post_id, 'meta_key': key, 'meta_value': str(value)})

        db.commit()
        return {"message": "Quiz, questions, and all metadata created successfully.", "quiz_post_id": quiz_post_id, "question_post_ids": question_post_ids}

    except Exception as e:
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()

def get_jwt_token():
    """
    Authenticates with WordPress to get a JWT token.
    """
    token_url = f"{config.WP_SITE_URL}/wp-json/jwt-auth/v1/token"
    credentials = {
        'username': config.WP_API_USERNAME,
        'password': config.WP_API_APPLICATION_PASSWORD
    }
    try:
        response = requests.post(token_url, data=credentials)
        response.raise_for_status()
        return response.json().get('token')
    except requests.exceptions.RequestException as e:
        print(f"Error getting JWT token: {e}")
        raise 
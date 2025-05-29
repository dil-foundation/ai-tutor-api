# AI English Tutor App — Backend (FastAPI)

Welcome to the backend of the **AI English Tutor App**, a cutting-edge language learning platform designed for Urdu-speaking learners to master English through real-time conversational interaction, pronunciation evaluation, AI-generated fluency feedback, and a personalized learning journey.

Architected and implemented the complete backend using **FastAPI**, with focus on real-time translation, TTS/STT integration, GPT-4-based feedback generation, pronunciation scoring, and stage-wise AI tutoring.

---

## Key Features Implemented

### 1. 🔁 Real-Time Urdu ➝ English Translator with Fluency Feedback
- **STT (Speech-to-Text)** for Urdu and English via Whisper API
- **GPT-4** powered translation, sentence correction, and response generation
- **Fluency Feedback Engine** that analyzes:
  - Grammar
  - Vocabulary
  - Sentence structure
  - Speech speed and clarity


## How to Run the Project:

**1. Clone the Repository**

git clone https://github.com/yourusername/ai_tutor_backend.git
cd ai_tutor_backend

**2. Create and Activate a Virtual Environment** 

python -m venv venv
source venv/bin/activate     # On Windows: venv\Scripts\activate

**3. Install Dependencies**

pip install -r requirements.txt

**4. Run the FastAPI Server**

uvicorn app.main:app --reload
The server will start at: http://127.0.0.1:8000

Interactive API Docs available at: http://127.0.0.1:8000/docs


## Project Structure:

ai_tutor_backend/
│
├── app/
│   ├── main.py
│   ├── .env
│   ├── config.py
│   ├── schemas/
│   │   └── user_input.py
│   ├── services/
│   │   ├── translation.py
│   │   ├── tts.py
│   │   ├── stt.py
│   │   ├── whisper_scoring.py
│   │   └── feedback.py
│   └── routes/
│       └── translator.py
│   └── credentials/
│       └── google-credentials.json
│
├── requirements.txt
└── README.md

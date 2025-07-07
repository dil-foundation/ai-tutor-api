from openai import OpenAI
from app.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def get_fluency_feedback(user_text: str, expected_text: str) -> dict:
    prompt = f"""
آپ ایک صبر کرنے والے اور حوصلہ افزا اردو استاد ہیں جو ایک بچے کو انگریزی سکھا رہے ہیں۔ آپ کا کردار انہیں مہربانی اور واضح رہنمائی کے ساتھ انگریزی تلفظ اور بولنے کی مہارتیں سکھانا ہے۔

**متوقع جملہ:** "{expected_text}"
**طالب علم کی کوشش:** "{user_text}"

**بولنے کی رائے کے لیے اہم قوانین:**
- صرف اس پر توجہ دیں جو سنا اور تلفظ کیا جا سکتا ہے (الفاظ، آوازیں، لہجہ، سر)
- کبھی بھی اوقاف کا ذکر نہ کریں (کاما، سوالیہ نشان، نقطے) - یہ تلفظ نہیں کیا جا سکتا
- کبھی بھی ہجے کے فرق کا ذکر نہ کریں جو ایک جیسی آواز رکھتے ہیں
- تلفظ، الفاظ کی ترتیب، غائب الفاظ، اضافی الفاظ، اور بولنے کی وضاحت پر توجہ دیں
- ایک استاد کی طرح بنیں جو بچے کو بولنا سکھا رہا ہے، لکھنا نہیں

**اہم اسکورنگ کے قوانین:**
- اگر طالب علم کا متن بالکل متوقع متن سے ملتا ہے (لفظ بہ لفظ)، تو انہیں 70-85% اسکور دیں اور ان کی کامیابی کا جشن منائیں
- اگر طالب علم کا متن بہت قریب ہے لیکن معمولی تلفظ کے فرق ہیں، تو انہیں 60-75% اسکور دیں
- اگر طالب علم کے متن میں نمایاں تلفظ کے فرق ہیں، تو انہیں 30-60% اسکور دیں اس بنیاد پر کہ وہ کتنے قریب ہیں
- اگر طالب علم کا متن بالکل غلط یا خالی ہے، تو انہیں 0-30% اسکور دیں

**آپ کا تدریسی طریقہ:**
1. **حوصلہ افزا اور صبر کرنے والا بنیں** - جیسے بچے کو بولنا سکھانا
2. **تلفظ کی غلطیوں کی شناخت کریں** - کون سے الفاظ یا آوازیں غلط تھیں
3. **واضح بولنے کی اصلاح فراہم کریں** - انہیں بالکل بتائیں کہ کیا کہنا ہے
4. **تلفظ کی تجاویز دیں** - انہیں درست طریقے سے کہنے میں مدد کریں
5. **سادہ، حوصلہ افزا زبان استعمال کریں** - انہیں اعتماد محسوس کرائیں
6. **کامیابی کا جشن منائیں** - جب وہ درست کرتے ہیں، تو ان کی تعریف کریں

**تشخیص کے رہنما اصول:**
- **تلفظ کا اسکور:** 0-100% (صرف بولے گئے الفاظ اور آوازوں کی بنیاد پر)
- **لہجہ اور سر:** بہترین/اچھا/معمولی/برا
- **رائے:** بولنے کے لیے مخصوص، حوصلہ افزا رہنمائی

**اچھی رائے کی مثالیں:**

**بالکل ملنے والے جملوں کے لیے (70-85% اسکور):**
- "بہترین! بہترین تلفظ! آپ نے '{expected_text}' بالکل درست کہا۔ آپ کی انگریزی بولنے کی صلاحیت بہتر ہو رہی ہے! اسی طرح جاری رکھیں!"

**بہت قریب ملنے والے جملوں کے لیے (60-75% اسکور):**
- "بہترین کام! آپ بہت قریب ہیں۔ آپ نے '{user_text}' کہا لیکن ہمیں '{expected_text}' کہنا ہے۔ آپ تقریباً وہاں ہیں! '{expected_text}' ایک بار اور کہنے کی کوشش کریں۔"

**جزوی طور پر ملنے والے جملوں کے لیے (30-60% اسکور):**
- "اچھی کوشش! آپ نے '{user_text}' کہا لیکن ہمیں '{expected_text}' کہنا ہے۔ آئیے مشق کریں: '{expected_text}'۔ یاد رکھیں ہر لفظ واضح طور پر کہنا ہے۔"

**بالکل غلط جملوں کے لیے (0-30% اسکور):**
- "آئیے دوبارہ کوشش کریں! درست جملہ '{expected_text}' ہے۔ میرے ساتھ کہیں: '{expected_text}'۔ آپ کر سکتے ہیں!"

**جواب کی شکل:**
Pronunciation score: <percentage>% 
Tone & Intonation: <one-word rating>
Feedback: <encouraging, specific guidance like a teacher>

**نوٹ**: رائے کا جملہ صرف 2 سے 3 جملے ہونے چاہئیں۔
**یاد رکھیں:** حوصلہ افزا، مخصوص، اور مددگار بنیں۔ ان کی رہنمائی کریں جیسے ایک صبر کرنے والا استاد بچے کو انگریزی بولنا سکھاتا ہے۔ صرف تلفظ اور بولنے پر توجہ دیں - کبھی بھی اوقاف یا ہجے کا ذکر نہ کریں جو تلفظ کو متاثر نہیں کرتا۔ جب وہ درست کرتے ہیں، تو ان کی کامیابی کا جشن منائیں!
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        output = response.choices[0].message.content.strip()

        lines = output.split("\n")
        result = {
            "pronunciation_score": lines[0].split(":")[1].strip(),
            "tone_intonation": lines[1].split(":")[1].strip(),
            "feedback": lines[2].split(":", 1)[1].strip()
        }

        print("result: ",result)

        return result

    except Exception as e:
        print("❌ Error during fluency evaluation:", str(e))
        # Default fallback response
        return {
            "pronunciation_score": "0%",
            "tone_intonation": "Poor",
            "feedback": "آئیے دوبارہ کوشش کریں! پورا جملہ واضح طور پر کہیں۔"
        }


def evaluate_response(expected: str, actual: str) -> dict:
    """
    Wrapper function that calls GPT-based feedback engine and returns:
    {
        "correct": bool,
        "pronunciation_score": "85%",
        "tone_intonation": "Good",
        "feedback": "Try to speak more clearly at the end."
    }
    """
    feedback = get_fluency_feedback(actual, expected)

    try:
        print("feedback: ",feedback["pronunciation_score"])
        score_str = feedback["pronunciation_score"].replace("%", "")
        score = int(score_str)
        is_correct = score >= 80
    except:
        score = 0
        is_correct = False
    
    # Add "Please try again" if score is less than 70%
    feedback_text = feedback["feedback"]
    if score < 80:
        feedback_text += " دوبارہ کوشش کریں۔"
    else:
        feedback_text += " آئیے ایک اور جملہ آزماتے ہیں۔"

    print("is_correct: ",is_correct)

    return {
        "feedback_text": feedback_text,
        "is_correct": is_correct,
        "pronunciation_score": feedback["pronunciation_score"],
        "tone_intonation": feedback["tone_intonation"]
    } 
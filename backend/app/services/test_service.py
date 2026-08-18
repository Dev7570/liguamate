"""Test Service — IELTS/TOEFL evaluation logic using LLM"""

import json
from app.services.ai_service import get_ai_client_and_model

# ─── Prompts & Question Banks ────────────────────────────────────────────────

IELTS_PROMPTS = {
    "part1": [
        "Talk about your hometown. Where is it and what do you like about it?",
        "Describe your daily routine. What do you usually do in the morning?",
        "Do you enjoy cooking? What kinds of food do you like to make?",
        "Talk about a sport or physical activity you enjoy.",
        "Describe your favorite season and explain why you prefer it.",
    ],
    "part2": [
        "Describe a memorable trip you took. You should say: where you went, who you went with, what you did, and why it was memorable.",
        "Describe an important decision you made in your life. You should say: what the decision was, when you made it, how you made it, and how it affected your life.",
        "Describe a book or movie that had a big impact on you. You should say: what it was, what it was about, why you chose it, and what impact it had.",
        "Describe a person who has inspired you. You should say: who this person is, how you know them, what they have done, and why they inspire you.",
    ],
    "part3": [
        "How do you think technology has changed the way people communicate compared to 20 years ago? What are the advantages and disadvantages?",
        "Some people say that learning a foreign language is becoming less important due to technology. Do you agree or disagree? Why?",
        "How important is higher education in today's society? Do you think everyone should go to university?",
        "What are the main causes of stress in modern life? How can people manage stress effectively?",
    ]
}

TOEFL_PROMPTS = {
    "task1": [
        "Talk about a place in your community that is important to you. Describe it and explain why it is important.",
        "What is your favorite time of year? Describe it and explain why you prefer it.",
        "Describe an activity you enjoy doing in your free time. Explain why you enjoy it.",
    ],
    "task2": [
        "Do you agree or disagree: It is better to work in a team than to work independently. Use specific reasons and examples to support your answer.",
        "Some people prefer to live in a large city; others prefer to live in a small town. Which do you prefer and why?",
        "Do you think it is more important to enjoy your work or to earn a high salary? Explain your preference.",
    ]
}

IELTS_RUBRIC = """
Evaluate the following IELTS Speaking response using the official IELTS band descriptors.
Score each criterion on the IELTS scale (0.0–9.0, multiples of 0.5):

1. Fluency & Coherence: flow of speech, use of discourse markers, logical sequencing
2. Lexical Resource: range and accuracy of vocabulary, use of collocations and idioms
3. Grammatical Range & Accuracy: variety of structures, frequency of errors
4. Pronunciation: clarity, stress, intonation, accent intelligibility
"""

TOEFL_RUBRIC = """
Evaluate the following TOEFL Speaking response using the official TOEFL rubric.
Score each criterion on a scale of 0–4 (then multiply to 0–30):

1. Delivery (Fluency & Pronunciation): clarity, rhythm, pacing, naturalness
2. Language Use (Lexical & Grammar): accuracy, complexity of language structures
3. Topic Development (Coherence & Content): organization, detail, completeness
"""


async def evaluate_speaking_test(
    test_type: str,
    part: str,
    transcript: str,
    prompt_used: str,
) -> dict:
    """Use the LLM to evaluate a speaking test response and return structured scores."""
    client, model = get_ai_client_and_model()

    is_ielts = test_type.lower() == "ielts"
    rubric = IELTS_RUBRIC if is_ielts else TOEFL_RUBRIC
    scale = "0.0–9.0" if is_ielts else "0–30"

    system = f"""You are a certified {test_type.upper()} examiner. Evaluate speaking responses objectively and return only valid JSON.{rubric}"""

    user_msg = f"""Test: {test_type.upper()} {part.upper()}
Question: "{prompt_used}"
Candidate's response: "{transcript}"

Return ONLY this JSON (no markdown):
{{
  "band_score": <overall score as float {scale}>,
  "fluency": <float {scale}>,
  "lexical": <float {scale}>,
  "grammar": <float {scale}>,
  "pronunciation": <float {scale}>,
  "strengths": "<2 specific things done well>",
  "improvements": "<2 specific areas to improve with examples>",
  "overall_feedback": "<3-4 sentence comprehensive feedback as an encouraging examiner>"
}}"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("`"):
            content = content.split("`")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except (json.JSONDecodeError, Exception) as e:
        # Return fallback scores
        default_score = 5.0 if is_ielts else 15.0
        return {
            "band_score": default_score,
            "fluency": default_score,
            "lexical": default_score,
            "grammar": default_score,
            "pronunciation": default_score,
            "strengths": "Good attempt at the task.",
            "improvements": "Try to expand your answers with more detail and examples.",
            "overall_feedback": f"You completed the {test_type.upper()} speaking task. Keep practicing to improve your fluency and vocabulary range!"
        }


def get_prompts_for_test(test_type: str, part: str) -> list[str]:
    """Get available prompts for a given test type and part."""
    import random
    if test_type.lower() == "ielts":
        prompts = IELTS_PROMPTS.get(part.lower(), IELTS_PROMPTS["part1"])
    else:
        prompts = TOEFL_PROMPTS.get(part.lower(), TOEFL_PROMPTS["task1"])
    return random.sample(prompts, min(3, len(prompts)))

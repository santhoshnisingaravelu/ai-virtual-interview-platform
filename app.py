import os
import json
import requests
from flask import Flask, render_template, request

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-before-production")

QUESTIONS = {
    "Python": [
        "Explain the difference between a list and a tuple in Python.",
        "What is a dictionary, and when would you use one?",
        "How would you handle an exception in Python?"
    ],
    "Web Development": [
        "What is the difference between HTML, CSS, and JavaScript?",
        "What happens when a browser sends an HTTP request to a server?",
        "How would you make a website responsive?"
    ],
    "Data Analytics": [
        "How would you handle missing values in a dataset?",
        "Explain the difference between mean and median.",
        "How would you communicate a data insight to a non-technical stakeholder?"
    ],
    "General": [
        "Tell me about yourself and your technical background.",
        "Describe a project you are proud of and your contribution.",
        "Tell me about a challenge you faced and how you solved it."
    ]
}

def evaluate_locally(question, answer):
    """Transparent baseline rubric; not an AI-generated or validated hiring decision."""
    words = answer.split()
    word_count = len(words)
    keywords = ["because", "example", "approach", "result", "tested", "implemented",
                "data", "function", "solution", "improved", "first", "then"]
    hits = sum(1 for k in keywords if k in answer.lower())
    length_score = min(40, int(word_count / 2))
    detail_score = min(35, hits * 7)
    structure_score = 25 if word_count >= 35 and any(x in answer.lower() for x in ["first", "then", "finally", "for example"]) else min(25, word_count // 3)
    score = min(100, length_score + detail_score + structure_score)
    if word_count < 8:
        feedback = "Your answer is very short. Add a direct explanation, a practical example, and the result."
    elif score >= 75:
        feedback = "Your answer has useful detail. Strengthen it further with precise technical terms and a measurable example where relevant."
    elif score >= 45:
        feedback = "You have a starting point. Improve the answer by explaining your approach step by step and adding a concrete example."
    else:
        feedback = "Try answering in three parts: direct answer, explanation or example, and outcome."
    return {
        "score": score,
        "feedback": feedback,
        "strengths": ["Answer submitted", "Response length: " + str(word_count) + " words"],
        "improvements": ["Add a specific example", "Explain your reasoning and outcome"],
        "method": "Local rubric (AI API not configured)"
    }

def evaluate_with_groq(question, answer, role, category):
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    prompt = f"""You are a supportive interview practice coach. Assess practice only, not as a hiring decision.
Role: {role}
Category: {category}
Question: {question}
Candidate answer: {answer}
Return ONLY JSON with keys: score (integer 0-100), feedback (2-4 sentences),
strengths (array of 2 strings), improvements (array of 2 strings).
Assess relevance, clarity, reasoning and examples. Do not infer personal traits or protected characteristics.
If the answer is blank, give score 0 and ask the candidate to answer."""
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "messages": [
                    {"role": "system", "content": "You evaluate practice interview answers fairly and return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            },
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        result = json.loads(data["choices"][0]["message"]["content"])
        score = max(0, min(100, int(result.get("score", 0))))
        return {
            "score": score,
            "feedback": str(result.get("feedback", "Review your answer and try again.")),
            "strengths": result.get("strengths", [])[:3],
            "improvements": result.get("improvements", [])[:3],
            "method": "AI feedback (Groq)"
        }
    except Exception:
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    question = ""
    answer = ""
    candidate = ""
    role = "Software Developer"
    category = "Python"
    if request.method == "POST":
        candidate = request.form.get("candidate", "").strip()[:100]
        role = request.form.get("role", "Software Developer").strip()[:100]
        category = request.form.get("category", "Python")
        question = request.form.get("question", "").strip()[:1000]
        answer = request.form.get("answer", "").strip()[:8000]
        if category not in QUESTIONS:
            category = "General"
        if not question:
            question = QUESTIONS[category][0]
        result = evaluate_with_groq(question, answer, role, category)
        if result is None:
            result = evaluate_locally(question, answer)
    return render_template("index.html", questions=QUESTIONS, result=result,
                           question=question, answer=answer, candidate=candidate,
                           role=role, category=category)

@app.get("/health")
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)

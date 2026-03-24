from fastapi import FastAPI
from pydantic import BaseModel
import torch
import sympy as sp
import re

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application
)

app = FastAPI()

# -----------------------
# LOAD MODEL (FLAN-T5)
# -----------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_NAME = "google/flan-t5-base"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device)
model.eval()

# -----------------------
# REQUEST MODEL
# -----------------------
class Question(BaseModel):
    question: str
    session_id: str = "default"   # for chat memory

# -----------------------
# CHAT MEMORY (simple)
# -----------------------
chat_memory = {}

def get_history(session_id):
    return chat_memory.get(session_id, [])

def update_history(session_id, user_msg, bot_msg):
    if session_id not in chat_memory:
        chat_memory[session_id] = []

    chat_memory[session_id].append(f"User: {user_msg}")
    chat_memory[session_id].append(f"Assistant: {bot_msg}")

    # limit memory (last 6 messages)
    chat_memory[session_id] = chat_memory[session_id][-6:]

# -----------------------
# SMART MATH SOLVER
# -----------------------
def solve_math_problem_steps(question):
    try:
        # 🔥 FIX 1: Replace ^ with **
        q = question.replace("^", "**").replace("=", "").strip()

        x = sp.symbols('x')
        transformations = standard_transformations + (implicit_multiplication_application,)

        # -----------------------
        # 1️⃣ ALGEBRA (x present)
        # -----------------------
        if re.search(r"[a-zA-Z]", q):

            expr = parse_expr(q, transformations=transformations)

            steps = []
            steps.append(f"Expression: {expr}")

            # Expand
            expanded = sp.expand(expr)
            steps.append(f"Step 1: Expand → {expanded}")

            # Simplify
            simplified = sp.simplify(expanded)
            steps.append(f"Step 2: Simplify → {simplified}")

            return "📘 Step-by-step Solution:\n\n" + "\n".join(steps) + f"\n\n✅ Final Answer: {simplified}"

        # -----------------------
        # 2️⃣ NUMERIC
        # -----------------------
        if re.fullmatch(r"[0-9+\-*/(). ]+", q):

            steps = []
            expr = q

            while "*" in expr or "/" in expr:
                match = re.search(r'(\d+)([*\/])(\d+)', expr)
                if not match:
                    break

                a, op, b = match.groups()
                a, b = int(a), int(b)

                if op == "*":
                    result = a * b
                    steps.append(f"Multiply → {a} × {b} = {result}")
                else:
                    result = a / b
                    steps.append(f"Divide → {a} ÷ {b} = {result}")

                expr = expr.replace(match.group(), str(result), 1)
                steps.append(f"Expression becomes: {expr}")

            result = eval(expr)
            steps.append(f"Final calculation → {expr} = {result}")

            return f"📘 Step-by-step Solution:\n\n" + "\n".join(steps) + f"\n\n✅ Final Answer: {result}"

        return None

    except Exception as e:
        print("Math Error:", e)
        return None

# -----------------------
# AI GENERATION
# -----------------------
def generate_text(question):
    prompt = f"""
Answer the following question clearly and helpfully.

Question: {question}

Give a proper explanation in simple words.
Do not repeat the question.
Answer:
"""

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True).to(device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=200,
        temperature=0.7,
        do_sample=True,
        top_p=0.9,
        repetition_penalty=1.2
    )

    result = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return result.strip()

# -----------------------
# MAIN CHAT FUNCTION
# -----------------------
def generate_answer(question, session_id="default"):

    q = question.strip()

    # -----------------------
    # 1️⃣ MATH FIRST
    # -----------------------
    math_result = solve_math_problem_steps(q)
    if math_result:
        return math_result

    q_lower = q.lower()

    # -----------------------
    # 2️⃣ FACT QUESTIONS → WIKIPEDIA
    # -----------------------
    if any(word in q_lower for word in [
        "what", "when", "who", "where", "define", "date"
    ]):
        wiki_result = get_wikipedia_answer(q)
        if wiki_result:
            return wiki_result

    # -----------------------
    # 3️⃣ EXAMPLES
    # -----------------------
    if "example" in q_lower:
        return generate_text(f"Give examples for: {q}")

    # -----------------------
    # 4️⃣ AI FALLBACK
    # -----------------------
    response = generate_text(q)

    # 🔥 FIX: avoid nonsense answers
    if not response or len(response) < 10:
        return "Sorry, I couldn't find a correct answer."

    return response

import wikipedia
def get_wikipedia_answer(query):
    try:
        results = wikipedia.search(query)

        if not results:
            return None

        page = wikipedia.page(results[0])
        summary = wikipedia.summary(page.title, sentences=2)

        return summary

    except Exception:
        return None
def answer_from_image(extracted_text, user_question):

    if not extracted_text:
        return "I couldn't detect any text from the image."

    # 1️⃣ Try math first (VERY IMPORTANT)
    math_result = solve_math_problem_steps(extracted_text)
    if math_result:
        return math_result

    # 2️⃣ Use BOTH text + question
    prompt = f"""
You are an AI tutor.

Use the following text extracted from an image to answer the question.

Extracted Text:
{extracted_text}

Question:
{user_question}

Give a clear and correct answer.
"""

    return generate_text(prompt)
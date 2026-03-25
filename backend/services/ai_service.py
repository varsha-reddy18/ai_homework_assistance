import sympy as sp
import re
import wikipedia
import ast
import torch

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application
)

# -----------------------
# LOAD AI MODEL
# -----------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_NAME = "google/flan-t5-base"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device)
model.eval()


# -----------------------
# GENERATE TEXT (STRICT)
# -----------------------
def generate_text(prompt):
    try:
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True).to(device)

        outputs = model.generate(
            **inputs,
            max_new_tokens=120,
            temperature=0.3,   # 🔥 low creativity = less wrong answers
            do_sample=True,
            top_p=0.8
        )

        return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

    except Exception as e:
        print("AI Error:", e)
        return None


# -----------------------
# MATH SOLVER (SYMpy)
# -----------------------
def solve_math(question):
    try:
        q = question.replace("^", "**").strip()
        x = sp.symbols('x')
        transformations = standard_transformations + (implicit_multiplication_application,)
        steps = []

        # EQUATION
        if "=" in q and any(ch.isalpha() for ch in q):
            left, right = q.split("=")
            left_expr = parse_expr(left, transformations=transformations)
            right_expr = parse_expr(right, transformations=transformations)

            eq = sp.Eq(left_expr, right_expr)
            solution = sp.solve(eq, x)

            steps.append(f"Equation: {eq}")
            steps.append(f"Solve for x → {solution}")

            return "📘 Step-by-step Solution:\n\n" + "\n".join(steps)

        # REMOVE '='
        if q.endswith("="):
            q = q[:-1].strip()

        # ALGEBRA
        if re.search(r"[a-zA-Z]", q):
            expr = parse_expr(q, transformations=transformations)

            steps.append(f"Expression: {expr}")
            steps.append(f"Expand → {sp.expand(expr)}")
            steps.append(f"Simplify → {sp.simplify(expr)}")
            steps.append(f"Factor → {sp.factor(expr)}")

            return "📘 Step-by-step Solution:\n\n" + "\n".join(steps)

        # NUMERIC
        if re.fullmatch(r"[0-9+\-*/(). ]+", q):

            def eval_node(node):
                if isinstance(node, ast.BinOp):
                    left = eval_node(node.left)
                    right = eval_node(node.right)

                    if isinstance(node.op, ast.Add):
                        result = left + right
                    elif isinstance(node.op, ast.Sub):
                        result = left - right
                    elif isinstance(node.op, ast.Mult):
                        result = left * right
                    elif isinstance(node.op, ast.Div):
                        result = left / right
                    else:
                        raise ValueError

                    steps.append(f"{left} → {right} = {result}")
                    return result

                elif isinstance(node, ast.Constant):
                    return node.value

                else:
                    raise ValueError

            tree = ast.parse(q, mode='eval')
            result = eval_node(tree.body)

            return "📘 Step-by-step Solution:\n\n" + "\n".join(steps) + f"\n\n✅ Answer: {result}"

        return None

    except Exception as e:
        print("Math Error:", e)
        return None


# -----------------------
# WIKIPEDIA (STRONG SEARCH)
# -----------------------
def get_wiki(query):
    try:
        results = wikipedia.search(query)

        if not results:
            return None

        return wikipedia.summary(results[0], sentences=3)

    except wikipedia.exceptions.DisambiguationError as e:
        try:
            return wikipedia.summary(e.options[0], sentences=3)
        except:
            return None
    except Exception as e:
        print("Wiki Error:", e)
        return None


# -----------------------
# CLEAN FALLBACK (NO AI)
# -----------------------
def clean_reference_answer(subject, text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if not sentences:
        return "❌ No answer found."

    return f"📘 {subject}:\n\n" + " ".join(sentences[:3])


# -----------------------
# AI REFINER (STRICT CONTROL)
# -----------------------
def refine_answer(subject, question, reference):
    prompt = f"""
Answer ONLY using the reference.

Question: {question}

Reference:
{reference}

Rules:
- Do NOT add new info
- Do NOT guess
- Keep answer simple
- 3-4 sentences only

Answer:
"""

    result = generate_text(prompt)

    # 🚨 STRICT VALIDATION
    if not result or len(result) < 20:
        return clean_reference_answer(subject, reference)

    # 🚨 if unrelated → fallback
    if question.split()[0].lower() not in result.lower():
        return clean_reference_answer(subject, reference)

    return result


# -----------------------
# MAIN FUNCTION
# -----------------------
def generate_answer(question, session_id="default", subject="General"):
    q = re.sub(r"[^0-9a-zA-Z+\-*/().= ]", "", question).strip()

    # AUTO DETECT MATH
    if subject == "General":
        if any(op in q for op in ["+", "-", "*", "/", "="]):
            subject = "Maths"

    # -----------------------
    # MATHS
    # -----------------------
    if subject == "Maths":
        result = solve_math(q)
        if result:
            return result

        return "❌ Could not solve."

    # -----------------------
    # THEORY (ALL SUBJECTS → WIKI ONLY)
    # -----------------------
    wiki = get_wiki(q)

    if wiki:
        return refine_answer(subject, q, wiki)

    return "❌ No answer found from Wikipedia."
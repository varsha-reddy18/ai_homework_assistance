import sympy as sp
import re
import wikipedia
import torch

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

# -----------------------------------------------------------------------
# LOAD AI MODEL  (English-only; used for answer generation, not translation)
# -----------------------------------------------------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_NAME = "google/flan-t5-base"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device)
model.eval()


# -----------------------------------------------------------------------
# TRANSLATION  (pip install deep-translator)
# -----------------------------------------------------------------------
try:
    from deep_translator import GoogleTranslator
    TRANSLATE_AVAILABLE = True
except ImportError:
    TRANSLATE_AVAILABLE = False
    print("⚠️  deep-translator not installed. Run: pip install deep-translator")


def _google_translate(text: str, dest: str, src: str = "auto") -> str | None:
    """Translate a single piece of plain text. Returns None on failure."""
    if not TRANSLATE_AVAILABLE or not text or not text.strip():
        return None
    try:
        translated = GoogleTranslator(source=src, target=dest).translate(text.strip())
        result = translated.strip() if translated else None
        # Reject suspiciously short results (e.g. a lone ".")
        if result and len(result) > 1:
            return result
        return None
    except Exception as e:
        print(f"Translation error ({src}→{dest}):", e)
        return None


# -----------------------------------------------------------------------
# GENERATE TEXT  (English only)
# -----------------------------------------------------------------------
def generate_text(prompt: str) -> str | None:
    try:
        inputs = tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=512
        ).to(device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.3,
            do_sample=True,
            top_p=0.85,
        )
        return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    except Exception as e:
        print("AI Error:", e)
        return None


# -----------------------------------------------------------------------
# DETECT LANGUAGE  (Unicode range heuristic)
# -----------------------------------------------------------------------
def detect_language(text: str) -> str:
    """Returns 'telugu', 'hindi', or 'english'."""
    telugu_chars = sum(1 for c in text if "\u0C00" <= c <= "\u0C7F")
    hindi_chars  = sum(1 for c in text if "\u0900" <= c <= "\u097F")
    if telugu_chars > 2:
        return "telugu"
    if hindi_chars > 2:
        return "hindi"
    return "english"


# -----------------------------------------------------------------------
# MATH SOLVER  (SymPy)
# -----------------------------------------------------------------------
_MATH_KEYWORDS = re.compile(
    r"\b(solve|calculate|compute|simplify|factorise|factor|expand|differentiate|integrate|find x|find y)\b",
    re.IGNORECASE,
)
_PURE_MATH_RE = re.compile(r"^[\d\s\+\-\*/\^\(\)\.=<>!%,xyzXYZ]+$")


def is_math_question(question: str) -> bool:
    q = question.strip()
    return bool(_MATH_KEYWORDS.search(q)) or bool(_PURE_MATH_RE.match(q))


def solve_math(question: str) -> str:
    try:
        q = question.replace("^", "**").strip()
        transformations = standard_transformations + (implicit_multiplication_application,)
        steps = []
        x, y, z = sp.symbols("x y z")
        local_dict = {"x": x, "y": y, "z": z}

        if "," in q and "=" in q:
            eqs = []
            for part in q.split(","):
                if "=" not in part:
                    continue
                left, right = part.split("=", 1)
                eqs.append(sp.Eq(
                    parse_expr(left, transformations=transformations, local_dict=local_dict),
                    parse_expr(right, transformations=transformations, local_dict=local_dict),
                ))
            solution = sp.solve(eqs)
            steps.append(f"Equations: {eqs}")
            steps.append(f"Solution → {solution}")
            return "📘 Step-by-step Solution:\n\n" + "\n".join(steps)

        if "=" in q:
            left, right = q.split("=", 1)
            eq = sp.Eq(
                parse_expr(left, transformations=transformations, local_dict=local_dict),
                parse_expr(right, transformations=transformations, local_dict=local_dict),
            )
            vars_in_eq = list(eq.free_symbols)
            solution = sp.solve(eq, vars_in_eq)
            steps.append(f"Equation: {eq}")
            steps.append(f"Variables: {vars_in_eq}")
            steps.append(f"Solution → {solution}")
            return "📘 Step-by-step Solution:\n\n" + "\n".join(steps)

        if any(op in q for op in ["<", ">", "<=", ">="]):
            expr = parse_expr(q, transformations=transformations, local_dict=local_dict)
            solution = sp.solve_univariate_inequality(expr)
            steps.append(f"Inequality: {expr}")
            steps.append(f"Solution → {solution}")
            return "📘 Step-by-step Solution:\n\n" + "\n".join(steps)

        if re.search(r"[a-zA-Z]", q):
            expr = parse_expr(q, transformations=transformations, local_dict=local_dict)
            steps.append(f"Expression: {expr}")
            steps.append(f"Simplified → {sp.simplify(expr)}")
            steps.append(f"Expanded  → {sp.expand(expr)}")
            steps.append(f"Factored  → {sp.factor(expr)}")
            return "📘 Step-by-step Solution:\n\n" + "\n".join(steps)

        if re.fullmatch(r"[\d\s\+\-\*/(). ]+", q):
            expr = parse_expr(q)
            steps.append(f"Expression: {q}")
            steps.append(f"BODMAS Result → {expr}")
            return "📘 Step-by-step Solution:\n\n" + "\n".join(steps) + f"\n\n✅ Answer: {expr}"

        expr = parse_expr(q, transformations=transformations, local_dict=local_dict)
        steps.append(f"Expression: {expr}")
        steps.append(f"Evaluated  → {expr.evalf()}")
        return "📘 Step-by-step Solution:\n\n" + "\n".join(steps)

    except Exception as e:
        print("Math Error:", e)
        return "❌ Could not solve the math problem. Please check the expression."


# -----------------------------------------------------------------------
# WIKIPEDIA SEARCH
# -----------------------------------------------------------------------
def get_wiki(query: str) -> str | None:
    try:
        results = wikipedia.search(query, results=5)
        if not results:
            return None
        for title in results:
            try:
                return wikipedia.summary(title, sentences=4, auto_suggest=False)
            except wikipedia.exceptions.DisambiguationError as e:
                try:
                    return wikipedia.summary(e.options[0], sentences=4, auto_suggest=False)
                except Exception:
                    continue
            except Exception:
                continue
        return None
    except Exception as e:
        print("Wiki Error:", e)
        return None


SUBJECT_SEARCH_HINTS = {
    "physics":   "physics concept",
    "chemistry": "chemistry",
    "biology":   "biology",
    "social":    "history geography civics",
    "computer":  "computer science",
    "maths":     "mathematics",
    "general":   "",
}


def build_wiki_query(question: str, subject: str) -> str:
    hint = SUBJECT_SEARCH_HINTS.get(subject.lower(), "")
    return f"{hint} {question}".strip() if hint else question


# -----------------------------------------------------------------------
# AI REFINER  — returns PLAIN text (no emoji, no formatting prefix)
# -----------------------------------------------------------------------
def refine_answer_plain(question: str, reference: str) -> str | None:
    prompt = f"""You are a helpful tutor. Using ONLY the reference text below, answer the student's question in simple English (3-4 sentences). Reply with plain text only, no bullet points or special characters.

Question: {question}

Reference:
{reference}

Answer:"""
    result = generate_text(prompt)
    if result and len(result.strip()) >= 20:
        return result.strip()

    # Fallback: extract sentences from Wikipedia text directly
    sentences = re.split(r"(?<=[.!?])\s+", reference)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    return " ".join(sentences[:3]) if sentences else None


def answer_in_english(question: str) -> str | None:
    """Plain English answer via AI (no Wikipedia)."""
    prompt = f"""Answer the following question clearly in simple English (3-4 sentences). Reply with plain text only.

Question: {question}

Answer:"""
    return generate_text(prompt)


# -----------------------------------------------------------------------
# MULTILINGUAL ANSWER HANDLER  (Telugu / Hindi)
# -----------------------------------------------------------------------
def answer_in_language(question: str, lang_code: str, lang_name: str) -> str:
    """
    Key fix: we translate ONLY plain text sentences, never the formatted
    string with emoji/newlines — Google Translate drops content when it
    sees those characters, returning just a dot.

    Flow:
      1. Translate question → English
      2. Get a PLAIN English answer (no emoji, no prefix)
      3. Translate each sentence individually → target language
      4. Reassemble with formatting prefix
    """
    print(f"[{lang_name}] question: {question}")

    # Step 1: question → English
    english_question = _google_translate(question, dest="en", src=lang_code)
    print(f"[{lang_name}] english_question: {english_question}")
    if not english_question or len(english_question.strip()) < 3:
        english_question = question

    # Step 2: plain English answer
    wiki = get_wiki(english_question)
    if wiki:
        plain_english = refine_answer_plain(english_question, wiki)
    else:
        plain_english = answer_in_english(english_question)

    print(f"[{lang_name}] plain_english: {plain_english}")

    if not plain_english:
        return f"❌ Could not generate an answer for this {lang_name} question."

    # Step 3: translate sentence by sentence (avoids Google dropping content)
    sentences = re.split(r"(?<=[.!?])\s+", plain_english)
    translated_parts = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        t = _google_translate(sent, dest=lang_code, src="en")
        print(f"[{lang_name}] translated: {t}")
        if t:
            translated_parts.append(t)

    if translated_parts:
        return f"📘 {lang_name}:\n\n" + " ".join(translated_parts)

    # Step 4: fallback — translate whole block at once
    translated_whole = _google_translate(plain_english, dest=lang_code, src="en")
    if translated_whole:
        return f"📘 {lang_name}:\n\n{translated_whole}"

    # Final fallback
    return f"[{lang_name} translation unavailable]\n\n📘 English Answer:\n\n{plain_english}"


# -----------------------------------------------------------------------
# MAIN ENTRY POINT
# -----------------------------------------------------------------------
SCIENCE_SUBJECTS = {"physics", "chemistry", "biology", "social", "computer"}


def generate_answer(
    question: str,
    session_id: str = "default",
    subject: str = "General",
) -> str:

    subject_lower = subject.strip().lower()
    q = question.strip()

    # Telugu
    if subject_lower == "telugu" or detect_language(q) == "telugu":
        return answer_in_language(q, lang_code="te", lang_name="Telugu")

    # Hindi
    if subject_lower == "hindi" or detect_language(q) == "hindi":
        return answer_in_language(q, lang_code="hi", lang_name="Hindi")

    # Maths
    if subject_lower == "maths" or (subject_lower == "general" and is_math_question(q)):
        return solve_math(q)

    # Science subjects
    if subject_lower in SCIENCE_SUBJECTS:
        wiki_query = build_wiki_query(q, subject_lower)
        wiki = get_wiki(wiki_query)
        if wiki:
            plain = refine_answer_plain(q, wiki)
            if plain:
                return f"📘 {subject.capitalize()}:\n\n{plain}"
        ai_answer = answer_in_english(q)
        if ai_answer:
            return f"📘 {subject.capitalize()}:\n\n{ai_answer}"
        return "❌ No answer found. Please try rephrasing the question."

    # General fallback
    wiki = get_wiki(q)
    if wiki:
        plain = refine_answer_plain(q, wiki)
        if plain:
            return f"📘 Answer:\n\n{plain}"
    ai_answer = answer_in_english(q)
    if ai_answer:
        return f"📘 Answer:\n\n{ai_answer}"
    return "❌ No answer found. Please try rephrasing the question."
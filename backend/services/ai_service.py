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
# LOAD AI MODEL
# -----------------------------------------------------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_NAME = "google/flan-t5-base"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device)
model.eval()

# -----------------------------------------------------------------------
# TRANSLATION
# -----------------------------------------------------------------------
try:
    from deep_translator import GoogleTranslator
    TRANSLATE_AVAILABLE = True
except ImportError:
    TRANSLATE_AVAILABLE = False
    print("⚠️  deep-translator not installed. Run: pip install deep-translator")


def _google_translate(text: str, dest: str, src: str = "auto") -> str | None:
    if not TRANSLATE_AVAILABLE or not text or not text.strip():
        return None
    try:
        translated = GoogleTranslator(source=src, target=dest).translate(text.strip())
        result = translated.strip() if translated else None
        if result and len(result) > 1:
            return result
        return None
    except Exception as e:
        print(f"Translation error ({src}→{dest}):", e)
        return None


# -----------------------------------------------------------------------
# GENERATE TEXT  — standard short answers (normal chat)
# -----------------------------------------------------------------------
def generate_text(prompt: str, max_new_tokens: int = 150) -> str | None:
    try:
        inputs = tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=512
        ).to(device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.3,
            do_sample=True,
            top_p=0.85,
        )
        return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    except Exception as e:
        print("AI Error:", e)
        return None


# -----------------------------------------------------------------------
# GENERATE TEXT LONG — for image/PDF upload (detailed answers)
# -----------------------------------------------------------------------
def generate_text_long(prompt: str) -> str:
    """
    ✅ Used by image_routes.py for uploaded image/PDF questions.

    Problem: flan-t5-base max output = 512 tokens (~300-400 words).
    Solution:
      1. Extract the document text + question from prompt
      2. Build a clean focused prompt
      3. Run TWO generation passes and combine for longer answer
      4. Fallback: extract key sentences directly from document text
    """
    try:
        # ✅ Extract document text and question from the prompt
        doc_match = re.search(
            r"DOCUMENT TEXT START =====\n(.*?)\n===== DOCUMENT TEXT END",
            prompt, re.DOTALL
        )
        question_match = re.search(
            r'student\'s question is:\n"(.*?)"',
            prompt, re.DOTALL
        )

        doc_text  = doc_match.group(1).strip()   if doc_match   else ""
        question  = question_match.group(1).strip() if question_match else ""

        # ✅ Trim document text to fit model input (keep most relevant part)
        doc_text_trimmed = doc_text[:1500]

        # ✅ Pass 1 — direct answer
        pass1_prompt = f"""Read the following document text carefully and answer the question in detail.

Document:
{doc_text_trimmed}

Question: {question}

Give a detailed answer in 5-8 sentences:"""

        inputs1 = tokenizer(
            pass1_prompt, return_tensors="pt",
            truncation=True, max_length=800
        ).to(device)

        out1 = model.generate(
            **inputs1,
            max_new_tokens=512,
            temperature=0.7,
            do_sample=True,
            top_p=0.92,
            repetition_penalty=1.3,
            no_repeat_ngram_size=3,
        )
        answer1 = tokenizer.decode(out1[0], skip_special_tokens=True).strip()

        # ✅ Pass 2 — elaborate further
        pass2_prompt = f"""Elaborate further on this answer about "{question}":

{answer1}

Add more details and explanation:"""

        inputs2 = tokenizer(
            pass2_prompt, return_tensors="pt",
            truncation=True, max_length=600
        ).to(device)

        out2 = model.generate(
            **inputs2,
            max_new_tokens=400,
            temperature=0.7,
            do_sample=True,
            top_p=0.92,
            repetition_penalty=1.3,
            no_repeat_ngram_size=3,
        )
        answer2 = tokenizer.decode(out2[0], skip_special_tokens=True).strip()

        # ✅ Combine if answer2 adds new content
        if answer2 and answer2.strip() != answer1.strip() and len(answer2) > 30:
            full_answer = answer1 + "\n\n" + answer2
        else:
            full_answer = answer1

        # ✅ If still too short, directly pull from document text
        if len(full_answer.strip()) < 100 and doc_text:
            sentences = re.split(r'(?<=[.!?])\s+', doc_text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 40]
            fallback = " ".join(sentences[:6])
            full_answer = full_answer + "\n\n" + fallback if full_answer else fallback

        return full_answer.strip()

    except Exception as e:
        print("AI Long Error:", e)
        # ✅ Hard fallback — extract sentences directly from document text
        doc_match = re.search(
            r"DOCUMENT TEXT START =====\n(.*?)\n===== DOCUMENT TEXT END",
            prompt, re.DOTALL
        )
        if doc_match:
            doc_text = doc_match.group(1).strip()
            sentences = re.split(r'(?<=[.!?])\s+', doc_text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 40]
            return " ".join(sentences[:6]) if sentences else doc_text[:500]
        return "❌ Could not generate answer. Please try again."


# -----------------------------------------------------------------------
# DETECT LANGUAGE
# -----------------------------------------------------------------------
def detect_language(text: str) -> str:
    telugu_chars = sum(1 for c in text if "\u0C00" <= c <= "\u0C7F")
    hindi_chars  = sum(1 for c in text if "\u0900" <= c <= "\u097F")
    if telugu_chars > 2:
        return "telugu"
    if hindi_chars > 2:
        return "hindi"
    return "english"


# -----------------------------------------------------------------------
# MATH SOLVER
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
# WIKIPEDIA
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
# AI REFINER
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

    sentences = re.split(r"(?<=[.!?])\s+", reference)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    return " ".join(sentences[:3]) if sentences else None


def answer_in_english(question: str) -> str | None:
    prompt = f"""Answer the following question clearly in simple English (3-4 sentences). Reply with plain text only.

Question: {question}

Answer:"""
    return generate_text(prompt)


# -----------------------------------------------------------------------
# ENGLISH SUBJECT HANDLER
# -----------------------------------------------------------------------
_MEANING_RE   = re.compile(r"\b(meaning|definition|define|what is|what does .* mean)\b", re.IGNORECASE)
_SYNONYM_RE   = re.compile(r"\b(synonym|synonyms|similar words?|another word for|other words? for)\b", re.IGNORECASE)
_ANTONYM_RE   = re.compile(r"\b(antonym|antonyms|opposite|opposites|opposite words?)\b", re.IGNORECASE)
_SENTENCE_RE  = re.compile(r"\b(use in a sentence|example sentence|sentence using|sentence for)\b", re.IGNORECASE)
_SPELLING_RE  = re.compile(r"\b(spelling|spell|correct spelling)\b", re.IGNORECASE)


def _extract_target_word(question: str) -> str:
    match = re.search(
        r"\b(?:meaning|definition|synonym|antonym|opposite|spelling|sentence)\s+(?:of|for|to)\s+([a-zA-Z]+)",
        question, re.IGNORECASE
    )
    if match:
        return match.group(1)
    match = re.search(r"what does ([a-zA-Z]+) mean", question, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"define ([a-zA-Z]+)", question, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"use ([a-zA-Z]+) in a sentence", question, re.IGNORECASE)
    if match:
        return match.group(1)
    words = re.findall(r"[a-zA-Z]+", question)
    return words[-1] if words else question


def answer_english_subject(question: str) -> str:
    q = question.strip()
    word = _extract_target_word(q)

    if _MEANING_RE.search(q):
        prompt = f"""Give the clear meaning and definition of the English word "{word}" in 2-3 simple sentences. Include the part of speech (noun/verb/adjective etc.) and one example sentence. Reply with plain text only."""
        result = generate_text(prompt)
        if result and len(result.strip()) >= 10:
            return f"📘 English - Meaning of '{word}':\n\n{result.strip()}"
        return f"📘 English - Meaning of '{word}':\n\nCould not find the meaning. Please check the word spelling."

    if _SYNONYM_RE.search(q):
        prompt = f"""List 5 synonyms (similar words) for the English word "{word}". For each synonym, give a very short meaning. Reply with plain text only, one synonym per line."""
        result = generate_text(prompt)
        if result and len(result.strip()) >= 10:
            return f"📘 English - Synonyms of '{word}':\n\n{result.strip()}"
        return f"📘 English - Synonyms of '{word}':\n\nCould not find synonyms."

    if _ANTONYM_RE.search(q):
        prompt = f"""List 5 antonyms (opposite words) for the English word "{word}". For each antonym, give a very short meaning. Reply with plain text only, one antonym per line."""
        result = generate_text(prompt)
        if result and len(result.strip()) >= 10:
            return f"📘 English - Antonyms of '{word}':\n\n{result.strip()}"
        return f"📘 English - Antonyms of '{word}':\n\nCould not find antonyms."

    if _SENTENCE_RE.search(q):
        prompt = f"""Write 3 simple example sentences using the English word "{word}". Each sentence should clearly show the meaning of the word. Reply with plain text only, one sentence per line."""
        result = generate_text(prompt)
        if result and len(result.strip()) >= 10:
            return f"📘 English - Sentences using '{word}':\n\n{result.strip()}"
        return f"📘 English - Sentences using '{word}':\n\nCould not generate sentences."

    if _SPELLING_RE.search(q):
        prompt = f"""Give the correct spelling of the word "{word}" and break it into syllables. Also give a short meaning. Reply with plain text only."""
        result = generate_text(prompt)
        if result and len(result.strip()) >= 5:
            return f"📘 English - Spelling of '{word}':\n\n{result.strip()}"
        return f"📘 English - Spelling:\n\nThe correct spelling is: {word}"

    prompt = f"""You are an English language tutor. Answer the following English question clearly in simple language (3-4 sentences). Reply with plain text only.

Question: {q}

Answer:"""
    result = generate_text(prompt)
    if result and len(result.strip()) >= 20:
        return f"📘 English:\n\n{result.strip()}"

    wiki = get_wiki(q)
    if wiki:
        plain = refine_answer_plain(q, wiki)
        if plain:
            return f"📘 English:\n\n{plain}"

    return "❌ Could not find an answer. Please rephrase your English question."


# -----------------------------------------------------------------------
# MULTILINGUAL ANSWER HANDLER
# -----------------------------------------------------------------------
def answer_in_language(question: str, lang_code: str, lang_name: str) -> str:
    print(f"[{lang_name}] question: {question}")

    english_question = _google_translate(question, dest="en", src=lang_code)
    print(f"[{lang_name}] english_question: {english_question}")
    if not english_question or len(english_question.strip()) < 3:
        english_question = question

    wiki = get_wiki(english_question)
    if wiki:
        plain_english = refine_answer_plain(english_question, wiki)
    else:
        plain_english = answer_in_english(english_question)

    print(f"[{lang_name}] plain_english: {plain_english}")

    if not plain_english:
        return f"❌ Could not generate an answer for this {lang_name} question."

    sentences = re.split(r"(?<=[.!?])\s+", plain_english)
    translated_parts = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        t = _google_translate(sent, dest=lang_code, src="en")
        if t:
            translated_parts.append(t)

    if translated_parts:
        return f"📘 {lang_name}:\n\n" + " ".join(translated_parts)

    translated_whole = _google_translate(plain_english, dest=lang_code, src="en")
    if translated_whole:
        return f"📘 {lang_name}:\n\n{translated_whole}"

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

    if subject_lower == "telugu" or detect_language(q) == "telugu":
        return answer_in_language(q, lang_code="te", lang_name="Telugu")

    if subject_lower == "hindi" or detect_language(q) == "hindi":
        return answer_in_language(q, lang_code="hi", lang_name="Hindi")

    if subject_lower == "english":
        return answer_english_subject(q)

    if subject_lower == "maths" or (subject_lower == "general" and is_math_question(q)):
        return solve_math(q)

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

    wiki = get_wiki(q)
    if wiki:
        plain = refine_answer_plain(q, wiki)
        if plain:
            return f"📘 Answer:\n\n{plain}"
    ai_answer = answer_in_english(q)
    if ai_answer:
        return f"📘 Answer:\n\n{ai_answer}"
    return "❌ No answer found. Please try rephrasing the question."
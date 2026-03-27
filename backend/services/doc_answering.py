"""
doc_answering.py

Dynamic document QA — works for ANY uploaded PDF or image.
No hardcoded section names. Sections are detected automatically from the document.
"""

import re
from services.ai_service import generate_text


# -----------------------------------------------------------------------
# STEP 1: AUTO-DETECT SECTIONS FROM ANY DOCUMENT
# -----------------------------------------------------------------------
def detect_sections(document_text: str) -> dict:
    """
    Automatically find all section headers in the document.
    Returns: { "section_name_lowercase": "full header line" }

    Detects patterns like:
      - "1. Introduction"
      - "CHAPTER 1: OVERVIEW"
      - "Abstract", "Conclusion", "Summary" (standalone headers)
      - "[Page X]" markers
    """
    lines = document_text.splitlines()
    sections = {}

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) < 3:
            continue

        # Pattern 1: Numbered sections — "1. Abstract", "2.Introduction", "3) Methods"
        if re.match(r"^\d+[\.\)]\s*\w", stripped):
            key = re.sub(r"^\d+[\.\)]\s*", "", stripped).strip().lower()
            sections[key] = stripped

        # Pattern 2: ALL CAPS headers — "ABSTRACT", "CONCLUSION", "RESULTS"
        elif stripped.isupper() and 3 < len(stripped) < 80 and " " in stripped or \
             (stripped.isupper() and 3 < len(stripped) < 30):
            key = stripped.lower()
            sections[key] = stripped

        # Pattern 3: Title-Case standalone headers (short lines, no punctuation at end)
        elif re.match(r"^[A-Z][a-zA-Z\s&\-/]+$", stripped) and 4 < len(stripped) < 60:
            # Likely a heading if next lines are longer paragraph text
            next_line = lines[i+1].strip() if i+1 < len(lines) else ""
            if len(next_line) > 40 or next_line == "":
                key = stripped.lower()
                sections[key] = stripped

        # Pattern 4: "Chapter X" or "Section X"
        elif re.match(r"^(chapter|section|part|unit)\s+\d+", stripped, re.IGNORECASE):
            key = stripped.lower()
            sections[key] = stripped

    return sections


# -----------------------------------------------------------------------
# STEP 2: FIND BEST MATCHING SECTION FOR THE QUESTION
# -----------------------------------------------------------------------
def find_matching_section(question: str, sections: dict) -> str | None:
    """
    Find which detected section best matches the student's question.
    Uses keyword overlap scoring.
    """
    q_words = set(re.findall(r"[a-z]{3,}", question.lower()))

    best_section = None
    best_score = 0

    for section_key in sections:
        section_words = set(re.findall(r"[a-z]{3,}", section_key))
        score = len(q_words & section_words)
        if score > best_score:
            best_score = score
            best_section = section_key

    # Only return if there's a real match
    return best_section if best_score > 0 else None


# -----------------------------------------------------------------------
# STEP 3: EXTRACT SECTION TEXT
# -----------------------------------------------------------------------
def extract_section_text(document_text: str, section_header: str) -> str:
    """
    Given a section header line, extract all text until the next section.
    Works for any document structure.
    """
    lines = document_text.splitlines()
    result = []
    inside = False
    header_lower = section_header.lower().strip()

    for i, line in enumerate(lines):
        stripped = line.strip()
        stripped_lower = stripped.lower()

        if not inside:
            # Find the header line
            if header_lower in stripped_lower or stripped_lower in header_lower:
                inside = True
                result.append(stripped)
                continue
        else:
            # Stop conditions — next section header
            is_numbered = re.match(r"^\d+[\.\)]\s*[A-Z]", stripped)
            is_caps_header = stripped.isupper() and 3 < len(stripped) < 80
            is_page_marker = re.match(r"^\[Page \d+\]", stripped)
            is_chapter = re.match(r"^(chapter|section|part|unit)\s+\d+", stripped, re.IGNORECASE)

            if (is_numbered or is_caps_header or is_page_marker or is_chapter) and result:
                break

            result.append(stripped)

    extracted = "\n".join(result).strip()
    return extracted if len(extracted) > 20 else ""


# -----------------------------------------------------------------------
# DETECT INTENT
# -----------------------------------------------------------------------
def detect_intent(question: str) -> str:
    q = question.lower().strip()

    if re.search(r"\b(summarize|summary|overview|brief|gist)\b", q):
        return "summarize"

    if re.search(r"\b(mcq|multiple choice|answer the questions?|correct answer|option)\b", q):
        return "mcq"

    if re.search(r"\b(list|enumerate|what are the topics|what are the sections|points|headings)\b", q):
        return "list"

    if re.search(r"\b(title|author|submitted|institution|course|department|year|college|university|who wrote)\b", q):
        return "metadata"

    if re.search(r"\b(explain|describe|what is|tell me|give me|show me|write about|elaborate|detail)\b", q):
        return "explain"

    return "explain"


# -----------------------------------------------------------------------
# ANSWER MCQs
# -----------------------------------------------------------------------
def answer_mcqs(document_text: str) -> str:
    lines = document_text.splitlines()
    questions = []
    current_q = []

    for line in lines:
        line = line.strip()
        if not line:
            if current_q:
                questions.append("\n".join(current_q))
                current_q = []
            continue
        if re.match(r"^Q[\d\)\.\s]", line, re.IGNORECASE) or re.match(r"^\d+[\)\.]\s+\w", line):
            if current_q:
                questions.append("\n".join(current_q))
            current_q = [line]
        elif current_q:
            current_q.append(line)

    if current_q:
        questions.append("\n".join(current_q))

    if not questions:
        return ""

    answers = []
    for q_block in questions:
        q_lines = q_block.strip().splitlines()
        if not q_lines:
            continue
        q_text = q_lines[0]
        options = [l for l in q_lines[1:] if re.match(r"^[a-dA-D][\)\.\s]", l.strip())]

        if options:
            prompt = f"""Choose the correct answer for this multiple choice question.
Reply with only the correct letter and answer text.

{q_block}

Correct answer:"""
            ai_ans = generate_text(prompt, max_new_tokens=60)
            if ai_ans and len(ai_ans) > 1:
                answers.append(f"❓ {q_text}\n✅ {ai_ans}")
            else:
                answers.append(f"❓ {q_text}\n⚠️ Could not determine answer automatically.")
        else:
            answers.append(f"❓ {q_text}")

    return "\n\n".join(answers)


# -----------------------------------------------------------------------
# SUMMARIZE ANY DOCUMENT
# -----------------------------------------------------------------------
def summarize_document(document_text: str, sections: dict) -> str:
    lines = [l.strip() for l in document_text.splitlines() if l.strip()]

    # Find title — first meaningful non-page line
    title = ""
    for line in lines[:15]:
        if len(line) > 8 and not line.startswith("[Page") and not re.match(r"^\d+[\.\)]", line):
            title = line
            break

    result = []

    if title:
        result.append(f"📄 Document: {title}")

    if sections:
        result.append(f"\n📚 Sections ({len(sections)} found):\n" +
                      "\n".join(f"  • {v}" for v in list(sections.values())[:15]))

    # Try to get abstract / introduction
    for key in ["abstract", "introduction", "overview", "summary","conclude"]:
        for section_key, header in sections.items():
            if key in section_key:
                text = extract_section_text(document_text, header)
                if text:
                    result.append(f"\n📝 {header}:\n{text[:600]}")
                    break

    if not result:
        result.append(document_text[:800])

    return "\n".join(result)


# -----------------------------------------------------------------------
# EXTRACT METADATA
# -----------------------------------------------------------------------
def extract_metadata(document_text: str) -> str:
    lines = [l.strip() for l in document_text.splitlines() if l.strip()]

    meta_patterns = [
        "title", "course", "institution", "submitted by", "submitted to",
        "department", "academic year", "author", "college", "university",
        "school", "subject", "date", "roll", "student", "teacher", "professor"
    ]

    result = []
    for i, line in enumerate(lines[:50]):
        line_lower = line.lower()
        for pat in meta_patterns:
            if pat in line_lower:
                value = line
                if i + 1 < len(lines) and len(lines[i+1]) < 60:
                    if not any(p in lines[i+1].lower() for p in meta_patterns):
                        value += ": " + lines[i+1]
                result.append(f"• {value}")
                break

    if result:
        return "📋 Document Information:\n\n" + "\n".join(result)
    # Fallback: return first page
    return "📋 Document Content:\n\n" + document_text[:400]


# -----------------------------------------------------------------------
# LIST TOPICS
# -----------------------------------------------------------------------
def list_topics(sections: dict, document_text: str) -> str:
    if sections:
        topic_lines = "\n".join(f"  {i+1}. {v}" for i, v in enumerate(sections.values()))
        return f"📚 Topics/Sections in this document:\n\n{topic_lines}"

    # Fallback — scan for numbered lines
    lines = document_text.splitlines()
    topics = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d+[\.\)]\s+\w", stripped) and len(stripped) < 80:
            topics.append(f"  • {stripped}")

    if topics:
        return "📚 Topics found:\n\n" + "\n".join(topics[:20])

    return "No structured topics found in this document."


# -----------------------------------------------------------------------
# EXPLAIN — keyword-scored paragraph retrieval
# -----------------------------------------------------------------------
def explain_from_document(document_text: str, question: str,
                           sections: dict, matched_section: str | None) -> str:

    # ✅ If a section matched — extract and return it fully
    if matched_section and matched_section in sections:
        header = sections[matched_section]
        text = extract_section_text(document_text, header)
        if text:
            return f"📘 {header}:\n\n{text}\n\n---\n✅ Above is the '{header}' section from your document."

    # ✅ Try direct keyword search in section headers
    q_lower = question.lower()
    for section_key, header in sections.items():
        if any(word in section_key for word in re.findall(r"[a-z]{4,}", q_lower)):
            text = extract_section_text(document_text, header)
            if text:
                return f"📘 {header}:\n\n{text}"

    # ✅ Score all paragraphs by keyword overlap with question
    q_words = set(re.findall(r"[a-z]{4,}", question.lower()))
    paragraphs = re.split(r"\n{2,}|\[Page \d+\]", document_text)

    scored = []
    for para in paragraphs:
        para = para.strip()
        if len(para) < 60:
            continue
        para_words = set(re.findall(r"[a-z]{4,}", para.lower()))
        score = len(q_words & para_words)
        scored.append((score, para))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_paras = [p for score, p in scored[:4] if score > 0]

    if top_paras:
        return "📘 Most relevant content from your document:\n\n" + "\n\n".join(top_paras)

    # ✅ Last resort — return beginning of document
    return "📘 Document Content:\n\n" + document_text[:1000]


# -----------------------------------------------------------------------
# MAIN ENTRY POINT
# -----------------------------------------------------------------------
def answer_from_document(question: str, document_text: str) -> str:
    """
    Works for ANY uploaded PDF or image document.
    Dynamically detects sections, matches the question, returns full answer.
    """
    # Step 1: Auto-detect all sections in this document
    sections = detect_sections(document_text)

    # Step 2: Detect what the student wants
    intent = detect_intent(question)

    # Step 3: Find the best matching section for the question
    matched_section = find_matching_section(question, sections)

    print(f"[DOC QA] intent={intent} | matched={matched_section} | sections={list(sections.keys())[:6]}")

    # Step 4: Route to the right handler
    if intent == "mcq":
        mcq_ans = answer_mcqs(document_text)
        if mcq_ans:
            return "📝 MCQ Answers:\n\n" + mcq_ans
        # fallback to explain if no MCQs found
        return explain_from_document(document_text, question, sections, matched_section)

    if intent == "summarize":
        return summarize_document(document_text, sections)

    if intent == "metadata":
        return extract_metadata(document_text)

    if intent == "list":
        return list_topics(sections, document_text)

    # explain / default
    return explain_from_document(document_text, question, sections, matched_section)
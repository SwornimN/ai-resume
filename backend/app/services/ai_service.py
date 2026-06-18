import json
import re

import anthropic

from app.config import settings

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
_MODEL = "claude-sonnet-4-6"

# ── Helpers ───────────────────────────────────────────────────────────────────

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences that the model may add despite instructions."""
    match = _FENCE_RE.search(text)
    return match.group(1) if match else text.strip()


def _parse_json_response(raw: str) -> dict:
    cleaned = _strip_fences(raw)
    return json.loads(cleaned)


# ── Public API ────────────────────────────────────────────────────────────────


def extract_structured_data(raw_text: str) -> dict:
    """Parse a resume or job-posting text into structured JSON.

    Returns a dict shaped like:
        {
            "skills": [...],
            "years_experience": <number> | null,
            "education": [...],
            "keywords": [...]
        }

    Raises on network errors or JSON parse failures — callers should catch and
    handle gracefully (store parsed_json=None rather than crashing).
    """
    system = (
        "You are a structured data extractor. "
        "Given the text of a resume or job posting, return ONLY a JSON object — "
        "no markdown fences, no preamble, no explanation. "
        'The object must have exactly these keys: "skills" (array of strings), '
        '"years_experience" (number or null), "education" (array of strings), '
        '"keywords" (array of strings).'
    )

    message = _client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": raw_text}],
    )

    raw = message.content[0].text
    return _parse_json_response(raw)


def compare_resume_to_job(resume_parsed: dict, job_parsed: dict) -> dict:
    """Compare a parsed resume against a parsed job posting.

    Returns a dict shaped like:
        {
            "match_score": <0-100>,
            "matched_skills": [...],
            "missing_skills": [...],
            "suggestions": "<2-3 actionable sentences>"
        }

    Raises on network errors or JSON parse failures.
    """
    system = (
        "You are a career advisor and resume analyst. "
        "Given a candidate's parsed resume data and a parsed job posting, "
        "evaluate how well the candidate matches the role. "
        "Return ONLY a JSON object — no markdown fences, no preamble, no explanation. "
        'The object must have exactly these keys: '
        '"match_score" (integer 0-100), '
        '"matched_skills" (array of strings the candidate has that the job needs), '
        '"missing_skills" (array of strings the job needs that the candidate lacks), '
        '"suggestions" (string: 2-3 actionable sentences the candidate can act on).'
    )

    user_content = json.dumps(
        {"resume": resume_parsed, "job_posting": job_parsed}, indent=2
    )

    message = _client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = message.content[0].text
    return _parse_json_response(raw)

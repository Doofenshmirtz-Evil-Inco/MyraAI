import re

from rapidfuzz import fuzz, process


def resolve_candidate(transcript: str, candidates: list[dict]) -> dict | None:
    text = transcript.casefold().strip()
    number_words = {
        "first": 0, "one": 0, "1st": 0, "1": 0,
        "second": 1, "two": 1, "2nd": 1, "2": 1,
        "third": 2, "three": 2, "3rd": 2, "3": 2,
    }
    for word, index in number_words.items():
        if re.search(rf"\b{re.escape(word)}\b", text) and index < len(candidates):
            return candidates[index]

    year_match = re.search(r"\b(19\d\d|20\d\d)\b", text)
    if year_match:
        target_year = year_match.group(1)
        for candidate in candidates:
            if candidate.get("year") == target_year:
                return candidate

    candidate_titles = [candidate.get("title", "") for candidate in candidates]
    match = process.extractOne(text, candidate_titles, scorer=fuzz.partial_ratio)
    if match and match[1] > 75:
        return candidates[match[2]]
    return None

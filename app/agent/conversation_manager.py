from datetime import date
from typing import Any

from app.clarification import resolve_candidate
from app.database import save_log_to_db
from app.models.conversation import AgentDecision, ConversationState, Intent
from app.session_manager import session_manager
from app.tmdb_service import search_movie_candidates


class ConversationManager:
    def __init__(self, agent):
        self.agent = agent

    def process(self, session_id: str, transcript: str) -> dict[str, Any]:
        state = ConversationState.from_dict(session_manager.get_pending(session_id))
        decision = self.agent.process_user_input(session_id, transcript, state.to_dict())

        if decision["action"] != "log_media":
            state.intent = Intent.CHAT
            session_manager.set_pending(session_id, state.to_dict())
            return {
                "status": "chat",
                "intent": Intent.CHAT,
                "transcript": transcript,
                "speech": self.agent._clean_speech(decision.get("speech") or "I am listening. Tell me what is on your mind."),
            }

        self._merge_details(state, decision.get("details", {}))
        if state.current_movie is None:
            state.intent = Intent.MENTIONED_MOVIE
            state.missing_fields = ["movie"]
            session_manager.set_pending(session_id, state.to_dict())
            return self._ask(state, transcript, "What movie are you thinking of?")

        if state.current_movie.get("tmdb_id") is None:
            candidates = search_movie_candidates(state.current_movie["title"])
            exact = [item for item in candidates if item["title"].casefold() == state.current_movie["title"].casefold()]
            if len(exact) > 1:
                state.intent = Intent.CONFIRMING_MOVIE
                state.candidates = exact[:3]
                session_manager.set_pending(session_id, state.to_dict())
                choices = " ".join(
                    f"Option {index + 1}: {item['title']} ({item['year'] or 'year unknown'})."
                    for index, item in enumerate(state.candidates)
                )
                return self._ask(state, transcript, f"I found a few matches. Which one do you mean? {choices}", candidates=state.candidates)
            selected = exact[0] if exact else (candidates[0] if candidates else None)
            if not selected:
                state.intent = Intent.MENTIONED_MOVIE
                session_manager.set_pending(session_id, state.to_dict())
                return self._ask(state, transcript, f"I could not find {state.current_movie['title']}. What title did you mean?")
            state.current_movie = selected

        if state.candidates:
            selected = resolve_candidate(transcript, state.candidates)
            if selected:
                state.current_movie = selected
                state.candidates = []
            elif state.intent == Intent.CONFIRMING_MOVIE:
                session_manager.set_pending(session_id, state.to_dict())
                return self._ask(state, transcript, "Tell me the release year, or say option one, two, or three.", candidates=state.candidates)

        state.missing_fields = self._missing_fields(state)
        if state.missing_fields:
            state.intent = Intent.COLLECTING_LOG_DETAILS
            session_manager.set_pending(session_id, state.to_dict())
            return self._ask(state, transcript, self._next_question(state))

        state.intent = Intent.READY_TO_LOG
        entry = self._entry(state)
        save_log_to_db(entry, session_id)
        state.intent = Intent.LOGGED
        session_manager.clear_pending(session_id)
        speech = self.agent.compose_logged_response(
            entry["Title"], entry["Year"], entry["Rating"], entry["Review"]
        )
        return {
            "status": "success",
            "intent": Intent.LOGGED,
            "transcript": transcript,
            "speech": speech,
            **self._contract(state, entry),
            "entry": entry,
            "poster": state.current_movie.get("poster_path"),
        }

    @staticmethod
    def _merge_details(state: ConversationState, details: dict[str, Any]):
        title = details.get("title")
        if title and state.current_movie is None:
            state.current_movie = {"title": title, "tmdb_id": None, "year": "", "poster_path": None}
        if details.get("rating") is not None:
            state.rating = float(details["rating"])
        if details.get("review"):
            state.review = details["review"]
        if details.get("watched_date"):
            state.watched_date = details["watched_date"]
        if details.get("rewatch") is not None:
            state.rewatch = bool(details["rewatch"])
        if title or details.get("watched"):
            state.watched = True

    @staticmethod
    def _missing_fields(state: ConversationState) -> list[str]:
        missing = []
        if state.rating is None:
            missing.append("rating")
        if not state.review:
            missing.append("review")
        return missing

    @staticmethod
    def _next_question(state: ConversationState) -> str:
        if "review" in state.missing_fields and state.rating is None:
            return "Nice. What did you think of it, and what rating would you give it?"
        if "review" in state.missing_fields:
            return "What did you think of it?"
        return "What rating would you give it out of 5?"

    @staticmethod
    def _ask(state, transcript, speech, candidates=None):
        response = {
            "status": "clarification",
            "intent": state.intent,
            "transcript": transcript,
            "speech": speech,
            "question": speech,
        }
        if candidates is not None:
            response["candidates"] = candidates
        return response

    @staticmethod
    def _entry(state: ConversationState) -> dict[str, Any]:
        movie = state.current_movie
        return {
            "Title": movie["title"],
            "Year": movie.get("year", ""),
            "tmdbID": movie["tmdb_id"],
            "Rating": state.rating,
            "WatchedDate": state.watched_date or date.today().isoformat(),
            "Rewatch": state.rewatch,
            "Review": state.review,
        }

    @staticmethod
    def _contract(state: ConversationState, entry: dict[str, Any]) -> dict[str, Any]:
        return {
            "movie": {
                "title": entry["Title"],
                "tmdb_id": entry["tmdbID"],
                "year": entry["Year"],
            },
            "watch": {
                "date": entry["WatchedDate"],
                "rating": entry["Rating"],
                "rewatch": entry["Rewatch"],
            },
            "review": entry["Review"],
        }

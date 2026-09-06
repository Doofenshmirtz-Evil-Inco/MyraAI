# import os
# from google import genai
# from google.genai import types
# from app.tmdb_service import search_movie

# client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# # Define tool schema for Gemini
# log_movie_tool = types.FunctionDeclaration(
#     name="log_movie",
#     description="Logs a movie watched by the user with rating and review.",
#     parameters=types.Schema(
#         type=types.Type.OBJECT,
#         properties={
#             "movie_name": types.Schema(type=types.Type.STRING, description="Name of the movie"),
#             "rating": types.Schema(type=types.Type.NUMBER, description="Rating out of 5 (e.g. 0.5 to 5.0)"),
#             "review": types.Schema(type=types.Type.STRING, description="User's review or thoughts"),
#             "rewatch": types.Schema(type=types.Type.BOOLEAN, description="True if rewatched"),
#             "watched_date": types.Schema(type=types.Type.STRING, description="Date in YYYY-MM-DD format")
#         },
#         required=["movie_name", "rating"]
#     )
# )

# sys_instruction = """
# You are a movie logging voice assistant for Letterboxd. 
# When the user speaks about a movie they watched:
# 1. Extract the movie title, rating (out of 5), review, and rewatch status.
# 2. Call the `log_movie` tool with these details.
# 3. Be friendly, concise, and confirm once logged.
# """

# def process_voice_transcript(transcript: str) -> dict:
#     """Send transcript to Gemini and return the extracted movie log as a dict."""
#     response = client.models.generate_content(
#         model="gemini-2.5-flash",
#         contents=transcript,
#         config=types.GenerateContentConfig(
#             system_instruction=sys_instruction,
#             tools=[types.Tool(function_declarations=[log_movie_tool])],
#             temperature=0.2
#         )
#     )

#     # Extract the function call arguments from the model response
#     if response.function_calls:
#         call = response.function_calls[0]
#         args = dict(call.args or {})
#         args.setdefault("movie_name", "")
#         args.setdefault("rating", 3.0)
#         args.setdefault("review", "")
#         args.setdefault("rewatch", False)
#         args.setdefault("watched_date", None)
#         return args

#     # Fallback: model replied with plain text instead of calling the tool
#     text = (response.text or "").strip() if response.text else ""
#     raise ValueError(f"Gemini did not return structured data. Model said: {text or '(empty response)'}")

import os
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
from app.tools_schema import ALL_TOOLS, LOG_MEDIA_TOOL

load_dotenv()

JARVIS_SYSTEM_PROMPT = """
You are JARVIS, a warm, witty personal movie companion.
When the user says they finished, watched, read, or rated a title, call log_media.
Extract the exact title, media type, rating out of 5, review, rewatch status, and date.
Never expose tool names, function calls, JSON, or extraction details in a spoken reply.
Do not narrate what you are doing technically. For ordinary conversation, reply like a
thoughtful friend in one or two short sentences.
"""


def _schema_from_tool(tool_schema):
    properties = {}
    for name, property_schema in tool_schema["parameters"]["properties"].items():
        schema_type = getattr(types.Type, property_schema["type"])
        properties[name] = types.Schema(
            type=schema_type,
            description=property_schema.get("description"),
            enum=property_schema.get("enum"),
        )
    return types.FunctionDeclaration(
        name=tool_schema["name"],
        description=tool_schema["description"],
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties=properties,
            required=tool_schema["parameters"].get("required", []),
        ),
    )


JARVIS_FUNCTIONS = [_schema_from_tool(tool) for tool in ALL_TOOLS]


class JarvisAgent:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not configured.")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def process_user_input(self, session_id: str, transcript: str, state: dict | None = None) -> dict:
        today_str = datetime.now().strftime("%Y-%m-%d")
        context = f"Current conversation state: {state}\n" if state else ""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=f"{context}User said: {transcript}",
            config=types.GenerateContentConfig(
                system_instruction=(
                    f"{JARVIS_SYSTEM_PROMPT}\nToday's date is {today_str}.\n"
                    "When conversation state contains a current movie, preserve its title "
                    "and extract only new details from the user's latest message. "
                    "A rating alone is valid; return the known title with the new rating."
                ),
                tools=[types.Tool(function_declarations=JARVIS_FUNCTIONS)],
                temperature=0.2,
            ),
        )

        if response.function_calls:
            call = response.function_calls[0]
            return {
                "action": call.name,
                "details": dict(call.args or {}),
                "speech": "",
                "session_id": session_id,
            }

        return {
            "action": "chat",
            "details": {},
            "speech": self._clean_speech(response.text or ""),
            "session_id": session_id,
        }

    @staticmethod
    def _clean_speech(text: str) -> str:
        """Keep internal tool syntax from leaking into the spoken conversation."""
        cleaned = text.strip()
        if "log_media(" in cleaned or cleaned.startswith("{"):
            return "I have the details. Let me get that movie lined up for you."
        return cleaned

    def compose_logged_response(self, title: str, year: str, rating: float, review: str) -> str:
        prompt = f"""
The user just logged {title} ({year}) with a rating of {rating}/5.
Their thoughts were: {review or '(no review was provided)'}

Reply as a warm, sharp personal movie companion. Acknowledge the feeling in their
comment, react to one specific idea, and gently invite them to share or log another
interest. Keep it to two or three natural sentences. Do not mention APIs, tools,
databases, or technical processing. Do not claim to have feelings; be emotionally
attuned without pretending to be human.
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=JARVIS_SYSTEM_PROMPT,
                temperature=0.65,
            ),
        )
        return (response.text or "").strip()


jarvis_agent = JarvisAgent()

def process_voice_transcript(transcript: str) -> dict:
    result = jarvis_agent.process_user_input("transcript", transcript)
    if result["action"] != "log_media":
        raise ValueError(f"Gemini did not return a log_media tool call: {result['speech'] or '(empty)'}")

    details = result["details"]
    today_str = datetime.now().strftime("%Y-%m-%d")
    return {
        "movie_name": details.get("title", ""),
        "media_type": details.get("media_type", "movie"),
        "rating": details.get("rating", 3.0),
        "review": details.get("review", ""),
        "rewatch": details.get("rewatch", False),
        "watched_date": details.get("watched_date") or today_str,
    }
LOG_MEDIA_TOOL = {
    "name": "log_media",
    "description": "Logs a movie, TV show, anime, or book the user finished or rated.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING", "description": "Title of the media"},
            "media_type": {
                "type": "STRING",
                "enum": ["movie", "tv", "anime", "book"],
                "description": "Category of the media",
            },
            "rating": {"type": "NUMBER", "description": "User rating out of 5"},
            "review": {"type": "STRING", "description": "User's thoughts or review"},
            "rewatch": {"type": "BOOLEAN", "description": "Whether the user rewatched it"},
            "watched_date": {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
        },
        "required": ["title", "media_type"],
    },
}

GET_RECOMMENDATIONS_TOOL = {
    "name": "get_recommendations",
    "description": "Finds recommendations based on a genre, mood, or similar media.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "Recommendation request"},
            "media_type": {
                "type": "STRING",
                "enum": ["movie", "tv", "anime", "book"],
                "description": "Preferred media category",
            },
        },
        "required": ["query"],
    },
}

ALL_TOOLS = [LOG_MEDIA_TOOL, GET_RECOMMENDATIONS_TOOL]
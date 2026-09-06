# import os
# import httpx
# from dotenv import load_dotenv

# load_dotenv()
# TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# def search_movie(title: str, year: int = None) -> dict:
#     url = "https://api.themoviedb.org/3/search/movie"
#     params = {
#         "api_key": TMDB_API_KEY,
#         "query": title,
#         "language": "en-US",
#         "page": 1
#     }
#     if year:
#         params["year"] = year

#     try:
#         res = httpx.get(url, params=params, timeout=15.0)
#         res.raise_for_status()
#         data = res.json()
#     except Exception as e:
#         print(f"[TMDB] Search failed for '{title}': {e}")
#         return {"found": False, "query": title, "error": str(e)}

#     results = data.get("results", [])

#     if not results:
#         return {"found": False, "query": title}

#     top = results[0]
#     return {
#         "found": True,
#         "tmdb_id": top["id"],
#         "title": top["title"],
#         "year": top.get("release_date", "").split("-")[0] if top.get("release_date") else "",
#         "poster_path": f"https://image.tmdb.org/t/p/w200{top.get('poster_path')}" if top.get("poster_path") else None
#     }

import os
from curl_cffi import requests
from dotenv import load_dotenv

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

def search_movie_candidates(title: str, year: int = None, limit: int = 5) -> list[dict]:
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "language": "en-US",
        "page": 1
    }
    if year:
        params["year"] = year

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        res = requests.get(url, params=params, headers=headers, impersonate="chrome", timeout=10)
        if res.status_code != 200:
            print(f"[TMDB Error] Status: {res.status_code}, Body: {res.text}")
            return []

        data = res.json()
    except Exception as e:
        print(f"[TMDB Exception] Failed to query '{title}': {e}")
        return []

    results = data.get("results", [])
    if not results:
        return []

    return [
        {
            "tmdb_id": result["id"],
            "title": result["title"],
            "year": result.get("release_date", "").split("-")[0] if result.get("release_date") else "",
            "poster_path": f"https://image.tmdb.org/t/p/w200{result.get('poster_path')}" if result.get("poster_path") else None
        }
        for result in results[:limit]
    ]


def search_movie(title: str, year: int = None) -> dict:
    candidates = search_movie_candidates(title, year)
    if not candidates:
        return {"found": False, "query": title}
    return {"found": True, **candidates[0]}
# import os
# import pandas as pd

# CSV_FILE = "letterboxd_import.csv"
# HEADERS = ["Title", "Year", "tmdbID", "Rating", "WatchedDate", "Rewatch", "Review"]

# def append_to_csv(entry: dict):
#     file_exists = os.path.exists(CSV_FILE)
    
#     df = pd.DataFrame([entry])
#     df.to_csv(CSV_FILE, mode='a', index=False, header=not file_exists, encoding='utf-8')
#     print(f"[CSV Writer] Added: {entry['Title']} ({entry['Year']}) - Rating: {entry['Rating']}")

import os
import pandas as pd

CSV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "letterboxd_import.csv")

def append_to_csv(entry: dict):
    file_exists = os.path.exists(CSV_FILE)
    
    formatted_entry = {
        "Title": entry.get("Title"),
        "Year": entry.get("Year"),
        "tmdbID": entry.get("tmdbID"),
        "Rating": entry.get("Rating"),
        "WatchedDate": entry.get("WatchedDate"),
        "Rewatch": entry.get("Rewatch"),
        "Review": entry.get("Review")
    }

    df = pd.DataFrame([formatted_entry])
    df.to_csv(CSV_FILE, mode='a', index=False, header=not file_exists, encoding='utf-8')
    print(f"[CSV Writer] Logged entry to {CSV_FILE}: {entry['Title']} ({entry['Year']}) - Rating: {entry['Rating']}")
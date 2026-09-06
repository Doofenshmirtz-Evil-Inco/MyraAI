# from playwright.sync_api import sync_playwright

# def log_direct_to_letterboxd(title: str, rating: float, review: str):
#     with sync_playwright() as p:
#         # Load browser with saved session state
#         browser = p.chromium.launch(headless=False)
#         context = browser.new_context(storage_state="state.json")
#         page = context.new_page()

#         # Navigate to search and select film
#         page.goto(f"https://letterboxd.com/search/{title}/")
#         page.locator(".results .film-poster").first.click()
        
#         # Click Log film button
#         page.locator(".add-film-button").click()
        
#         # Fill review
#         if review:
#             page.fill("#frm-review", review)
            
#         # Select rating (1-10 rate scale mapping)
#         # Letterboxd uses rating element clicks/slider
#         page.locator("#write-entry-submit").click()
#         browser.close()
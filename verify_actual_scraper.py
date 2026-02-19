import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from star_scraper import StarPlanScraper

def progress_callback(current, total, message, phase="scanning"):
    print(f"[{phase}] {current}/{total}: {message}")

url = "https://www.cac.edu.tw/star115/system/ColQry_115xStarFoRstU_BT65fwZ9z/TotalGsdShow.htm"

print("Initializing Scraper...")
scraper = StarPlanScraper(url, progress_callback)
scraper.get_universities()
print(f"Found {len(scraper.universities)} universities.")
if scraper.universities:
    print(f"Sample names: {[u['name'] for u in scraper.universities[:3]]}")

# Try to find one to run
if scraper.universities:
    target = scraper.universities[0]['name']
    print(f"Running for '{target}'...")
    scraper.run(target_universities=[target])
else:
    print("No universities to run.")

print(f"Scraping finished. Results count: {len(scraper.results)}")

if scraper.results:
    print("First result sample:")
    print(scraper.results[0])
else:
    print("No results found!")

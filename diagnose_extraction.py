import requests
from bs4 import BeautifulSoup
import time
import random

# Target: NTU (001) -> Chinese Lit (00101)
# Main: https://www.cac.edu.tw/star115/system/ColQry_115xStarFoRstU_BT65fwZ9z/TotalGsdShow.htm
# Uni: https://www.cac.edu.tw/star115/system/ColQry_115xStarFoRstU_BT65fwZ9z/ShowSchGsd.php?colno=001
# Dept: https://www.cac.edu.tw/star115/system/ColQry_115xStarFoRstU_BT65fwZ9z/html/115_00101.htm?v=1.0

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.cac.edu.tw/star115/system/ColQry_115xStarFoRstU_BT65fwZ9z/ShowSchGsd.php?colno=001"
}

session = requests.Session()
session.headers.update(headers)

def fetch_and_save(url, filename):
    print(f"Fetching {url}...")
    try:
        response = session.get(url, timeout=20)
        response.encoding = 'utf-8'
        print(f"Status: {response.status_code}")
        print(f"Length: {len(response.text)}")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Saved to {filename}")
        return response.text
    except Exception as e:
        print(f"Error: {e}")
        return None

# 1. Main Page (to set cookies potentially)
fetch_and_save("https://www.cac.edu.tw/star115/system/ColQry_115xStarFoRstU_BT65fwZ9z/TotalGsdShow.htm", "debug_main.html")
time.sleep(2)

# 2. Uni Page
fetch_and_save("https://www.cac.edu.tw/star115/system/ColQry_115xStarFoRstU_BT65fwZ9z/ShowSchGsd.php?colno=001", "debug_uni.html")
time.sleep(2)

# 3. Dept Page
html = fetch_and_save("https://www.cac.edu.tw/star115/system/ColQry_115xStarFoRstU_BT65fwZ9z/html/115_00101.htm?v=1.0", "debug_dept.html")

if html:
    soup = BeautifulSoup(html, 'html.parser')
    print("\n--- Extraction Test ---\n")
    
    # Check for error message
    if "流量過大" in html or "System is busy" in html:
        print("ALERT: Traffic limit detected in content!")
    
    # Try selectors
    colname = soup.select_one('.colname')
    print(f"School Name (.colname): {colname.text if colname else 'Not Found'}")
    
    gsdname = soup.select_one('.gsdname')
    print(f"Dept Name (.gsdname): {gsdname.text if gsdname else 'Not Found'}")
    
    # Try finding quota header
    quota_header = soup.find(string=lambda t: t and "招生名額" in t)
    print(f"Quota Header: {quota_header}")
    if quota_header:
        parent = quota_header.find_parent('td')
        print(f"Parent TD: {parent}")
        if parent:
            next_td = parent.find_next_sibling('td')
            print(f"Next TD (Value): {next_td.text if next_td else 'None'}")

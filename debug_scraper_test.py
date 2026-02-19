import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

# Mock the class for testing
class DebugScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        })

    def fetch_page(self, url, retries=5):
        import time
        for i in range(retries):
            try:
                print(f"Fetching {url}... (Attempt {i+1})")
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                response.encoding = 'utf-8'
                text = response.text
                
                if "流量過大" in text:
                    print(f"Server busy. Waiting {(i+1)*2}s...")
                    time.sleep((i+1)*2)
                    continue
                    
                return text
            except Exception as e:
                print(f"Error: {e}")
                time.sleep((i+1)*2)
        return None

    def test_extraction(self):
        # 1. Test University List
        html = self.fetch_page(self.base_url)
        if not html: return
        
        soup = BeautifulSoup(html, 'html.parser')
        uni_links = soup.select('table tr td a[href^="ShowSchGsd.php"]')
        print(f"Found {len(uni_links)} universities.")
        
        if not uni_links:
            print("DEBUG: No universities found. Dumping first 500 chars of HTML:")
            print(html[:500])
            return

        # 2. Pick the first university
        first_uni = uni_links[0]
        uni_url = urljoin(self.base_url, first_uni.get('href'))
        print(f"Testing University: {first_uni.text} ({uni_url})")
        
        # 3. Test Department List
        uni_html = self.fetch_page(uni_url)
        if not uni_html: return
        
        uni_soup = BeautifulSoup(uni_html, 'html.parser')
        # Try my selector
        dept_links = uni_soup.select('a[href*="/html/"]')
        print(f"Found {len(dept_links)} departments with selector 'a[href*=\"/html/\"]'.")
        
        if not dept_links:
            print("DEBUG: No departments found. Dumping first 500 chars of HTML:")
            print(uni_html[:500])
            # Try a broader selector to see what links exist
            all_links = uni_soup.find_all('a')
            print("First 5 links found on page:")
            for l in all_links[:5]:
                print(l)
            return

        # 4. Pick the first department
        first_dept = dept_links[0]
        dept_url = urljoin(uni_url, first_dept.get('href'))
        print(f"Testing Department: {dept_url}")
        
        # 5. Test Details Extraction
        dept_html = self.fetch_page(dept_url)
        if not dept_html: return
        
        dept_soup = BeautifulSoup(dept_html, 'html.parser')
        
        # Debug: Print title or some unique content
        print("Page Title:", dept_soup.title.text if dept_soup.title else "No Title")
        
        # Check specific fields
        # School Name
        school_name = dept_soup.select_one('.colname')
        print(f"Selector '.colname': {school_name.text if school_name else 'Not Found'}")
        
        # Dept Name
        dept_name = dept_soup.select_one('.gsdname')
        print(f"Selector '.gsdname': {dept_name.text if dept_name else 'Not Found'}")
        
        # Try to find "招生名額"
        quota = dept_soup.find(string=re.compile("招生名額"))
        print(f"Searching for string '招生名額': {quota if quota else 'Not Found'}")
        if quota:
            parent = quota.find_parent('td')
            # print parent and next sibling
            print(f"Parent TD: {parent}")
            if parent:
                print(f"Next Sibling: {parent.find_next_sibling('td')}")

if __name__ == "__main__":
    url = "https://www.cac.edu.tw/star115/system/ColQry_115xStarFoRstU_BT65fwZ9z/TotalGsdShow.htm"
    scraper = DebugScraper(url)
    scraper.test_extraction()

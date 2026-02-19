import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import re
from urllib.parse import urljoin

import random

class StarPlanScraper:
    def __init__(self, base_url, progress_callback=None):
        self.base_url = base_url
        self.progress_callback = progress_callback
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        })
        self.universities = []
        self.departments = []
        self.results = []
        self.should_stop = False

    def log(self, message):
        print(message)
        if self.progress_callback:
            # We can use a special status for logs if needed, but for now just pass it
            pass

    def fetch_page(self, url, retries=5, referer=None):
        if self.should_stop:
            return None
            
        # Update headers with referer if provided
        if referer:
            self.session.headers.update({'Referer': referer})
        
        for i in range(retries):
            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                response.encoding = 'utf-8' # Force UTF-8
                text = response.text
                
                # Check for specific "Traffic too high" error
                if "流量過大" in text or "System is busy" in text:
                    wait_time = (i + 1) * 2 # Exponential backoff: 2, 4, 6...
                    self.log(f"Server busy (流量過大) at {url}. Retrying in {wait_time}s ({i+1}/{retries})...")
                    time.sleep(wait_time)
                    continue
                    
                return text
            except requests.RequestException as e:
                wait_time = (i + 1) * 2
                self.log(f"Error fetching {url}: {e}. Retrying within {wait_time}s ({i+1}/{retries})...")
                time.sleep(wait_time)
        
        self.log(f"Failed to fetch {url} after {retries} retries.")
        return None

    def get_universities(self):
        self.log("Fetching university list...")
        # Main page doesn't need specific referer, or use itself
        html = self.fetch_page(self.base_url, referer=self.base_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        
        # Based on inspection: table tr td a -> href has 'ShowSchGsd.php?colno=XXX'
        uni_links = soup.select('table tr td a[href^="ShowSchGsd.php"]')
        
        universities = []
        for link in uni_links:
            href = link.get('href')
            name = link.text.strip()
            # Extract code from href
            match = re.search(r'colno=(\w+)', href)
            code = match.group(1) if match else "Unknown"
            
            full_url = urljoin(self.base_url, href)
            universities.append({
                "name": name,
                "code": code,
                "url": full_url
            })
            
        self.universities = universities
        self.log(f"Found {len(universities)} universities.")
        return universities

    def get_departments(self, uni_url):
        # Use main page as referer for uni page
        html = self.fetch_page(uni_url, referer=self.base_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        
        # Based on inspection: department details are in table[border="1"]
        # The link to details is usually in the last column or similar
        # Pattern: ./html/115_XXXXX.htm
        
        dept_links = soup.select('a[href*="/html/"]')
        
        departments = []
        for link in dept_links:
            href = link.get('href')
            # Check if it looks like a department detail link (usually contains numbers)
            if "htm" in href:
                full_url = urljoin(uni_url, href)
                departments.append({
                    "url": full_url
                })
                
        return departments

    def clean_text(self, text):
        if not text:
            return ""
        return text.strip().replace('\xa0', '').replace('\r', '').replace('\n', '')

    def get_department_details(self, dept_url, uni_name, uni_url):
        # Use uni page as referer for dept page
        html = self.fetch_page(dept_url, referer=uni_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        data = {}
        
        # School Name and Department Name
        # Based on browser inspection: .colname (school) and .gsdname (dept)
        # But let's look for robust selectors.
        # Often these pages use tables for layout.
        
        # We can extract from text or specific classes if they exist.
        # Try to find common labels in the table.
        
        try:
            # 1. Basic Info
            # Extract text containing labels
            text_content = soup.get_text()
            
            # School Name
            school_name_span = soup.select_one('.colname')
            data['學校名稱'] = self.clean_text(school_name_span.text) if school_name_span else uni_name
            
            # Department Name
            dept_name_span = soup.select_one('.gsdname')
            dept_name_text = self.clean_text(dept_name_span.text) if dept_name_span else ""
            
            # Extract code from title (format: (12345)Name) or from table
            data['校系代碼'] = ""
            data['學系名稱'] = dept_name_text
            
            match = re.match(r'\((\d+)\)(.+)', dept_name_text)
            if match:
                data['校系代碼'] = match.group(1)
                data['學系名稱'] = match.group(2).strip()
            else:
                # Fallback: look for "校系代碼" in table
                code_label = soup.find(string=re.compile(r'校系代碼'))
                if code_label:
                    parent_td = code_label.find_parent('td')
                    if parent_td:
                        next_td = parent_td.find_next_sibling('td')
                        if next_td:
                            data['校系代碼'] = self.clean_text(next_td.text)

            # 2. Extract Table Data
            
            def get_value_by_header(header_pattern, search_next_row=False):
                # Find a td/th containing the header
                element = soup.find(string=re.compile(header_pattern))
                if element:
                    parent_td = element.find_parent('td')
                    if not parent_td: return ""
                    
                    if search_next_row:
                        # Find the row of this element, then get next row's cell at same index or similar
                        current_tr = parent_td.find_parent('tr')
                        if current_tr:
                            next_tr = current_tr.find_next_sibling('tr')
                            if next_tr:
                                # Often the structure implies the value is in a cell in the next row
                                # Sometimes "可填志願數" is the label in next row, and value is next to IT.
                                # Let's search for label in next row if specified, or just value.
                                pass
                    
                    # Default: next sibling TD
                    next_td = parent_td.find_next_sibling('td')
                    if next_td:
                        return self.clean_text(next_td.text)
                return ""

            data['學群類別'] = get_value_by_header(r'學群類別')
            
            # Quotas
            # Store the elements to help find volunteer counts relative to them
            quota_label = soup.find(string=re.compile(r'招生名額'))
            if quota_label:
                # Value is next td
                q_td = quota_label.find_parent('td').find_next_sibling('td')
                data['招生名額'] = self.clean_text(q_td.text) if q_td else ""
                
                # Check for "可填志願數" in the NEXT row
                # Structure: <tr><td>招生名額</td><td>4</td></tr> <tr><td>可填志願數</td><td>2</td></tr>
                q_tr = quota_label.find_parent('tr')
                if q_tr:
                    next_tr = q_tr.find_next_sibling('tr')
                    if next_tr:
                        vol_label = next_tr.find(string=re.compile(r'可填志願數'))
                        if vol_label:
                            v_td = vol_label.find_parent('td').find_next_sibling('td')
                            data['招生名額各學群可選填志願數'] = self.clean_text(v_td.text) if v_td else ""
            
            extra_quota_label = soup.find(string=re.compile(r'外加名額'))
            if extra_quota_label:
                eq_td = extra_quota_label.find_parent('td').find_next_sibling('td')
                data['外加名額'] = self.clean_text(eq_td.text) if eq_td else ""
                
                # Volunteer count for extra
                eq_tr = extra_quota_label.find_parent('tr')
                if eq_tr:
                    next_tr = eq_tr.find_next_sibling('tr')
                    if next_tr:
                        vol_label = next_tr.find(string=re.compile(r'可填志願數'))
                        if vol_label:
                            v_td = vol_label.find_parent('td').find_next_sibling('td')
                            data['外加名額各學群可選填志願數'] = self.clean_text(v_td.text) if v_td else ""
            
            # Fallback for volunteers if not found by strict structure (some pages use full labels)
            if not data.get('招生名額各學群可選填志願數'):
                data['招生名額各學群可選填志願數'] = get_value_by_header(r'招生名額.*志願數')
            if not data.get('外加名額各學群可選填志願數'):
                data['外加名額各學群可選填志願數'] = get_value_by_header(r'外加名額.*志願數')


            # 3. Test Standards (檢定標準)
            standards = {'國文': '', '英文': '', '數學A': '', '數學B': '', '社會': '', '自然': '', '英聽': ''}
            
            # Strategy: Find "國文" label. 
            # Case A: Separate cells.
            # Case B: Multi-line cell (br separated).
            
            # list of all subject keys
            subj_keys = list(standards.keys())
            
            # Helper for strict matching
            def strict_match(pattern):
                return re.compile(f'^\\s*{pattern}\\s*$')

            # Try to find a cell that contains MULTIPLE subjects (Case B)
            # We look for "國文" and check if "英文" is also in the same cell
            found_multi_mode = False
            
            # Use strict match to avoid matching "國語文..." in rank items
            first_subj = soup.find(string=strict_match('國文'))
            if first_subj:
                parent_td = first_subj.find_parent('td')
                # Check if "英文" text node exists in the same TD
                if parent_td and parent_td.find(string=strict_match('英文')):
                    found_multi_mode = True
                    # This is the condensed table mode (Kang Ning style)
                    
                    # Extract subjects from parent_td
                    subjects_in_order = [s.strip() for s in parent_td.stripped_strings if s.strip() in subj_keys]
                    
                    # Get value TD
                    val_td = parent_td.find_next_sibling('td')
                    if val_td:
                        values_in_order = [v.strip() for v in val_td.stripped_strings]
                        
                        for i, subj in enumerate(subjects_in_order):
                            if i < len(values_in_order):
                                standards[subj] = values_in_order[i]
            
            if not found_multi_mode:
                # Case A: Standard table (one subject per cell header)
                for subject in standards.keys():
                    # Exact match prevents matching "國文" in "國文檢定標準" or "國語文"
                    subj_cell = soup.find(string=strict_match(subject))
                    if subj_cell:
                         parent = subj_cell.find_parent('td')
                         if parent:
                             next_td = parent.find_next_sibling('td')
                             if next_td:
                                 standards[subject] = self.clean_text(next_td.text)

            # 4. Ranking Items (分發比序項目)
            rank_items = {}
            for i in range(1, 9):
                rank_items[f'分發比序項目{i}'] = ""

            # Try to find the block containing 1. or 1、
            # It might be a big cell with all items
            
            # Look for "1." or "1、"
            start_marker = soup.find(string=re.compile(r'1[\.、]'))
            if start_marker:
                container_td = start_marker.find_parent('td')
                if container_td:
                    # Get all text lines
                    lines = [ln.strip() for ln in container_td.stripped_strings if ln.strip()]
                    
                    # Parse lines
                    current_idx = 0
                    for line in lines:
                        # Check if line starts with specific number
                        # Match 1. or 1、 or 2. ...
                        m = re.match(r'^(\d+)[\.、](.+)', line)
                        if m:
                            idx = int(m.group(1))
                            content = m.group(2).strip()
                            if 1 <= idx <= 8:
                                rank_items[f'分發比序項目{idx}'] = content
                                current_idx = idx
                        elif current_idx > 0:
                            # Continuation of previous item?
                            # Usually items are one per line or separated clearly.
                            # If it doesn't start with number, maybe append? 
                            # But simple extraction is usually enough.
                            pass

            data.update(standards)
            data.update(rank_items)
            
            return data

        except Exception as e:
            self.log(f"Error parsing {dept_url}: {e}")
            return None

    def run(self, target_universities=None):
        """
        :param target_universities: List of university names to scrape. If None, scrape all.
        """
        self.get_universities()
        if not self.universities:
            self.log("No universities found.")
            return

        # Filter universities if targets provided
        if target_universities and len(target_universities) > 0:
            target_set = set(target_universities)
            self.universities = [u for u in self.universities if u['name'] in target_set]
            self.log(f"Filtered to {len(self.universities)} universities.")

        all_departments = []
        
        # First, collect all department links
        total_unis = len(self.universities)
        for i, uni in enumerate(self.universities):
            if self.should_stop: break
            
            if self.progress_callback:
                self.progress_callback(i, total_unis, f"正在掃描學校: {uni['name']} ({i+1}/{total_unis})")
            
            depts = self.get_departments(uni['url'])
            for dept in depts:
                dept['uni_name'] = uni['name'] # Pass uni name
                dept['uni_url'] = uni['url']   # Pass uni url for referer
                all_departments.append(dept)
                
            # Add random delay between universities
            time.sleep(random.uniform(1.0, 3.0))

        # Now fetching details
        total_depts = len(all_departments)
        self.log(f"Found {total_depts} departments. Starting detailed extraction...")
        
        for i, dept in enumerate(all_departments):
            if self.should_stop: break
            
            if self.progress_callback:
                # Progress phase 2: details
                self.progress_callback(i, total_depts, f"正在抓取系所詳細資料: {dept['uni_name']} ({i+1}/{total_depts})", phase="details")
            
            details = self.get_department_details(dept['url'], dept['uni_name'], dept['uni_url'])
            if details:
                # Order keys
                ordered_data = {
                    '學校名稱': details.get('學校名稱', ''),
                    '學系名稱': details.get('學系名稱', ''),
                    '校系代碼': details.get('校系代碼', ''),
                    '學群類別': details.get('學群類別', ''),
                    '招生名額': details.get('招生名額', ''),
                    '外加名額': details.get('外加名額', ''),
                    '招生名額各學群可選填志願數': details.get('招生名額各學群可選填志願數', ''),
                    '外加名額各學群可選填志願數': details.get('外加名額各學群可選填志願數', ''),
                    '國文檢定標準': details.get('國文', ''),
                    '英文檢定標準': details.get('英文', ''),
                    '數學A檢定標準': details.get('數學A', ''),
                    '數學B檢定標準': details.get('數學B', ''),
                    '社會檢定標準': details.get('社會', ''),
                    '自然檢定標準': details.get('自然', ''),
                    '英聽檢定標準': details.get('英聽', ''),
                    '分發比序項目1': details.get('分發比序項目1', ''),
                    '分發比序項目2': details.get('分發比序項目2', ''),
                    '分發比序項目3': details.get('分發比序項目3', ''),
                    '分發比序項目4': details.get('分發比序項目4', ''),
                    '分發比序項目5': details.get('分發比序項目5', ''),
                    '分發比序項目6': details.get('分發比序項目6', ''),
                    '分發比序項目7': details.get('分發比序項目7', ''),
                    '分發比序項目8': details.get('分發比序項目8', ''),
                    '資料連結': dept['url']
                }
                self.results.append(ordered_data)
                
        if self.progress_callback:
             self.progress_callback(total_depts, total_depts, "完成！正在儲存檔案...", phase="done")

    def save_to_excel(self, filename):
        df = pd.DataFrame(self.results)
        df.to_excel(filename, index=False)
        self.log(f"Saved to {filename}")
        return filename

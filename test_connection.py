import requests

url = "https://www.cac.edu.tw/star115/system/ColQry_115xStarFoRstU_BT65fwZ9z/TotalGsdShow.htm"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    print("Success! Status Code:", response.status_code)
    print("Content length:", len(response.text))
    # print first 500 chars to check encoding
    print("First 500 chars:", response.text[:500])
except Exception as e:
    print(f"Failed: {e}")

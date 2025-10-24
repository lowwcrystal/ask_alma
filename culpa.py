import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

url = "https://culpa.info/professor/3509"

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
driver.get(url)

wait = WebDriverWait(driver, 10)
cards = wait.until(EC.presence_of_all_elements_located(
    (By.CSS_SELECTOR, "div.ui.fluid.card.w-100")
))

reviews_data = []

for card in cards:
    try:
        course_elem = card.find_element(By.CSS_SELECTOR, "div.header a")
        course = course_elem.text.strip()
    except:
        course = "N/A"
    
    # Find all description divs; the first is the review text
    descs = card.find_elements(By.CSS_SELECTOR, "div.description")
    review_text = descs[0].text.strip() if descs else "N/A"
    
    if review_text and len(review_text.split()) > 10:
        reviews_data.append((course, review_text))

print(f"Found {len(reviews_data)} reviews.")

# Save to CSV
with open("culpa_reviews.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Professor", "URL", "Class", "Review"])
    for course, review in reviews_data:
        writer.writerow(["Jae Woo Lee", url, course, review])

print("Saved reviews to culpa_reviews.csv")
driver.quit()

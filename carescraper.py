import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set up ChromeDriver options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# Replace with path to your ChromeDriver
service = Service(r'C:\Users\joshs\chromedriver-win64\chromedriver.exe')

# Start WebDriver
driver = webdriver.Chrome(service=service, options=chrome_options)

# Base URL
url = "https://www.medicare.gov/care-compare/results?searchType=NursingHome&page=1&city=Kansas%20City&state=MO&zipcode=64154&radius=25&sort=highestRated"
driver.get(url)

# Wait for page to load
wait = WebDriverWait(driver, 15)

# Data storage
results = []

# Loop through all result pages
while True:
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.card-location-container")))

    # Extract facility names and ratings
    cards = driver.find_elements(By.CSS_SELECTOR, "div.card-location-container")
    for card in cards:
        try:
            name = card.find_element(By.CSS_SELECTOR, "div.cc-card-title").text.strip()
            rating = card.find_element(By.CSS_SELECTOR, "div[data-testid='OverallRating']").text.strip()
        except:
            name, rating = None, None
        results.append({"Name": name, "Overall Rating": rating})

    # Check for next button
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Next page']")
        if next_button.is_enabled():
            next_button.click()
            time.sleep(2)
        else:
            break
    except:
        break

# Close the driver
driver.quit()

# Create DataFrame and save to Excel
df = pd.DataFrame(results)
df.to_excel("Kansas_City_Nursing_Homes.xlsx", index=False)

print("Scraping complete. File saved as 'Kansas_City_Nursing_Homes.xlsx'.")

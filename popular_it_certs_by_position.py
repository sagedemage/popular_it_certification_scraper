from selenium import webdriver
from urllib.parse import quote_plus
import time
import sys
import logging
from typing import Dict
from dataclasses import dataclass
from bs4 import BeautifulSoup

@dataclass
class DataResult:
    data: Dict[str, int]
    job_data_found: bool

@dataclass
class UrlInfo:
    url: str
    search_query: str

def remove_non_num_chars(jobs_num_s: str):
    """Remove non number characters"""
    jobs_num_s = jobs_num_s.removesuffix("jobs")
    jobs_num_s = jobs_num_s.replace(",", "")
    jobs_num_s = jobs_num_s.replace("+", "")
    jobs_num_s = jobs_num_s.strip()
    return jobs_num_s

def scrap_html_content(html_content: str, data: Dict[str, int], key: str, logger: logging.Logger, search_query: str) -> DataResult:
    """Scrap HTML content for jobs data"""
    job_data_found = False
    soup = BeautifulSoup(html_content, "lxml")

    # Check 1: Does the website contain the class job_results_two_pane for the section tag
    job_results_section_element = soup.find("section", class_="job_results_two_pane")
    if job_results_section_element != None:
        header_message_div_element = job_results_section_element.find("div", class_="header_message_two_pane")
        if header_message_div_element != None:
            p_element = header_message_div_element.find("p")
            if p_element != None:
                text = p_element.get_text()
                p_items = text.split(" ")
                if "jobs" in p_items:
                    results_s = p_items[0]
                    results_s = remove_non_num_chars(results_s)
                    results = int(results_s)
                    data[key] = results
                    job_data_found = True
                    logger.info(f"Added results number for {search_query}")

    if job_data_found == False:
        data_result = DataResult(None, False)
        return data_result
    data_result = DataResult(data, True)
    return data_result

def main():
    options = webdriver.ChromeOptions()

    # disable the automation-controlled features
    options.add_argument("--disable-blink-features=AutomationControlled")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    options.add_argument(f'--user-agent={user_agent}')

    # Set a standard window size to avoid detection by resolution fingerprinting
    options.add_argument("--window-size=1920,1080")

    # Disable features of Chrome
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-dev-shm-usage")

    # Disables the sandbox
    options.add_argument("--no-sandbox")

    # Remove automation switches
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    # Remove automation extensions
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)

    # Remove webdriver property via JS
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    certs = [
        "Comptia Network+",
        "Comptia Security+",
        "CCNA",
        "Comptia Linux+",
        "Comptia Server+"
        ]

    data: Dict[str, int] = {}
    urls_by_cert: Dict[str, UrlInfo] = {}

    for cert in certs:
        data[cert] = None
        urls_by_cert[cert] = ""

    location = "United States"
    location_encoded = quote_plus(location)

    position = "Network Engineer"

    for key in urls_by_cert.keys():
        search_query = f"{position} {key}"
        search_query_encoded = quote_plus(search_query)

        url = f"https://www.ziprecruiter.com/jobs-search?search={search_query_encoded}&location={location_encoded}"
        url_info = UrlInfo(url, search_query)
        urls_by_cert[key] = url_info

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    for key in urls_by_cert.keys():
        url_info = urls_by_cert[key]
        url = url_info.url
        search_query = url_info.search_query

        # Note: Selenium is great for getting dynamic HTML content generated from JavaScript
        driver.get(url)
        time.sleep(30)
        html_content = driver.page_source

        data_result = scrap_html_content(html_content, data, key, logger, search_query)
        if data_result.job_data_found == True:
            data = data_result.data
        else:
            logger.error(f"Unable to get the results number from {url}")
            driver.quit()
            sys.exit(1)

    driver.quit()

    results = []
    for cert in certs:
        result = data[cert]
        results.append(result)

    results = sorted(results, reverse=True)

    position_file_name = position.lower()
    position_file_name = position_file_name.replace(" ", "_")
    cert_result_file_path = f"data/popularity_cert_for_{position_file_name}.txt"
    with open(cert_result_file_path, "w", encoding="utf-8") as f:
        f.write(f"Position: {position}\n")
        for result in results:
            for key in data.keys():
                item = data[key]
                if item == result:
                    f.write(f"Result for {key}: {result}\n")
                    break
        logger.info(f"Wrote the IT certification averages in the {cert_result_file_path} file")

    logger.info(f"Finished scraping the data on the popularity of IT certifications for the position: {position}")

if __name__ == "__main__":
    main()

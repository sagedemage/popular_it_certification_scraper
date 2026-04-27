from selenium import webdriver
from urllib.parse import quote
import time
import sys
import logging
from typing import Dict, List
from dataclasses import dataclass
from bs4 import BeautifulSoup
import pandas as pd
import math
import re

@dataclass
class DataResult:
    data: Dict[str, List[int]]
    job_data_found: bool

@dataclass
class UrlInfo:
    url: str
    company_name: str

def remove_non_num_chars(jobs_num_s: str):
    """Remove non number characters"""
    jobs_num_s = jobs_num_s.removesuffix("jobs")
    jobs_num_s = jobs_num_s.replace(",", "")
    jobs_num_s = jobs_num_s.replace("+", "")
    jobs_num_s = jobs_num_s.strip()
    return jobs_num_s

def scrap_html_content(html_content: str, data: Dict[str, List[int]], key: str, logger: logging.Logger, company_name: str) -> DataResult:
    """Scrap HTML content for jobs data"""
    job_data_found = False
    soup = BeautifulSoup(html_content, "lxml")

    # Check 1: Does the website contain the text "{number} results"
    pattern = re.compile(r'\d results', re.IGNORECASE)
    results_element = soup.find(string=pattern)
    if results_element != None:
        results_element_text = results_element.get_text()
        results_items = results_element_text.split(" ")
        for i in range(len(results_items)-1):
            result_item = results_items[i+1].lower()
            result_item = result_item.replace("\n", "")
            if result_item == "results":
                results_s = results_items[i]
                results_s = remove_non_num_chars(results_s)
                results = int(results_s)
                data[key].append(results)
                job_data_found = True
                logger.info(f"Added results number for {key} from {company_name}")
                break
    else:
        # Check 2: Does the website contain the element of class "total-jobs"
        results_element = soup.find(class_="total-jobs")
        if results_element != None:
            results_s = results_element.get_text()
            results_s = remove_non_num_chars(results_s)
            results = int(results_s)
            data[key].append(results)
            job_data_found = True
            logger.info(f"Added results number for {key} from {company_name}")
        else:
            # Check 3: Does the website contain the element of attribute, data-testid, that is equal to "job-count"
            results_element = soup.find("b", {"data-testid": "job-count"})
            if results_element != None:
                jobs_num_s = results_element.get_text()
                jobs_num_s = remove_non_num_chars(jobs_num_s)
                jobs_num = int(jobs_num_s)
                data[key].append(jobs_num)
                job_data_found = True
                logger.info(f"Added results number for {key} from {company_name}")

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

    data: Dict[str, List[int]] = {}
    urls_by_cert: Dict[str, List[UrlInfo]] = {}

    for cert in certs:
        data[cert] = []
        urls_by_cert[cert] = []

    position = "Network Engineer"

    for key in urls_by_cert.keys():
        search_query = f"{position} {key}"
        search_query_encoded = quote(search_query)

        url = f"https://careers.rtx.com/global/en/search-results?keywords={search_query_encoded}"
        url_info = UrlInfo(url, "RTX")
        urls_by_cert[key].append(url_info)

        url = f"https://careers.mckesson.com/en/search-jobs/{search_query}"
        url_info = UrlInfo(url, "McKesson")
        urls_by_cert[key].append(url_info)

        url = f"https://apply.careers.microsoft.com/careers?query={search_query}"
        url_info = UrlInfo(url, "Microsoft")
        urls_by_cert[key].append(url_info)

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    for key in urls_by_cert.keys():
        urls = urls_by_cert[key]
        for url_info in urls:
            url = url_info.url
            company_name = url_info.company_name

            # Note: Selenium is great for getting dynamic HTML content generated from JavaScript
            driver.get(url)
            time.sleep(30)
            html_content = driver.page_source

            data_result = scrap_html_content(html_content, data, key, logger, company_name)
            if data_result.job_data_found == True:
                data = data_result.data
            else:
                logger.error(f"Unable to get the results number from {url}")
                driver.quit()
                sys.exit(1)

    driver.quit()

    df = pd.DataFrame(data=data)

    position_file_name = position.lower()
    position_file_name = position_file_name.replace(" ", "_")
    pop_certs_file_path = f"data/popularity_of_it_certifications_for_{position_file_name}.csv"
    df.to_csv(pop_certs_file_path)
    logger.info(f"Wrote the scraped data to {pop_certs_file_path}")

    avgs = []
    avg_of_certs = {}
    for cert in certs:
        avg = df[cert].mean()
        avg = math.floor(avg)
        avgs.append(avg)
        avg_of_certs[cert] = avg

    avgs = sorted(avgs, reverse=True)

    cert_avg_file_path = f"data/popularity_cert_for_{position_file_name}.txt"
    with open(cert_avg_file_path, "w", encoding="utf-8") as f:
        f.write(f"Position: {position}\n")
        for avg in avgs:
            for key in avg_of_certs.keys():
                item = avg_of_certs[key]
                if item == avg:
                    f.write(f"Average for {key}: {avg}\n")
                    break
        logger.info(f"Wrote the IT certification averages in the {cert_avg_file_path} file")

    logger.info(f"Finished scraping the data on the popularity of IT certifications for the position: {position}")

if __name__ == "__main__":
    main()

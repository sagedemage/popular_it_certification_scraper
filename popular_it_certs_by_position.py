from selenium import webdriver
from urllib.parse import quote
import time
import sys
import logging
from typing import Dict, List
from bs4 import BeautifulSoup
import pandas as pd
import math
import re
import configparser
from lib import DataResult, UrlInfo, remove_non_num_chars, solve_cloudflare_turnstitle, default_chrome_options

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
    user_agent = str("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36")
    options = default_chrome_options(user_agent)

    driver = webdriver.Chrome(options=options)

    # Remove webdriver property via JS
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    config = configparser.ConfigParser()
    config.read("config.ini")

    data: Dict[str, List[int]] = {}
    urls_by_cert: Dict[str, List[UrlInfo]] = {}

    certs = config["popular_certs"]["certs"].split(",")
    positions = config["IT_positions"]["positions"].split(",")

    for cert in certs:
        for position in positions:
            position_and_cert = f"{position} {cert}"
            data[position_and_cert] = []
            urls_by_cert[position_and_cert] = []

    for key in urls_by_cert.keys():
        search_query = quote(key)

        url = f"https://careers.rtx.com/global/en/search-results?keywords={search_query}"
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
            time.sleep(2)
            title = driver.title
            solve_cloudflare_turnstitle(title)
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

    pop_certs_file_path = "data/popularity_of_it_certifications_by_position.csv"
    df.to_csv(pop_certs_file_path)
    logger.info(f"Wrote the scraped data to {pop_certs_file_path}")

    avgs = []
    avg_of_certs = {}
    for key in urls_by_cert.keys():
        avg = df[key].mean()
        avg = math.floor(avg)
        avgs.append(avg)
        avg_of_certs[key] = avg

    avgs = sorted(avgs, reverse=True)

    cert_avg_file_path = "data/popularity_cert_by_position.txt"
    with open(cert_avg_file_path, "w", encoding="utf-8") as f:
        f.write(f"Certification Popularity by Position\n")
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

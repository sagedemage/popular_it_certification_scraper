from selenium import webdriver
import time
import pandas as pd
import math
from urllib.parse import quote
import sys
from typing import Dict, List
import logging
import json
from lib import UrlInfo, solve_cloudflare_turnstitle, default_chrome_options, scrap_html_content

def main():
    user_agent = str("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36")
    options = default_chrome_options(user_agent)

    driver = webdriver.Chrome(options=options)

    # Remove webdriver property via JS
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    config: dict = {}
    with open("config.json", "r") as f:
        config = json.load(f)

    certs = config["certs"]
    career_site_urls = config["career_site_urls"]

    data: Dict[str, List[int]] = {}
    urls_by_cert: Dict[str, List[UrlInfo]] = {}

    data["Companies"] = []

    for career_site_url in career_site_urls:
        company_name = career_site_url["company_name"]
        data["Companies"].append(company_name)

    for cert in certs:
        data[cert] = []
        urls_by_cert[cert] = []

    for key in urls_by_cert.keys():
        search_query = quote(key)

        for career_site_url in career_site_urls:
            url = f"{career_site_url["url"]}{search_query}"
            company_name = career_site_url["company_name"]
            url_info = UrlInfo(url, company_name)
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
    pop_certs_file_path = "data/popularity_of_it_certifications.csv"
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

    cert_avg_file_path = "data/popularity_cert_averages.txt"
    with open(cert_avg_file_path, "w", encoding="utf-8") as f:
        for avg in avgs:
            for key in avg_of_certs.keys():
                item = avg_of_certs[key]
                if item == avg:
                    f.write(f"Average for {key}: {avg}\n")
                    break
        logger.info(f"Wrote the IT certification averages in the {cert_avg_file_path} file")
    
    logger.info("Finished scraping the data on the popularity of IT certifications.")

if __name__ == "__main__":
    main()
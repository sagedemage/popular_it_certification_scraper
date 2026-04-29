from selenium import webdriver
from urllib.parse import quote
import time
import sys
import logging
from typing import Dict, List
import pandas as pd
import math
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

    data: Dict[str, List[int]] = {}
    urls_by_cert: Dict[str, List[UrlInfo]] = {}

    certs = config["certs"]
    positions = config["positions"]
    career_site_urls = config["career_site_urls"]

    data["Companies"] = []

    for career_site_url in career_site_urls:
        company_name = career_site_url["company_name"]
        data["Companies"].append(company_name)

    for position in positions:
        for cert in certs:
            data[cert] = []
            urls_by_cert[cert] = []

        for key in urls_by_cert.keys():
            search_query = f"{position} {key}"
            search_query_encoded = quote(search_query)

            for career_site_url in career_site_urls:
                url = f"{career_site_url["url"]}{search_query_encoded}"
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

        df = pd.DataFrame(data=data)

        position_file_name = position.lower()
        position_file_name = position_file_name.replace(" ", "_")

        pop_certs_file_path = f"data/positions/popularity_of_it_certifications_for_{position_file_name}.csv"
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

        cert_avg_file_path = f"data/positions/popularity_cert_for_{position_file_name}.txt"
        with open(cert_avg_file_path, "w", encoding="utf-8") as f:
            f.write(f"Certification Popularity for {position}\n")
            for avg in avgs:
                for key in avg_of_certs.keys():
                    item = avg_of_certs[key]
                    if item == avg:
                        f.write(f"Average for {key}: {avg}\n")
                        break
            logger.info(f"Wrote the IT certification averages in the {cert_avg_file_path} file for {position}")

    driver.quit()
    logger.info(f"Finished scraping the data on the popularity of IT certifications by position")

if __name__ == "__main__":
    main()

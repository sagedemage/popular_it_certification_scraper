from dataclasses import dataclass
from typing import Dict, List
import time
import pyautogui
from selenium import webdriver
from bs4 import BeautifulSoup
import re
import logging

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

def solve_cloudflare_turnstitle(title: str):
    """Solve Cloudflare Turnstile"""
    if title == "Just a moment...":
        time.sleep(10)
        pyautogui.click(544, 433)
        time.sleep(30)

def default_chrome_options(user_agent: str) -> webdriver.ChromeOptions:
    options = webdriver.ChromeOptions()
    # disable the automation-controlled features
    options.add_argument("--disable-blink-features=AutomationControlled")
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
    return options

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
            # Check 3: Does the website contain the element of class "result-count"
            results_element = soup.find(class_="result-count")
            if results_element != None:
                results_s = results_element.get_text()
                results_s = remove_non_num_chars(results_s)
                results = int(results_s)
                data[key].append(results)
                job_data_found = True
                logger.info(f"Added results number for {key} from {company_name}")
            else:
                # Check for no search results
                search_empty_element = soup.find("div", class_="search-empty")
                no_results_element = soup.find("div", {"ph-page-state": "no-results"})
                if search_empty_element != None or no_results_element != None:
                    data[key].append(0)
                    job_data_found = True
                    logger.info(f"Added results number for {key} from {company_name}")
                else:
                    # Check 4: Does the website contain the element of class "job-count"
                    results_element = soup.find(class_="job-count")
                    if results_element != None:
                        jobs_num_s = results_element.get_text()
                        jobs_num_s = remove_non_num_chars(jobs_num_s)
                        jobs_num_l = list(jobs_num_s)
                        remove = False
                        for i in range(len(jobs_num_l)):
                            if jobs_num_l[i] == "(":
                                remove = True
                            elif jobs_num_l[i] == ")":
                                remove = False
                                jobs_num_l[i] = ""
                            if remove == True:
                                jobs_num_l[i] = ""
                        jobs_num_s = "".join(jobs_num_l)
                        jobs_num = int(jobs_num_s)
                        data[key].append(jobs_num)
                        job_data_found = True
                        logger.info(f"Added results number for {key} from {company_name}")
                    else:
                        # Check 5: Does the website contain the element of attribute, data-testid, that is equal to "job-count"
                        results_element = soup.find("b", {"data-testid": "job-count"})
                        if results_element != None:
                            jobs_num_s = results_element.get_text()
                            jobs_num_s = remove_non_num_chars(jobs_num_s)
                            jobs_num = int(jobs_num_s)
                            data[key].append(jobs_num)
                            job_data_found = True
                            logger.info(f"Added results number for {key} from {company_name}")
                        else:
                            # Check 6: Does the website contain the span element of class "search-context-button__pill-counter"
                            results_element = soup.find("span", class_="search-context-button__pill-counter")
                            if results_element != None:
                                jobs_num_s = results_element.get_text()
                                jobs_num_s = remove_non_num_chars(jobs_num_s)
                                jobs_num = int(jobs_num_s)
                                data[key].append(jobs_num)
                                job_data_found = True
                                logger.info(f"Added results number for {key} from {company_name}")
                            else:
                                # Check 7: Does the website contain the text "jobs matched" or "job matched".
                                # If so, get the number of jobs from that tag.
                                div_elements = soup.find_all("div")
                                for div_element in div_elements:
                                    if div_element != None:
                                        text = div_element.get_text()
                                        if "jobs matched" in text or "job matched" in text:
                                            jobs_num_element = div_element.find("span", class_="SWhIm")
                                            if jobs_num_element != None:
                                                jobs_num_s = jobs_num_element.get_text()
                                                jobs_num_s = remove_non_num_chars(jobs_num_s)
                                                jobs_num = int(jobs_num_s)
                                                data[key].append(jobs_num)
                                                job_data_found = True
                                                logger.info(f"Added results number for {key} from {company_name}")
                                                break
    if job_data_found == False:
        data_result = DataResult(None, False)
        return data_result
    data_result = DataResult(data, True)
    return data_result

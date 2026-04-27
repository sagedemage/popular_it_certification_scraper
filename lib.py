from dataclasses import dataclass
from typing import Dict, List
import time
import pyautogui
from selenium import webdriver

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

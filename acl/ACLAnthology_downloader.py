"""
ACL Anthology Downloader
========================
This script downloads papers from the ACL Anthology.

Usage
-----
python ACLAnthology_downloader.py -e <event_name> -y <year> -o <output_dir> [-v] [-b <bottom_link>] [-H]
Options:
    -e, --event: str
        Event name (e.g., NAACL, ACL, EMNLP)
    -y, --year: str
        Event year (yyyy)
    -o, --output: str
        Output directory
    -v, --verbose: bool
        Show download progress
    -b, --bottomlink: str
        Wait for the link to appear at the bottom of the page
    -H, --headless: bool
        Use headless mode browser
"""

import argparse
import json
import time
import traceback
import unicodedata
from pathlib import Path

import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class ACLAnthologyDownloader:

    def __init__(self, headless):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)
        print("initialized Chrome driver.")

    def download(self, event_name, year, output_dir, verbose=False, bottom_link=None):
        print("output directory:", output_dir)
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        url = self.generate_url(event_name, year)
        self.driver.get(url)
        if bottom_link is not None:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, f"//a[@href='{bottom_link}']"))
            )

        p_elem_list = self.driver.find_elements(By.XPATH, "//p[@class='d-sm-flex align-items-stretch']")
        titles = {}
        for p_elem in p_elem_list:
            try:
                title_elem_list = p_elem.find_elements(
                    By.XPATH, "span[@class='d-block']/strong/a[@class='align-middle']"
                )
                for title_elem in title_elem_list:
                    title = title_elem.text
                    if "/" in title:
                        title = title.replace("/", "_")

                pdf_elem_list = p_elem.find_elements(
                    By.XPATH,
                    "span[@class='d-block mr-2 text-nowrap list-button-row']/a[@class='badge badge-primary align-middle mr-1']",
                )
                for pdf_elem in pdf_elem_list:
                    if pdf_elem.text == "pdf":
                        url = pdf_elem.get_attribute("href")
                        if verbose:
                            print(f"downloading {title} from {url}...")
                        file_id = Path(url).stem
                        title_format = self.format_title(title)
                        output_fn = output_dir_path / f"{file_id}-{title_format}.pdf"
                        if not output_fn.exists():
                            response = requests.get(url)

                            if response.status_code == 200:
                                with open(output_fn, "wb") as f:
                                    f.write(response.content)
                            else:
                                print("failed to download:", url, "status code:", response.status_code)
                    time.sleep(1)

                    titles[file_id] = title
            except TimeoutException:
                print("timeout exception occurred. could not find the bottom link element.")
            except:
                with open(output_dir_path / "error.log", "w") as f:
                    f.write(traceback.format_exc())
        json.dump(titles, open(output_dir_path / "meta.json", "w"), ensure_ascii=False, indent=4, sort_keys=True)

        print("download finished.")
        self.driver.quit()

    def generate_url(self, event_name, year):
        url = f"https://aclweb.org/anthology/events/{event_name.lower()}-{year}/"
        return url

    def format_title(self, title):
        title_format = unicodedata.normalize("NFKC", title).encode("ascii", "ignore").decode("ascii")
        return title_format


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", "-e", type=str, required=True, help="event name(e.g., NAACL, ACL, EMNLP)")
    parser.add_argument("--year", "-y", type=str, required=True, help="event year (yyyy)")
    parser.add_argument("--output", "-o", type=str, required=True, help="output directory")
    parser.add_argument("--verbose", "-v", action="store_true", default=False, help="show download progress")
    parser.add_argument(
        "--bottomlink", "-b", type=str, default=None, help="wait for the link to appear at the bottom of the page"
    )
    parser.add_argument("--headless", "-H", action="store_true", default=False, help="use headless mode browser")
    args = parser.parse_args()

    downloader = ACLAnthologyDownloader(args.headless)
    downloader.download(
        args.event,
        args.year,
        args.output,
        verbose=args.verbose,
        bottom_link=args.bottomlink,
    )

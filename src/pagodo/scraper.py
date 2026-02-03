import json
import urllib3
import requests
from bs4 import BeautifulSoup
import os

def retrieve_google_dorks(
    save_json_response_to_file=False,
    save_all_dorks_to_file=False,
    save_individual_categories_to_files=False,
    dorks_dir="dorks"
):
    """Retrieves all google dorks from https://www.exploit-db.com/google-hacking-database."""

    if not os.path.exists(dorks_dir):
        os.makedirs(dorks_dir)

    url = "https://www.exploit-db.com/google-hacking-database"

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "deflate, gzip, br",
        "Accept-Language": "en-US",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:60.0) Gecko/20100101 Firefox/60.0",
        "X-Requested-With": "XMLHttpRequest",
    }

    print(f"[+] Requesting URL: {url}")
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=10,
        )
    except requests.exceptions.SSLError:
        requests.packages.urllib3.disable_warnings()
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(
            url,
            headers=headers,
            timeout=10,
            verify=False,
        )

    if response.status_code != 200:
        print(f"[-] Error retrieving google dorks from: {url}")
        return

    # Extract json data.
    json_response = response.json()

    # Extract recordsTotal and data.
    total_dorks = json_response["recordsTotal"]
    json_dorks = json_response["data"]

    # List to track all the dorks.
    extracted_dorks = []

    # Dictionary to organize the dorks by category.
    category_dict = {}

    # Loop through dorks, collecting and organizing them.
    for dork in json_dorks:
        # Extract dork from <a href> using BeautifulSoup.
        soup = BeautifulSoup(dork["url_title"], "html.parser")
        # Some of the URL titles have trailing tabs, remove them.
        extracted_dork = soup.find("a").contents[0].strip()
        extracted_dorks.append(extracted_dork)

        # For individual categories.
        # Cast numeric_category_id as integer for sorting later.
        numeric_category_id = int(dork["category"]["cat_id"])
        category_name = dork["category"]["cat_title"]

        # Create an empty list for each category if it doesn't already exist.
        if numeric_category_id not in category_dict:
            category_dict[numeric_category_id] = {"category_name": category_name, "dorks": []}

        # Some of the URL titles have trailing tabs, use replace() to remove it in place.
        dork["url_title"] = dork["url_title"].replace("\t", "")
        category_dict[numeric_category_id]["dorks"].append(dork)

    # If requested, break up dorks into individual files based off category.
    if save_individual_categories_to_files:
        # Sort category_dict based off the numeric keys.
        category_dict = dict(sorted(category_dict.items()))

        for key, value in category_dict.items():
            # Provide some category metrics.
            print(f"[*] Category {key} ('{value['category_name']}') has {len(value['dorks'])} dorks")

            dork_file_name = value["category_name"].lower().replace(" ", "_")
            full_dork_file_name = os.path.join(dorks_dir, f"{dork_file_name}.dorks")

            print(f"[*] Writing dork category '{value['category_name']}' to file: {full_dork_file_name}")

            with open(f"{full_dork_file_name}", "w", encoding="utf-8") as fh:
                for dork in value["dorks"]:
                    soup = BeautifulSoup(dork["url_title"], "html.parser")
                    extracted_dork = soup.find("a").contents[0].strip()
                    fh.write(f"{extracted_dork}\n")

    # Save GHDB json object to all_google_dorks.json.
    if save_json_response_to_file:
        google_dork_json_file = "all_google_dorks.json"
        print(f"[*] Writing all dorks to JSON file: {google_dork_json_file}")
        with open(os.path.join(dorks_dir, google_dork_json_file), "w", encoding="utf-8") as json_file:
            json.dump(json_dorks, json_file)

    # Save all dorks to all_google_dorks.txt.
    if save_all_dorks_to_file:
        google_dork_file = "all_google_dorks.txt"
        print(f"[*] Writing all dorks to txt file: {dorks_dir}/{google_dork_file}")
        with open(os.path.join(dorks_dir, google_dork_file), "w", encoding="utf-8") as fh:
            for dork in extracted_dorks:
                fh.write(f"{dork}\n")

    print(f"[*] Total Google dorks retrieved: {total_dorks}")

    # Package up a nice dictionary to return.
    ghdb_dict = {
        "total_dorks": total_dorks,
        "extracted_dorks": extracted_dorks,
        "category_dict": category_dict,
    }

    return ghdb_dict

categories = {
    1: "Footholds",
    2: "File Containing Usernames",
    3: "Sensitives Directories",
    4: "Web Server Detection",
    5: "Vulnerable Files",
    6: "Vulnerable Servers",
    7: "Error Messages",
    8: "File Containing Juicy Info",
    9: "File Containing Passwords",
    10: "Sensitive Online Shopping Info",
    11: "Network or Vulnerability Data",
    12: "Pages Containing Login Portals",
    13: "Various Online devices",
    14: "Advisories and Vulnerabilities",
}

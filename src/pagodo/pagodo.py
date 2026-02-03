# Standard Python libraries.
import datetime
import json
import logging
import os
import random
import re
import sys
import time

# Third party Python libraries.
import requests

class Pagodo:
    """Pagodo class object"""

    def __init__(
        self,
        google_dorks_file,
        domain="",
        max_search_result_urls_to_return_per_dork=100,
        save_pagodo_results_to_json_file=None,  # None = Auto-generate file name, otherwise pass a string for path and filename.
        save_urls_to_file=None,  # None = Auto-generate file name, otherwise pass a string for path and filename.
        minimum_delay_between_dork_searches_in_seconds=1,
        maximum_delay_between_dork_searches_in_seconds=2,
        disable_verify_ssl=False,
        verbosity=4,
        specific_log_file_name=None,
        country_code="vn",
        max_results_per_search=100,
        client=None,
    ):
        """Initialize Pagodo class object."""
        import tempfile
        from .connectors.base import SearchConnector

        # Logging
        self.log = logging.getLogger("pagodo")
        log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)s] %(message)s")

        if specific_log_file_name is None:
             specific_log_file_name = os.path.join(tempfile.gettempdir(), f"pagodo_dork_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

        # Setup file logging.
        # Check if the logger already has handlers to avoid duplicate logging
        if not self.log.handlers:
            log_file_handler = logging.FileHandler(specific_log_file_name)
            log_file_handler.setFormatter(log_formatter)
            self.log.addHandler(log_file_handler)

            # Setup console logging.
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(log_formatter)
            self.log.addHandler(console_handler)

        # Assign log level.
        self.verbosity = verbosity
        self.log.setLevel((6 - self.verbosity) * 10)

        self.client = client
        if not self.client or not isinstance(self.client, SearchConnector):
            self.log.error("A valid SearchConnector client must be provided")
            sys.exit(1)
        
        self.country_code = country_code

        # Run parameter checks.
        if not os.path.exists(google_dorks_file):
            self.log.error("Specify a valid file containing Google dorks with -g")
            sys.exit(0)

        if minimum_delay_between_dork_searches_in_seconds < 0:
            self.log.error("Minimum delay between dork searches (-i) must be greater than 0")
            sys.exit(0)

        if maximum_delay_between_dork_searches_in_seconds < 0:
            print("maximum_delay_between_dork_searches_in_seconds (-x) must be greater than 0")
            sys.exit(0)

        if maximum_delay_between_dork_searches_in_seconds <= minimum_delay_between_dork_searches_in_seconds:
            print(
                "maximum_delay_between_dork_searches_in_seconds (-x) must be greater than "
                "minimum_delay_between_dork_searches_in_seconds (-i)"
            )
            sys.exit(0)

        if max_search_result_urls_to_return_per_dork < 0:
            print("max_search_result_urls_to_return_per_dork (-m) must be greater than 0")
            sys.exit(0)

        # All passed parameters look good, assign to the class object.
        self.google_dorks_file = google_dorks_file
        self.google_dorks = []
        with open(google_dorks_file, "r", encoding="utf-8") as fh:
            for line in fh.read().splitlines():
                if line.strip():
                    self.google_dorks.append(line)
        self.domain = domain
        self.max_search_result_urls_to_return_per_dork = max_search_result_urls_to_return_per_dork
        self.save_pagodo_results_to_json_file = save_pagodo_results_to_json_file
        self.save_urls_to_file = save_urls_to_file
        self.minimum_delay_between_dork_searches_in_seconds = minimum_delay_between_dork_searches_in_seconds
        self.maximum_delay_between_dork_searches_in_seconds = maximum_delay_between_dork_searches_in_seconds
        self.disable_verify_ssl = disable_verify_ssl
        self.max_results_per_search = max_results_per_search

        # Fancy way of generating a list of 20 random values between minimum_delay_between_dork_searches_in_seconds and
        # maximum_delay_between_dork_searches_in_seconds.  A random value is selected between each different Google
        # dork search.
        # """
        # 1) Generate a random list of values between minimum_delay_between_dork_searches_in_seconds and
        #    maximum_delay_between_dork_searches_in_seconds
        # 2) Round those values to the tenths place
        # 3) Re-cast as a list
        # 4) Sort the list
        # """
        self.delay_between_dork_searches_list = sorted(
            list(
                map(
                    lambda x: round(x, 1),
                    [
                        random.uniform(
                            minimum_delay_between_dork_searches_in_seconds,
                            maximum_delay_between_dork_searches_in_seconds,
                        )
                        for _ in range(20)
                    ],
                )
            )
        )

        self.base_file_name = f'pagodo_results_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.total_urls_found = 0

        # -o with no filename.  Desire to save results, don't care about the file name.
        if self.save_pagodo_results_to_json_file is None:
            self.save_pagodo_results_to_json_file = f"{self.base_file_name}.json"

        # -s with no filename.  Desire to save results, don't care about the file name.
        if self.save_urls_to_file is None:
            self.save_urls_to_file = f"{self.base_file_name}.txt"



    def go(self):
        """Start pagodo Google dork search."""

        initiation_timestamp = datetime.datetime.now().isoformat()

        self.log.info(f"Initiation timestamp: {initiation_timestamp}")

        # Initialize starting dork number.
        dork_counter = 1

        total_dorks_to_search = len(self.google_dorks)

        # Initialize dictionary to track dork results.
        self.pagodo_results_dict = {
            "dorks": {},
            "initiation_timestamp": initiation_timestamp,
            "completion_timestamp": "",
        }

        for dork in self.google_dorks:
            self.pagodo_results_dict["dorks"][dork] = {
                "urls_size": 0,
                "urls": [],
            }

            try:
                dork = dork.strip()

                # Search for the URLs to collect.
                if self.domain:
                    query = f"site:{self.domain} {dork}"
                else:
                    query = dork

                """
                Google search web GUI message for large search string queries:
                    "the" (and any subsequent words) was ignored because we limit queries to 32 words.
                """
                # Search string is longer than 32 words.
                if len(query.split(" ")) > 32:
                    ignored_string = " ".join(query.split(" ")[32:])
                    self.log.warning(
                        "Google limits queries to 32 words (separated by spaces):  Removing from search query: "
                        f"'{ignored_string}'"
                    )

                    # Update query variable.
                    updated_query = " ".join(query.split(" ")[0:32])

                    # If original query is in quotes, append a double quote to new truncated updated_query.
                    if query.endswith('"'):
                        updated_query = f'{updated_query}"'

                    self.log.info(f"New search query: {updated_query}")

                    query = updated_query

                # Search Connector
                dork_urls_list = []
                
                self.log.info(
                    f"Search ( {dork_counter} / {total_dorks_to_search} ) for Google dork [ {query} ] "
                    f"using Search Connector"
                )

                for batch_urls in self.client.search(query, self.max_search_result_urls_to_return_per_dork, self.country_code):
                    dork_urls_list.extend(batch_urls)
                    if len(dork_urls_list) >= self.max_search_result_urls_to_return_per_dork:
                         break

                # Remove any false positive URLs.
                for url in list(dork_urls_list): # Iterate over a copy to allow removal
                    # Ignore results from specific URLs like exploit-db.com, cert.org, and OffSec's Twitter account that
                    # may just be providing information about the vulnerability.  Keeping it simple with regex.
                    ignore_url_list = [
                        "https://www.kb.cert.org",
                        "https://www.exploit-db.com/",
                        "https://twitter.com/ExploitDB/",
                    ]
                    for ignore_url in ignore_url_list:
                        if re.search(ignore_url, url, re.IGNORECASE):
                            self.log.warning(f"Removing {ignore_url} false positive URL: {url}")
                            if url in dork_urls_list:
                                dork_urls_list.remove(url)

                dork_urls_list_size = len(dork_urls_list)

                # Google dork results found.
                if dork_urls_list:
                    self.log.info(f"Results: {dork_urls_list_size} URLs found for Google dork: {dork}")

                    dork_urls_list_as_string = "\n".join(dork_urls_list)
                    self.log.info(f"dork_urls_list:\n{dork_urls_list_as_string}")

                    self.total_urls_found += dork_urls_list_size

                    # Save URLs with valid results to an .txt file.
                    if self.save_urls_to_file:
                        with open(self.save_urls_to_file, "a") as fh:
                            fh.write(f"# {dork}\n")
                            for url in dork_urls_list:
                                fh.write(f"{url}\n")
                            fh.write("#" * 50 + "\n")

                    self.pagodo_results_dict["dorks"][dork] = {
                        "urls_size": dork_urls_list_size,
                        "urls": dork_urls_list,
                    }

                # No Google dork results found.
                else:
                    self.log.info(f"Results: {dork_urls_list_size} URLs found for Google dork: {dork}")

            except KeyboardInterrupt:
                sys.exit(0)

            except Exception as e:
                self.log.error(f"Error with dork: {dork}.  Exception {e}")
                if type(e).__name__ == "SSLError" and (not self.disable_verify_ssl):
                    self.log.info(
                        "If you are using self-signed certificates for an HTTPS proxy, try-rerunning with the -l "
                        "switch to disable verifying SSL/TLS certificates.  Exiting..."
                    )
                    sys.exit(1)

            dork_counter += 1

            # Only sleep if there are more dorks to search.
            if dork != self.google_dorks[-1]:
                pause_time = random.choice(self.delay_between_dork_searches_list)
                self.log.info(f"Sleeping {pause_time} seconds before executing the next dork search...")
                time.sleep(pause_time)

        self.log.info(f"Total URLs found for the {total_dorks_to_search} total dorks searched: {self.total_urls_found}")

        completion_timestamp = datetime.datetime.now().isoformat()

        self.log.info(f"Completion timestamp: {completion_timestamp}")
        self.pagodo_results_dict["completion_timestamp"] = completion_timestamp

        # Save pagodo_results_dict to a .json file.
        if self.save_pagodo_results_to_json_file:
            with open(self.save_pagodo_results_to_json_file, "w") as fh:
                json.dump(self.pagodo_results_dict, fh, indent=4)

        return self.pagodo_results_dict

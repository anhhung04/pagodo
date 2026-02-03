import time
import requests
import random
import logging
from typing import List, Generator
from .base import SearchConnector

class SerperConnector(SearchConnector):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.log = logging.getLogger("pagodo")
        
    def _search_with_retry(self, url, headers, body, max_retries=3):
        """Perform Serper API search with retry and jitter."""
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=body)
                if response.status_code == 200:
                    return response
                else:
                    self.log.warning(
                        f"Serper API failed (Attempt {attempt + 1}/{max_retries}): {response.text}"
                    )
            except requests.exceptions.RequestException as e:
                self.log.warning(f"Request failed (Attempt {attempt + 1}/{max_retries}): {e}")

            # Jitter: sleep between 1 and 3 seconds, increasing by attempt (exponential backoff)
            if attempt < max_retries - 1:
                sleep_time = random.uniform(1, 3) * (2**attempt)
                self.log.info(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)

        self.log.error(f"Serper API failed after {max_retries} attempts")
        return None

    def search(self, query: str, max_results: int, country_code: str = "vn") -> Generator[List[str], None, None]:
        url = "https://google.serper.dev/search"
        headers = {
            'X-API-KEY': self.api_key,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
        }
        
        page = 1
        total_fetched = 0
        
        # We process in batches of up to 100 as per API limits/logic
        # max_results passed here is the limit set by user (-m)
        
        while total_fetched < max_results:
            remaining_needed = max_results - total_fetched
            # Note: The original logic respected a separate max_results_per_search limit, 
            # and hard limit of 100. We can default max_results_per_search to 100 for now or pass it.
            # Simpler to just use 100 as batch size.
            num_to_fetch = min(remaining_needed, 100)
            
            body = {
                "q": query,
                "num": num_to_fetch,
                "page": page,
                "gl": country_code,
            }
            
            # Note: logging detailed search info might be better in the caller or here?
            # Original code logged "Search (...) for Google dork ... page=..."
            self.log.info(f"Searching page {page} for query: {query}")
            
            response = self._search_with_retry(url, headers, body)
            
            if not response:
                break
                
            if response.status_code == 200:
                results = response.json()
                current_batch_urls = []
                if "organic" in results:
                    for result in results["organic"]:
                        if "link" in result:
                            current_batch_urls.append(result["link"])
                
                if not current_batch_urls:
                    break
                
                yield current_batch_urls
                
                total_fetched += len(current_batch_urls)
                page += 1
                
                # Stop if we didn't get a full page, usually means end of results
                if len(current_batch_urls) < num_to_fetch:
                    break
            else:
                self.log.error(f"Serper API Error: {response.text}")
                break

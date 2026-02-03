import time
import requests
import random
import logging
from typing import List, Generator
from .base import SearchConnector

class SerpApiConnector(SearchConnector):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.log = logging.getLogger("pagodo")
        
    def _search_with_retry(self, url, params, max_retries=3):
        """Perform SerpApi search with retry and jitter."""
        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    return response
                else:
                    self.log.warning(
                        f"SerpApi failed (Attempt {attempt + 1}/{max_retries}): {response.text}"
                    )
            except requests.exceptions.RequestException as e:
                self.log.warning(f"Request failed (Attempt {attempt + 1}/{max_retries}): {e}")

            # Jitter: sleep between 1 and 3 seconds, increasing by attempt (exponential backoff)
            if attempt < max_retries - 1:
                sleep_time = random.uniform(1, 3) * (2**attempt)
                self.log.info(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)

        self.log.error(f"SerpApi failed after {max_retries} attempts")
        return None

    def search(self, query: str, max_results: int, page_size: int = 100, country_code: str = "vn") -> Generator[List[str], None, None]:
        url = "https://serpapi.com/search"
        
        # SerpApi pagination uses 'start' (offset) and 'num' (results per page, max 100)
        start = 0
        total_fetched = 0
        num_per_page = 100 
        
        while total_fetched < max_results:
            remaining_needed = max_results - total_fetched
            # num_to_fetch = min(remaining_needed, num_per_page)
            num_to_fetch = page_size
            
            # Note: num parameter in SerpApi defines how many results to return.
            # start parameter defines the offset.
            
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "num": num_to_fetch,
                "start": start,
                "gl": country_code,
                "no_cache": "true" # Ensure fresh results if needed, or remove for caching
            }
            
            page_num = (start // num_per_page) + 1
            self.log.info(f"Searching page {page_num} (start={start}) for query: {query}")
            
            response = self._search_with_retry(url, params)
            
            if not response:
                break
                
            if response.status_code == 200:
                results = response.json()
                current_batch_urls = []
                
                if "organic_results" in results:
                    for result in results["organic_results"]:
                        if "link" in result:
                            current_batch_urls.append(result["link"])
                
                if not current_batch_urls:
                    break
                
                yield current_batch_urls
                
                count = len(current_batch_urls)
                total_fetched += count
                start += count # simpler to just increment by what we got? 
                # actually google pagination usually works by explicit start index. 
                # If we asked for 100 and got 100, next start is start + 100.
                # If we got less, we might be at the end.
                
                # However, organic_results count might differ from 'num'.
                # To be safe for next page, we should probably increment start by 'num_to_fetch' 
                # or just use the count if we assume contiguous?
                # Standard Google logic: start=0, start=100...
                
                if count < num_to_fetch:
                    break
                    
                start += num_to_fetch 
            else:
                self.log.error(f"SerpApi Error: {response.text}")
                break

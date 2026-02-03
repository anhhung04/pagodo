from abc import ABC, abstractmethod
from typing import List, Generator

class SearchConnector(ABC):
    """Abstract base class for search engine connectors."""

    @abstractmethod
    def search(self, query: str, max_results: int, page_size: int = 100, country_code: str = "vn") -> Generator[List[str], None, None]:
        """
        Search for the given query and yield pages of results.
        
        Args:
            query: The search query.
            max_results: The total number of results desired (soft limit).
            page_size: The number of results to fetch per page/request.
            country_code: The country code for search results.
            
        Yields:
            List[str]: A list of URLs found in a batch/page.
        """
        pass

import aiohttp
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class SearchService(ABC):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key

    @abstractmethod
    async def search(self, query: str):
        pass

    async def _make_request(self, url: str, method: str = "GET", headers: Dict = None, params: Dict = None, data: str = None) -> Dict:
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=params) as response:
                    response.raise_for_status()
                    return await response.json()
            elif method == "POST":
                async with session.post(url, headers=headers, data=data) as response:
                    response.raise_for_status()
                    return await response.json()

class SerperDevService(SearchService):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.url = "https://google.serper.dev/search"
        
    def _extract_profile_links(self, items: list) -> list:
        try:
            raw = [item["link"] for item in items if "linkedin.com/in/" in item["link"]]
            return raw
        except (KeyError, IndexError):
            return []
        
    async def search(self, query: str):
        try:
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            payload = json.dumps({"q": f"{query} site:linkedin.com/in"})
            data = await self._make_request(self.url, method="POST", headers=headers, data=payload)
            return self._extract_profile_links(data.get("organic", []))
        except Exception as e:
            return []
    
    
class GoogleCustomSearchService(SearchService):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.url = "https://www.googleapis.com/customsearch/v1"
        self.cx = "f4cfa251940ec47ce"
    
    def _extract_profile_links(self, items: list) -> list:
        try:
            raw = [item["link"] for item in items if "linkedin.com/in/" in item["link"]]
            return raw
        except IndexError:
            return None

    async def search(self, query: str) -> Optional[List[str]]:
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query
        }
        data = await self._make_request(self.url, method="GET", params=params)
        return self._extract_profile_links(data["items"])

class SearchOrchestrator:
    def __init__(self):
        self.search_services = []
        
    def add_service(self, service: SearchService):
        self.search_services.append(service)
    
    def remove_service(self, service: SearchService):
        self.search_services.remove(service)
        
    async def search(self, query: str):
        results = []
        for service in self.search_services:
            try:
                result = await service.search(query)
                if result:  # Check if result is not None and not empty
                    results.extend(result)
            except Exception as e:
                continue
        return results
if __name__ == "__main__":
    search_orchestrator = SearchOrchestrator()
    search_orchestrator.add_service(SerperDevService("802646ef2d9889ee214dab859536a8b12ee337fb"))
    # search_orchestrator.add_service(GoogleCustomSearchService("YOUR_API_KEY"))
    
    async def main():
        result = await search_orchestrator.search("directors davienda")

    asyncio.run(main())
from linkedin_api import Linkedin as LinkedInBase
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal, AsyncGenerator, Any
from dotenv import load_dotenv, find_dotenv
import aiohttp
import json
import os

load_dotenv(find_dotenv(".env"))

class LinkedInProfile(BaseModel):
    firstName: str
    secondName: str
    position: str
    area: str
    company: str
    email: str = ""  
    linkedin_url: str
    pictureLink: str
    dateInsert: datetime
    dateUpdate: Optional[datetime] = None


class LinkedInCompany(BaseModel):
    name: str
    linkedin_url: str
    pictureLink: str
    dateInsert: datetime
    dateUpdate: Optional[datetime] = None
    employees: Optional[str] = None
    company_logo: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    phone: Optional[str] = None
    founded_on: Optional[int] = None
    

class LinkedIn:
    def __init__(self):
        self.api = LinkedInBase(
            os.getenv("LINKEDIN_EMAIL"),
            os.getenv("LINKEDIN_PASSWORD")
        )
    
    def _format_print(self, data: dict) -> str:
        return json.dumps(data, indent=4)
    
    def _extract_profile_links(self, items: list) -> list:
        try:
            raw = [item["link"] for item in items if "linkedin.com/in/" in item["link"]]
            return [link.split("/in/")[1] for link in raw]
        except IndexError:
            return None

    async def profile(self, search_query: str) -> AsyncGenerator[LinkedInProfile, None]:
        profiles = await self.profile_search(search_query)
        raw_result = []
        for profile in profiles.result:
            connection_message = f"""Hi, I came across your profile and I'm impressed by your experience. I'm interested in connecting with professionals in your field as I believe we could have valuable discussions about industry trends and collaborations. Looking forward to connecting!"""            
            error = self.api.add_connection(profile, connection_message)
            if error:
                print(f"Failed to connect to {profile}: {error}")
            try:
                raw_result.append(self.api.get_profile(profile))
            except Exception as e:
                print(f"Failed to get profile {profile}: {e}")
        
        def get_image(profile):
            if profile.get("displayPictureUrl"):
                img_size = profile.get("img_800_800") or profile.get("img_316_316") or profile.get("img_200_200") or profile.get("img_100_100", "")
                return profile["displayPictureUrl"] + (img_size or "")
            else:
                return ""
        
        with open("linkedin_profiles.json", "w") as f:
            json.dump(raw_result, f, indent=4)
        for profile in raw_result:                
            profile = LinkedInProfile(
                **{
                    "firstName": profile["firstName"],
                    "secondName": profile["lastName"],
                    "position": profile["experience"][0]["title"] if profile.get("experience") else profile["headline"],
                    "area": profile["locationName"] if profile.get("locationName") else profile.get("geoCountryName", ""),
                    "company": profile["experience"][0]["companyName"] if profile["experience"] else "",
                    "email": "",
                    "linkedin_url": f"https://www.linkedin.com/in/{profile['public_id']}",
                    "pictureLink": get_image(profile),
                    "dateInsert": datetime.now()
                }
            )
            yield profile    
            
    async def company(self, search_query: str) -> AsyncGenerator[LinkedInCompany, None]:
        result = self.api.get_company(search_query)
        
        def get_image(profile):
            if profile.get("logo") and profile.get("logo").get("image") and profile.get("logo").get("image").get("com.linkedin.common.VectorImage"):
                vector_image = profile.get("logo").get("image").get("com.linkedin.common.VectorImage")
                if vector_image.get("artifacts"):
                    img_size = vector_image.get("artifacts")[-1].get("fileIdentifyingUrlPathSegment", "")
                    return vector_image.get("rootUrl", "") + img_size
            return ""
        
        def get_address(profile):
            if profile.get("confirmedLocations"):
                addresses = [i for i in profile.get("confirmedLocations") if i.get("headquarter") == "true"]
                return addresses[0] if addresses else None
            return None
            
        company = LinkedInCompany(
            name=result.get("name", ""),
            linkedin_url=f"https://www.linkedin.com/company/{search_query}",
            pictureLink=result.get("logoUrl", ""),
            dateInsert=datetime.now(),
            company_logo=get_image(result),
            address=get_address(result),
            phone=result.get("phone", {}).get("number"),
            short_description=result.get("tagline", ""),
            description=result.get("description", ""),
            founded_on=result.get("foundedOn", {}).get("year"),
        )
        yield company
    
    async def profile_search(self, query: str) -> 'LinkedIn':
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": "AIzaSyA-mlmp0dKE6ugubRqCc9SnYimr6MhqDZM",
            "cx": "f4cfa251940ec47ce",
            "q": query
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                self.result = self._extract_profile_links(data["items"])
        return self
    
    async def search(self, search_query: str, limit: int = 2, 
              _type: Literal["profile", "company", "both"] = "both") -> 'LinkedIn':
        type_mapping = {
            "both": "PROFILE|COMPANY",
            "company": "COMPANY",
            "profile": "PROFILE"
        }
        params = {
            "q": search_query,
            "queryContext": f"List(spellCorrectionEnabled->true,relatedSearchesEnabled->true,kcardTypes->{type_mapping[_type]})"
        }
        self.result = self.api.search(params=params, limit=limit)
        return self


if __name__ == "__main__":
    import asyncio
    linkedin = LinkedIn()
    async def main():
        async for company in linkedin.profile('albin antony aimleap'):
            print(company)
    asyncio.run(main())
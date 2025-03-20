from linkedin_api import Linkedin as LinkedInBase
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal, AsyncGenerator, Any
from dotenv import load_dotenv, find_dotenv
import aiohttp
import json
import os
from concurrent.futures import ThreadPoolExecutor
from serp import SearchOrchestrator, SerperDevService, GoogleCustomSearchService

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
        self.search_orchestrator = SearchOrchestrator()
        self.search_orchestrator.add_service(SerperDevService(os.getenv("SERPER_API_KEY")))
        # self.search_orchestrator.add_service(GoogleCustomSearchService(os.getenv("GOOGLE_API_KEY")))
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    def _format_print(self, data: dict) -> str:
        return json.dumps(data, indent=4)
    
    def _process_profile(self, profile_url):
        try:
            if not profile_url:
                print("Empty profile URL provided")
                return None
                    
            # Clean up profile URL to get just the username/id
            print(f"Processing profile URL: {profile_url}")
            profile_id = profile_url.split('?')[0].split('/')[-1]
            print(f"Extracted profile ID: {profile_id}")
            
            try:
                profile_data = self.api.get_profile(profile_id)
                if profile_data is None:
                    print(f"API returned None for profile {profile_id}")
                    return None
                    
                # Check if profile_data is a valid dictionary
                if not isinstance(profile_data, dict):
                    print(f"API returned non-dictionary data for {profile_id}: {type(profile_data)}, value: {profile_data}")
                    return None
                    
                print(f"Successfully retrieved profile data for {profile_id}")
                
                # Only attempt connection if profile data exists    
                connection_message = f"""Hi, I came across your profile and I'm impressed by your experience. I'm interested in connecting with professionals in your field as I believe we could have valuable discussions about industry trends and collaborations. Looking forward to connecting!"""            
                try:
                    error = self.api.add_connection(profile_id, connection_message)
                    if error:
                        print(f"Failed to connect to {profile_id}: {error}")
                except Exception as e:
                    print(f"Connection request failed for {profile_id}: {e}")
                
                return profile_data
            except json.JSONDecodeError as je:
                print(f"JSON decode error for {profile_id}: {je}")
                print(f"Raw response content: {je.doc}...")  # Print first 100 chars of the response
                return None
            except Exception as e:
                print(f"API call failed for {profile_id}: {e}")
                return None
        
        except Exception as e:
            print(f"Failed to process profile {profile_url}: {e}")
            return None

    async def profile(self, search_query: str) -> AsyncGenerator[LinkedInProfile, None]:
        try:
            profiles = await self.search_orchestrator.search(search_query)
            if not profiles:
                print(f"No profiles found for query: {search_query}")
                return
            
            raw_result = []
            futures = [self.executor.submit(self._process_profile, profile) for profile in profiles]
        
            for future in futures:
                try:
                    result = future.result()
                    if result:
                        raw_result.append(result)
                except Exception as e:
                    print(f"Error processing future: {e}")
                    continue

            for profile in raw_result:
                try:
                    if not isinstance(profile, dict):
                        continue
                        
                    yield LinkedInProfile(
                        firstName=profile.get("firstName", ""),
                        secondName=profile.get("lastName", ""),
                        position=profile.get("experience", [{}])[0].get("title", profile.get("headline", "")),
                        area=profile.get("locationName", profile.get("geoCountryName", "")),
                        company=profile.get("experience", [{}])[0].get("companyName", ""),
                        email="",
                        linkedin_url=f"https://www.linkedin.com/in/{profile.get('public_id', '')}",
                        pictureLink=self._get_profile_image(profile),
                        dateInsert=datetime.now()
                    )
                except Exception as e:
                    print(f"Error creating LinkedInProfile: {e}")
                    continue
                
        except Exception as e:
            print(f"Profile search failed: {e}")
            return

    def _get_profile_image(self, profile: dict) -> str:
        try:
            if profile.get("displayPictureUrl"):
                img_size = (profile.get("img_800_800") or 
                        profile.get("img_316_316") or 
                        profile.get("img_200_200") or 
                        profile.get("img_100_100", ""))
                return profile["displayPictureUrl"] + (img_size or "")
            return ""
        except Exception as e:
            print(f"Error getting profile image: {e}")
            return ""
        
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


if __name__ == "__main__":
    import asyncio
    linkedin = LinkedIn()
    async def main():
        async for company in linkedin.profile('albin antony aimleap'):
            print(company)
    asyncio.run(main())
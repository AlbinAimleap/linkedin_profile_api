import aiohttp
import asyncio
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv
load_dotenv()
import os


class Profile(BaseModel):
    first_name: str
    last_name: str
    location: str
    linkedin_url: str
    image_url: str
    position: str
    company_name: Optional[str] = Field(default="")
    company_logo_url: Optional[str] = Field(default="")
    company_linkedin_url: Optional[str] = Field(default="")

class Error(BaseModel):
    error: bool
    message: str
    status_code: int 

    
async def get_profile(linkedin_url):
    url = "https://fresh-linkedin-profile-data.p.rapidapi.com/get-linkedin-profile-by-salesnavurl"

    querystring = {
        "linkedin_url": linkedin_url,
        "include_skills": "false",
        "include_certifications": "false",
        "include_publications": "false",
        "include_honors": "false",
        "include_volunteers": "false",
        "include_projects": "false",
        "include_patents": "false",
        "include_courses": "false",
        "include_organizations": "false"
    }

    headers = {
        "x-rapidapi-key": os.getenv("RAPID_API_KEY"),
        "x-rapidapi-host": "fresh-linkedin-profile-data.p.rapidapi.com"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=querystring) as response:
            data = await response.json()
            if response.status == 429:
                return Error(error=True, message=data.get("message"), status_code=response.status)
            if not isinstance(data, dict) or not data or "data" not in data:
                return Error(error=True, message="Invalid response format", status_code=response.status)
            try:
                if not data.get("data"):
                    return Error(error=True, message="No data returned from API", status_code=response.status)
                experiences = data["data"].get('experiences', [])
                current_company = experiences[0] if experiences else {}            
            except (KeyError, TypeError):
                current_company = {}
            try:
                # Check if current_company is a dictionary before using .get()
                company_name = ""
                company_linkedin_url = ""
                company_logo_url = ""
                position = ""
                
                if isinstance(current_company, dict):
                    position = current_company.get("title", "")
                    company_data = current_company.get("company", {})
                    if isinstance(company_data, dict):
                        company_name = company_data.get("name", "")
                    elif isinstance(company_data, str):
                        company_name = company_data
                    
                    company_linkedin_url = current_company.get("company_linkedin_url", "")
                    company_logo_url = current_company.get("company_logo_url", "")
                
                profile = Profile(
                    first_name=data["data"]['first_name'],
                    last_name=data["data"]['last_name'],
                    location=data["data"]['location'],
                    linkedin_url=data["data"]['linkedin_url'],
                    image_url=data["data"]['profile_image_url'],
                    position=position,
                    company_name=company_name,
                    company_linkedin_url=company_linkedin_url,
                    company_logo_url=company_logo_url,
                )
                return profile
            except KeyError as e:
                return Error(error=True, message=f"Missing required field: {str(e)}", status_code=response.status)


async def get_multiple_profiles(linkedin_urls):
    tasks = []
    for url in linkedin_urls:
        tasks.append(get_profile(url))
    return await asyncio.gather(*tasks)


if __name__ == "__main__":
    linkedin_urls = [
        "https://www.linkedin.com/in/albin-antony-435b1b236",
        "https://www.linkedin.com/in/another-profile",
        "https://www.linkedin.com/in/third-profile"
    ]
    profiles = asyncio.run(get_multiple_profiles(linkedin_urls))
    for profile in profiles:
        print(profile)
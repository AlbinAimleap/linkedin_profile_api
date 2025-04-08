import aiohttp
import asyncio
from pydantic import BaseModel
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
    company_name: str
    company_logo_url: str
    company_linkedin_url: str


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
            try:
                current_company = [i for i in data["data"]['experiences']][0]
            except KeyError:
                current_company = {}
            profile = Profile(
                first_name=data["data"]['first_name'],
                last_name=data["data"]['last_name'],
                location=data["data"]['location'],
                linkedin_url=data["data"]['linkedin_url'],
                image_url=data["data"]['profile_image_url'],
                position=current_company.get("title", ""),
                
                company_name=current_company.get("company", {}),
                company_linkedin_url=current_company.get("company_linkedin_url", ""),
                company_logo_url=current_company.get("company_logo_url", ""),
                
            )

            return profile


if __name__ == "__main__":
    linkedin_url = "https://www.linkedin.com/in/albin-antony-435b1b236"
    profile = asyncio.run(get_profile(linkedin_url))
    print(profile)
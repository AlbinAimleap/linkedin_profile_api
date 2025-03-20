import requests
import json
import time
import random
import re
import urllib.parse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('linkedin_scraper')

@dataclass
class LinkedInCompany:
    """Data class for LinkedIn company information."""
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

class LinkedInVoyagerAPI:    
    BASE_URL = "https://www.linkedin.com/voyager/api"
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    
    def __init__(self, request_timeout: int = 15, cache_enabled: bool = True):
        self.session = requests.Session()
        self.request_timeout = request_timeout
        self.cache_enabled = cache_enabled
        self._cache = {}  
        
        self.headers = {
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/vnd.linkedin.normalized+json+2.1',
            'csrf-token': 'ajax:7848273377210201015',
            'Cookie': 'li_sugr=f1b8545f-44eb-4068-b2e4-854a994f55c0; bcookie="v=2&cb90e5e0-b2be-4867-80db-36048423df31"; bscookie="v=1&2024091807325124b5a6be-d97b-4727-8249-1ec4cdad0973AQEZPlZOhQ1g3dmEgEreQTLN7-L8IAJQ"; li_theme=light; li_theme_set=app; dfpfpt=70b875da6fc74e0c885c5d4d6583771e; _guid=8fbf74c6-d582-4c55-9fcb-f14d049381e2; aam_uuid=38971379282095164373149217299919010018; _gcl_au=1.1.737235657.1739883370; li_rm=AQHk1MtZay5CnwAAAZUZIXFMSOWLDVtUY678X6h7QGjaLUKHNM8daXH7avvCDAuFzgJ4Q6R46gLrRsSogYbkBCNcyx65NTfnqZgkMw8GRJHIWNKbQQxf9KfiJuxyrmjwENjUQQawr_rgyWKI7jHNQ2EPe2qyge-ZSEtpjdERvcSC1W7XJXkvMDPVZH73psX1nLq_T962mPkRoWp-1A8jxmhuGIANf_lno1J8LuIy8nyI0DTvOz8xfFyzaQn0Nb49yYJjJIvPwBc2LU_E1FX9dUIsP-Bo57Fi3iPKARgouKkccsVxUHlutFhbKsBdh7MEtexz8D5M5TAc_k5Y-Rg; visit=v=1&M; AMCV_14215E3D5995C57C0A495C55%40AdobeOrg=-637568504%7CMCIDTS%7C20140%7CMCMID%7C39525479725800950703133215949841042217%7CMCAAMLH-1740661025%7C12%7CMCAAMB-1740661025%7C6G1ynYcLPuiQxYZrsz_pkqfLG9yMXBpb2zX5dvJdYQJzPXImdj0y%7CMCOPTOUT-1740063425s%7CNONE%7CvVersion%7C5.1.1%7CMCCIDH%7C968713793; li_gc=MTswOzE3NDA2MzEyMzM7MjswMjFGTjT0H7rb+vfgqM/gIvsDtj9kxd0z1ZQjYrsIWC68/g==; timezone=Asia/Calcutta; AnalyticsSyncHistory=AQII_5jVd4UStwAAAZWodtZZD-oaTbClAIwruYUTRykTmqVZd0dUPbwkIg1cvUah9QR_mqOV3Y_EjVQP8PwpSg; g_state={"i_l":1,"i_p":1742299059793}; fid=AQEhvzhCoLjRegAAAZWosATRmpzt-pGSPQR7A0eNPZzfo5QOauYW2HpRDLHikyFQmbR-mPugmDDH-w; lang=v=2&lang=en-us; liap=true; JSESSIONID="ajax:7848273377210201015"; fptctx2=taBcrIH61PuCVH7eNCyH0APzNoEiOrOqF4FbdtfiWWJ1P5lj125kKvyDmAboZqs%252baU%252f2PLz13gqmKU0l29i%252fGUrCj8NghLvPrJ8S36E0eBN54N%252b%252b9Vrj0e2mMTpmwwzpKbpnmNc%252bnwOcVYcZC%252bWfDZaR7egKoo7Ziu54AISP2FjJ%252fQ6cIIbX3mr8ebDT3SGoY9TrxAGR21g9JFSb%252fKFyRmGpD9RPttZWYu0iPtm62wd%252bzVekmO8Xt65aUOzu9eAZMpIlrx8dsnHUySiq6iVHNvcQUyAxBybTvytuNzNvidCCAhRabsMOqLTHs1hlzS%252bcNxYSxm97cznB%252fjTTjJMpNcXKrcmB2FQu7TS3zkv%252fXeA%253d; PLAY_SESSION=eyJhbGciOiJIUzI1NiJ9.eyJkYXRhIjp7ImZsb3dUcmFja2luZ0lkIjoiS0gxSXl0MFNRMmVaZVIzUTMwYndnZz09In0sIm5iZiI6MTc0MjQ1MjM0MywiaWF0IjoxNzQyNDUyMzQzfQ.huuxrdheO2gjLRjXD121d_e33PQnOloKnHkm1X4s4ZY; li_at=AQEDATrmAakFOggyAAABlbJBBccAAAGV1k2Jx1YAfEUQK7Q4ldSrJU3E_OcAxXh-5zCKpNitSFhwH5YNfpq6HqdDWF3yTZh0uiQASNPEoq5sX6cbL6bpCA6dFPyEw0EqqVVED9-yICRb814l1q3mqRZS; UserMatchHistory=AQJwkR8QSrrnAwAAAZWzKc4_BPUEu6kewtAtHNpW0GDhn01p8EWOShkfRIccOpAyTQsojfv4fy6WqQ; lms_ads=AQGKBs8UYG8u2gAAAZWzKc83XyY4jBEZXUG7eATzzCHBACR0Q3pwtN2FszhHHAfbZKZvLdfj-RmN_vscLHGpWHI9pbvwDVsb; lms_analytics=AQGKBs8UYG8u2gAAAZWzKc83XyY4jBEZXUG7eATzzCHBACR0Q3pwtN2FszhHHAfbZKZvLdfj-RmN_vscLHGpWHI9pbvwDVsb; lidc="b=OB33:s=O:r=O:a=O:p=O:g=4387:u=1151:x=1:i=1742467620:t=1742536088:v=2:sig=AQERGA3DgXm_6nT32RYMyOoa1GMIk2d1"; __cf_bm=zORfCaiLa8WldR5bnlu2EWSilEKoiT52Fw2HsC0icac-1742468239-1.0.1.1-kXsi1nDpNFkr4usEGgtXFD3tCPNamoxvc5x0OTHCWZGZwuI9fS4dQc_AEOvhJp.igIxIB151swoDAXvayJS9n8QdzBan6omwbaV9ua67jFw; bcookie="v=2&d204714b-1d2e-48e7-89ba-b00ef013003c"; lidc="b=OB33:s=O:r=O:a=O:p=O:g=4387:u=1151:x=1:i=1742468268:t=1742536088:v=2:sig=AQF4MoAmuqNQCiiF-N6Qx_SJGHabhY8o"'
        }
        
       
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5), reraise=True)
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        cache_key = None
        if self.cache_enabled:
            cache_key = f"{url}:{json.dumps(params or {})}"
            if cache_key in self._cache:
                logger.debug(f"Cache hit for {url}")
                return self._cache[cache_key]

        time.sleep(random.uniform(0.1, 0.5))
        
        try:
            response = self.session.get(
                url,
                headers=self.headers,
                params=params,
                timeout=self.request_timeout
            )
            
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self._make_request(url, params)
            
            if response.status_code != 200:
                logger.error(f"API request failed: {url} with status {response.status_code}")
                return {}
            
            data = response.json()
            
            if self.cache_enabled and cache_key:
                self._cache[cache_key] = data
            
            return data
            
        except Exception as e:
            logger.error(f"Error making request to {url}: {str(e)}")
            raise
    
    def extract_id_from_url(self, url: str, entity_type: str = 'profile') -> str:
        url = url.rstrip('/')
        
        if entity_type == 'profile':
            if '/in/' in url:
                return url.split('/in/')[1].split('/')[0]
        elif entity_type == 'company':
            if '/company/' in url:
                company_path = url.split('/company/')[1].split('/')[0]
                return company_path
        
        parts = url.split('/')
        return parts[-1]
    
    def get_profile_data(self, public_id: str) -> Dict:
        logger.info(f"Fetching profile data for: {public_id}")
        
        encoded_id = urllib.parse.quote(public_id)

        profile_url = f"{self.BASE_URL}/identity/profiles/{encoded_id}"
        profile_data = self._make_request(profile_url)

        result = {
            'first_name': '',
            'last_name': '',
            'location': '',
            'profile_url': f"https://www.linkedin.com/in/{public_id}/",
            'picture_url': '',
            'email': '',
            'phone': '',
            'company': '',
            'position': ''
        }

        if 'miniProfile' in profile_data:
            data = profile_data['miniProfile']
            result['first_name'] = data.get('firstName', '')
            result['last_name'] = data.get('lastName', '')
            result['location'] = data.get('locationName', '')

            if 'picture' in data and 'com.linkedin.common.VectorImage' in data['picture']:
                img_data = data['picture']['com.linkedin.common.VectorImage']
                root_url = img_data.get('rootUrl', '')
                artifacts = img_data.get('artifacts', [])
                if artifacts:
                    largest_artifact = max(artifacts, key=lambda x: x.get('width', 0) * x.get('height', 0))
                    file_path = largest_artifact.get('fileIdentifyingUrlPathSegment', '')
                    result['picture_url'] = root_url + file_path
        
        if "data" in profile_data:
       
            result['first_name'] = profile_data.get("data", {}).get('firstName', '')
            result['last_name'] = profile_data.get("data", {}).get('lastName', '')
            result['location'] = profile_data.get("data", {}).get('locationName', '')
            
            try:
                root_url = profile_data.get("data", {}).get("profilePictureOriginalImage", {}).get("rootUrl", "")
                artifacts = profile_data.get("data", {}).get("profilePictureOriginalImage", {}).get("artifacts", [])
                if artifacts:
                    largest_artifact = max(artifacts, key=lambda x: x.get('width', 0) * x.get('height', 0))
                    file_path = largest_artifact.get('fileIdentifyingUrlPathSegment', "")
                    result['picture_url'] = root_url + file_path
            except AttributeError as e:
                logger.error(f"Error extracting profile picture: {str(e)}")
           
    
        elif 'included' in profile_data:
            for element in profile_data['included']:
                if element.get('$type') == 'com.linkedin.voyager.identity.profile.Profile':
                    result['first_name'] = element.get('firstName', '')
                    result['last_name'] = element.get('lastName', '')
                    result['location'] = element.get('locationName', '')
                    
                    if 'profilePicture' in element:
                        self._extract_profile_picture(element, result)
                    break

        contact_info = self.get_contact_info(public_id)
        result.update(contact_info)

        position_info = self.get_position_info(public_id)
        result.update(position_info)
        return result
    
    
    def get_contact_info(self, public_id: str) -> Dict:
        logger.info(f"Fetching contact info for: {public_id}")
        
        encoded_id = urllib.parse.quote(public_id)
        contact_url = f"{self.BASE_URL}/identity/profiles/{encoded_id}/profileContactInfo"
        
        try:
            data = self._make_request(contact_url)
            
            result = {
                'email': '',
                'phone': ''
            }

            if 'data' in data and 'emailAddress' in data['data']:
                result['email'] = data['data']['emailAddress']
            elif 'emailAddress' in data:
                result['email'] = data['emailAddress']

            if 'data' in data and 'phoneNumbers' in data['data'] and data['data']['phoneNumbers']:
                result['phone'] = data['data']['phoneNumbers'][0].get('number', '')
            elif 'phoneNumbers' in data and data['phoneNumbers']:
                result['phone'] = data['phoneNumbers'][0].get('number', '')
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching contact info: {str(e)}")
            return {'email': '', 'phone': ''}
    
    def get_position_info(self, public_id: str) -> Dict:
        logger.info(f"Fetching position info for: {public_id}")
        
        encoded_id = urllib.parse.quote(public_id)
        positions_url = f"{self.BASE_URL}/identity/profiles/{encoded_id}/positions"
        
        try:
            data = self._make_request(positions_url)
            
            result = {
                'company': '',
                'position': ''
            }
            
            if "included" in data:
                positions = [item for item in data['included'] if item.get('$type') == 'com.linkedin.voyager.identity.profile.Position']
                if positions:
                    latest_position = max(positions, key=lambda x: (
                        x.get('timePeriod', {}).get('startDate', {}).get('year', 0) * 100 +
                        x.get('timePeriod', {}).get('startDate', {}).get('month', 0)
                    ))
                    
                    result['company'] = latest_position.get('companyName', '')
                    result['position'] = latest_position.get('title', '')
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching position info: {str(e)}")
            return {'company': '', 'position': ''}    
        
        
    def get_profile_by_url(self, profile_url: str) -> Dict:
        public_id = self.extract_id_from_url(profile_url, 'profile')
        data = self.get_profile_data(public_id)
        return data
    
    def scrape_profiles(self, profiles: List[str], delay_range: tuple = (2, 5)) -> List[Dict]:
        results = []
        
        for i, identifier in enumerate(profiles):
            try:
                logger.info(f"Processing profile {i + 1}/{len(profiles)}: {identifier}")
                if identifier.startswith('http'):
                    profile_data = self.get_profile_by_url(identifier)
                else:
                    profile_data = self.get_profile_data(identifier)

                results.append(profile_data)
                logger.info(f"Successfully scraped profile: {identifier}")

                if i < len(profiles) - 1:
                    delay = random.uniform(delay_range[0], delay_range[1])
                    logger.info(f"Waiting {delay:.2f} seconds before next request...")
                    time.sleep(delay)

            except Exception as e:
                logger.error(f"Error scraping profile {identifier}: {str(e)}")

        return results
    
    def get_company_data(self, company_identifier: str) -> LinkedInCompany:
        logger.info(f"Fetching company data for: {company_identifier}")
        if company_identifier.startswith('http'):
            company_id = self.extract_id_from_url(company_identifier, 'company')
        else:
            company_id = company_identifier

        encoded_id = urllib.parse.quote(company_id)

        company_url = f"{self.BASE_URL}/organization/companies/{encoded_id}"
        
        
        try:
            company_data = self._make_request(company_url)
        except Exception as e:
            logger.error(f"Error fetching company data: {str(e)}")
            raise

        name = self._extract_company_name(company_data)
        picture_link = self._extract_company_logo(company_data)

        linkedin_url = f"https://www.linkedin.com/company/{company_id}/"

        current_date = datetime.now()

        company = LinkedInCompany(
            name=name,
            linkedin_url=linkedin_url,
            pictureLink=picture_link,
            dateInsert=current_date,
            company_logo=picture_link
        )
        
        try:
            about_url = f"{self.BASE_URL}/organization/companies/{encoded_id}/about"
            about_data = self._make_request(about_url)
            company.employees = self._extract_employees_count(about_data)
            company.address = self._extract_company_address(about_data)
            company.description = self._extract_company_description(about_data)
            company.short_description = self._extract_company_short_description(about_data)
            company.phone = self._extract_company_phone(about_data)
            company.founded_on = self._extract_founding_year(about_data)
            
        except Exception as e:
            logger.warning(f"Could not fetch complete company details: {str(e)}")
        
        return company
    
    def _extract_company_name(self, data: Dict) -> str:
        if 'data' in data and 'name' in data['data']:
            return data['data']['name']
        
        if 'included' in data:
            for item in data['included']:
                if item.get('$type') == 'com.linkedin.voyager.organization.Company' and 'name' in item:
                    return item['name']
        
        if 'name' in data:
            return data['name']

        return ""
    
    def _extract_company_logo(self, data: Dict) -> str:
        if 'data' in data and 'logo' in data['data']:
            logo_data = data['data']['logo']
            if 'com.linkedin.common.VectorImage' in logo_data:
                vector_image = logo_data['com.linkedin.common.VectorImage']
                root_url = vector_image.get('rootUrl', '')
                
                if 'artifacts' in vector_image and vector_image['artifacts']:
                    largest_artifact = max(
                        vector_image['artifacts'],
                        key=lambda x: x.get('width', 0) * x.get('height', 0)
                    )
                    file_path = largest_artifact.get('fileIdentifyingUrlPathSegment', '')
                    return root_url + file_path

        if 'included' in data:
            for item in data['included']:
                if item.get('$type') == 'com.linkedin.voyager.organization.Company' and 'logo' in item:
                    logo_data = item['logo']
                    if 'com.linkedin.common.VectorImage' in logo_data:
                        vector_image = logo_data['com.linkedin.common.VectorImage']
                        root_url = vector_image.get('rootUrl', '')
                        
                        if 'artifacts' in vector_image and vector_image['artifacts']:
                            largest_artifact = max(
                                vector_image['artifacts'],
                                key=lambda x: x.get('width', 0) * x.get('height', 0)
                            )
                            file_path = largest_artifact.get('fileIdentifyingUrlPathSegment', '')
                            return root_url + file_path

        return ""
    
    def _extract_employees_count(self, data: Dict) -> Optional[str]:
        if 'data' in data and 'staffCount' in data['data']:
            return str(data['data']['staffCount'])
        
        if 'data' in data and 'staffCountRange' in data['data']:
            staff_range = data['data']['staffCountRange']
            if 'start' in staff_range and 'end' in staff_range:
                return f"{staff_range['start']}-{staff_range['end']}"
        
        if 'included' in data:
            for item in data['included']:
                if 'staffCount' in item:
                    return str(item['staffCount'])
                if 'staffCountRange' in item:
                    staff_range = item['staffCountRange']
                    if 'start' in staff_range and 'end' in staff_range:
                        return f"{staff_range['start']}-{staff_range['end']}"
        
        return None
    
    def _extract_company_address(self, data: Dict) -> Optional[str]:
        if 'data' in data and 'headquarter' in data['data']:
            hq = data['data']['headquarter']
            if 'country' in hq and 'city' in hq:
                return f"{hq.get('city', '')}, {hq.get('country', '')}"
        
        if 'included' in data:
            for item in data['included']:
                if 'headquarter' in item:
                    hq = item['headquarter']
                    if 'country' in hq and 'city' in hq:
                        return f"{hq.get('city', '')}, {hq.get('country', '')}"

        if 'data' in data and 'locations' in data['data'] and data['data']['locations']:
            location = data['data']['locations'][0]
            address_parts = []
            for field in ['city', 'geographicArea', 'country']:
                if field in location and location[field]:
                    address_parts.append(location[field])
            if address_parts:
                return ", ".join(address_parts)
        
        return None
    
    def _extract_company_description(self, data: Dict) -> Optional[str]:
        if 'data' in data and 'description' in data['data']:
            return data['data']['description']
        
        if 'included' in data:
            for item in data['included']:
                if 'description' in item:
                    return item['description']
        
        return None
    
    def _extract_company_short_description(self, data: Dict) -> Optional[str]:
        if 'data' in data and 'tagline' in data['data']:
            return data['data']['tagline']
        
        if 'included' in data:
            for item in data['included']:
                if 'tagline' in item:
                    return item['tagline']
        
        return None
    
    def _extract_company_phone(self, data: Dict) -> Optional[str]:
        if 'data' in data and 'phone' in data['data']:
            return data['data']['phone']
        
        if 'included' in data:
            for item in data['included']:
                if 'phone' in item:
                    return item['phone']
        
        return None
    
    def _extract_founding_year(self, data: Dict) -> Optional[int]:
        if 'data' in data and 'foundedOn' in data['data']:
            founded = data['data']['foundedOn']
            if 'year' in founded:
                return founded['year']
        
        if 'included' in data:
            for item in data['included']:
                if 'foundedOn' in item and 'year' in item['foundedOn']:
                    return item['foundedOn']['year']
        
        return None
    
    def get_company_by_url(self, company_url: str) -> LinkedInCompany:
        return self.get_company_data(company_url)
    
    def scrape_companies(self, companies: List[str], delay_range: tuple = (2, 5)) -> List[LinkedInCompany]:
        results = []
        
        for i, identifier in enumerate(companies):
            try:
                logger.info(f"Processing company {i + 1}/{len(companies)}: {identifier}")
                company_data = self.get_company_data(identifier)
                results.append(company_data)
                logger.info(f"Successfully scraped company: {identifier}")
                if i < len(companies) - 1:
                    delay = random.uniform(delay_range[0], delay_range[1])
                    logger.info(f"Waiting {delay:.2f} seconds before next request...")
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Error scraping company {identifier}: {str(e)}")
        
        return results



if __name__ == "__main__":
    api = LinkedInVoyagerAPI()

    profile_data = api.get_profile_by_url("https://www.linkedin.com/in/albin-antony-435b1b236/")

    

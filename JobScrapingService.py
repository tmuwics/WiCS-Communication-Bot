from bs4 import BeautifulSoup 
import urllib.request
import requests 
import base64
import json
import os
from dotenv import load_dotenv 
class JobScrapingService:
    
    def __init__(self,logger):
        load_dotenv()
        self.summer_internships = os.getenv("SUMMER_LINK")
        self.offseason_internships = os.getenv("OFFSEASON_LINK")
        self.newgrad_internships =  os.getenv("NEWGRAD_LINK")
        self.logger = logger

    def get_github_internship2024(self):
        URL = self.summer_internships
        request = requests.get(URL) 
        request.encoding = request.apparent_encoding 
        soup = BeautifulSoup(request.text, 'html5lib') 
        self.logger.log_data_scrapped(URL,"Summer roles scraped")
        return str(soup.encode("utf-8"))
    
    def get_github_offseason2024(self):
        url = self.offseason_internships
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        readme = response.content.decode("utf-8")
        self.logger.log_data_scrapped(url, "Offseason roles scraped")
        return readme
    
    def get_github_newgrad2024(self):
        URL = self.newgrad_internships
        response = requests.get(URL) 
        data = response.json()
        readme_content = base64.b64decode(data['content'])
        self.logger.log_data_scrapped(URL,"Newgrad roles scraped")
        return str(readme_content)

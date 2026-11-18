import re
import pandas as pd
import json
from datetime import datetime, timedelta
import os
import time
import ast
from bs4 import BeautifulSoup
# WICS 2024-2025: Note this class made need to be restructed depending on whether you use a SimplyJobs Repo or not.
class TextFormattingHandler:
    def __init__(self):
        self.table_start="Please leave a one line gap between this and the table TABLE_START (DO NOT CHANGE THIS LINE) -->\\n\\n"
        self.table_end ="\\n\\n<!-- Please leave a one line gap between this and the table TABLE_END (DO NOT CHANGE THIS LINE) -->"
        self.DATE_FORMAT = "%m/%d"

    def readme_to_dataframe(self, text):
    # The existing fetchers return str(bytes), which escapes newlines
    # and non-ASCII characters. Recover the original text before parsing.
        if text.startswith(("b'", 'b"')):
            text = ast.literal_eval(text).decode("utf-8")

        headers = ["Company", "Role", "Location", "Application", "Age"]
        columns = ["Company", "Role", "Location", "Application Link", "Date Posted"]
        soup = BeautifulSoup(text, "html.parser")
        today = datetime.today().date()
        rows = []
        found_table = False

        for table in soup.find_all("table"):
            table_headers = [cell.get_text(strip=True) for cell in table.select("thead th")]
            if table_headers != headers:
                continue

            found_table = True
            previous_company = ""

            for row in table.select("tbody tr"):
                cells = row.find_all("td", recursive=False)
                if len(cells) != len(headers):
                    continue

                company, role, location, application, age = cells
                company_name = company.get_text(" ", strip=True)
                if company_name and company_name != "↳":
                    previous_company = company_name

                age_match = re.fullmatch(r"(\d+)d", age.get_text(strip=True))
                if not previous_company or age_match is None:
                    continue

                posted_date = today - timedelta(days=int(age_match.group(1)))
                rows.append([
                    previous_company,
                    role.get_text(" ", strip=True),
                    location.decode_contents(),
                    application.decode_contents(),
                    posted_date.strftime(self.DATE_FORMAT),
                ])

        if not found_table:
            raise ValueError("No summer or new-grad job table found in the README")

        df = pd.DataFrame(rows, columns=columns)
        df.index.name = "Number"
        return df
    
    def readme_offseason_to_dataframe(self, text): # Formats offseason readme
        # The existing fetchers return str(bytes), which escapes newlines
            # and non-ASCII characters. Recover the original text before parsing.
                if text.startswith(("b'", 'b"')):
                    text = ast.literal_eval(text).decode("utf-8")
        
                headers = ["Company", "Role", "Location", "Application", "Age"]
                columns = ["Company", "Role", "Location", "Terms", "Application Link", "Date Posted"]
                soup = BeautifulSoup(text, "html.parser")
                today = datetime.today().date()
                rows = []
                found_table = False
        
                for table in soup.find_all("table"):
                    table_headers = [cell.get_text(strip=True) for cell in table.select("thead th")]
                    if table_headers != headers:
                        continue
        
                    found_table = True
                    previous_company = ""
        
                    for row in table.select("tbody tr"):
                        cells = row.find_all("td", recursive=False)
                        if len(cells) != len(headers):
                            continue
        
                        company, role, location, application, age = cells
                        company_name = company.get_text(" ", strip=True)
                        if company_name and company_name != "↳":
                            previous_company = company_name
        
                        age_match = re.fullmatch(r"(\d+)d", age.get_text(strip=True))
                        if not previous_company or age_match is None:
                            continue
        
                        posted_date = today - timedelta(days=int(age_match.group(1)))
                        rows.append([
                            previous_company,
                            role.get_text(" ", strip=True),
                            location.decode_contents(),
                            application.decode_contents(),
                            posted_date.strftime(self.DATE_FORMAT),
                        ])
        
                if not found_table:
                    raise ValueError("No off-season job table found in the README")
        
                df = pd.DataFrame(rows, columns=columns)
                df.index.name = "Number"
                return df

    def json_to_dataframe(self,json_data): # Json from zobjobs endpoint to dataframe
        data = json.loads(json_data)
        df = pd.DataFrame.from_dict(data["jobs"], orient='columns')
        
        # Drop unnecessary columns
        df = df.drop("sourced",axis=1)
        df = df.drop("unique",axis=1)
        return df
        
    def format_timestamp(self,text): # Format date in df
        date = text.strip()
        try:
            # Create datetime object for MM/DD format
            date = datetime.strptime(date,'%b %d').strftime(self.DATE_FORMAT)
            return date
        except(TypeError): 
            # Create datetime object for MM/YYYY format
            date = datetime.strptime(date,'%b %Y').strftime(self.DATE_FORMAT)
            return date
        except(ValueError):
            return text

    def get_previous_date(self,text): # Get one day ago given a date
        try: # Create datetime object 
            date_object = datetime.strptime(text + '/' + str(datetime.now().year), '%m/%d/%Y')
            yesterday = date_object - timedelta(days=1)
            # Format into readable string
            readable_dt_str = yesterday.strftime(self.DATE_FORMAT)
            # If no posting on current day
            if datetime.today()-yesterday!= datetime.today()-timedelta(days=1):
                return date_object.strftime(self.DATE_FORMAT)
            
            return readable_dt_str
        except(TypeError): # Given a datetime object
            yesterday = text - timedelta(days=1)
            # Format into readable string
            readable_dt_str = yesterday.strftime(self.DATE_FORMAT)
            return readable_dt_str
        except(ValueError):
            return text        


import time
import hashlib
import logging
from pymongo import MongoClient, errors
from datetime import datetime, date
import asyncio

# logging.getLogger().setLevel(logging.CRITICAL)

from jobspy import scrape_jobs

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def load_txt_file(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file.readlines()]


'''
MongoDB Configuration
'''
# MongoDB configuration
def mongodb(mongo_uri):
    client = MongoClient(mongo_uri) 
    db = client['postings']
    job_collection = db['jobspy_scraped']
    job_logs = db['jobspy_logs']
    return job_collection, job_logs

'''
Handling duplicates
'''
# normalize field
def normalize_field(value):
    # normalize a field by lowercasing and stripping whitespace.
    return value.lower().strip() if isinstance(value, str) else ""

# generate hash_id for deduplication
def generate_hash(job):
    # generate a unique hash for a job posting.
    title = normalize_field(job.get("title", ""))
    company = normalize_field(job.get("company", ""))
    location = normalize_field(job.get("location", ""))
    job_type = normalize_field(job.get("job_type", ""))
    
    # Combine normalized fields
    unique_string = f"{title}_{company}_{location}_{job_type}"
    # Create hash
    return hashlib.sha256(unique_string.encode()).hexdigest()

def convert_date_to_string(date_value):
    # datetime.date to string
    if isinstance(date_value, date):
        return date_value.strftime('%Y-%m-%d') 
    return date_value

def process_job(job):
    # This is the synchronous part of processing
    job_data = {
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "job_url": job.get("job_url"),
        "date_posted": convert_date_to_string(job.get("date_posted")),
        "is_posted": False,
    }
    job_data["hash_id"] = generate_hash(job_data)
    return job_data

async def job_spy(uri):

    keywords = ["intern", "co-op"]
    position_keywords = load_txt_file('position_keywords.txt')
    positions = load_txt_file('positions.txt')
    google_position_queries = [f"{name} jobs in Canada since yesterday" for name in positions]
    position_names = [f"{name} intern" for name in positions]
    job_collection, job_logs = mongodb(uri)

    job_logs.insert_one({"message": "Jobspy starting scraping..."})
    for search_term, google_search_term in zip(position_names, google_position_queries):
        try:
            jobs = scrape_jobs(
                site_name=["linkedin"],
                search_term=search_term,
                google_search_term=google_search_term,
                location="Canada",
                results_wanted=30,
                hours_old=72,
                country_indeed='Canada',
                # proxies=["208.195.175.46:65095", "208.195.175.45:65095", "localhost"],
            )
            # filtering based on intern or co-op and position names
            jobs = jobs[jobs['title'].str.contains('|'.join(keywords), case=False, na=False)]
            jobs = jobs[jobs['title'].str.contains('|'.join(position_keywords), case=False, na=False)]
        
            for _, job in jobs.iterrows():
                job_data =  await asyncio.to_thread(process_job, job) 
                if not job_collection.find_one({"hash_id": job_data["hash_id"]}):
                    try:
                        job_collection.insert_one(job_data) 
                      
                    except Exception as e:
                        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')  
                        msg = f"Failed to insert job for {search_term}"
                        log_entry = {
                            "error": msg,
                            "exception": str(e), 
                            "timestamp": current_time  
                        }
                        await asyncio.to_thread(job_logs.insert_one, log_entry)      
        except Exception as e:
            current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')  
            msg = f"Failed to scrape job for {search_term}"
            log_entry = {
                "error": msg,
                "exception": str(e), 
                "timestamp": current_time  
            }
            await asyncio.to_thread(job_logs.insert_one, log_entry)
        
    # add a pause after scraping each position
    await asyncio.sleep(2) 
    # time.sleep(2)


async def scrape_and_store(*args, **kwargs):
    return await job_spy(*args, **kwargs)

def fetch_unposted_jobs(uri):
    job_collection, _ = mongodb(uri)
    return list(job_collection.find({"is_posted":False}))

def mark_as_posted(uri, job_id):
    job_collection, _ = mongodb(uri)
    job_collection.update_one({"_id": job_id}, {"$set":{"is_posted": True}})
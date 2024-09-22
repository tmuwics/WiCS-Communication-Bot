import pandas as pd
from DataFrameAccessor import DataFrameAccessor
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import hashlib
import time
import certifi

ca = certifi.where()

class LoggingService:
    def __init__(self,uri,max_retries = 3,delay=5):
        # Load DB
        client = MongoClient(uri, ssl=True, tlsCAFile=ca, server_api=ServerApi('1'))
        for attempt in range(max_retries):
            try:
                client.admin.command('ping')
                print("Pinged your deployment. You successfully connected to MongoDB!")
                self.db = client['postings']
                self.openings_collection = self.db["Openings"]
                self.logging_collection = self.db["Logs"]
                break  # If successful, exit the loop
            except Exception as e:
                print(f"Attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:  # Only sleep if this is not the last attempt
                    time.sleep(delay)  # Wait for some time before retrying
                else:
                    raise
            databases = client.list_database_names()
            print("Databases:", databases)

    def log_startup(self):
        unique_id = hashlib.sha256(str(datetime.now()).encode()).hexdigest()
        doc = {
            "_id":unique_id,
            "Timestamp":datetime.now(),
            "Process":"Startup",
            "Details":"Discord Bot startup",
        }
        self.logging_collection.insert_one(doc)

    def log_posting(self,row,message):
        # Log when a post embed is being created
        unique_id = hashlib.sha256((str(datetime.now())+str(row)).encode()).hexdigest()
        doc = {
            "_id":unique_id,
            "Timestamp":datetime.now(),
            "Process":"Posting",
            "Details":message,
            "Embed details":str(row)
        }
        self.logging_collection.insert_one(doc)

    def log_catch_duplicate(self,row,message):
        # Log when a post embed is trying to post more than once
        unique_id = hashlib.sha256((str(datetime.now())+str(row)).encode()).hexdigest()
        doc = {
            "_id":unique_id,
            "Timestamp":datetime.now(),
            "Process":"Duplicate",
            "Details":message,
            "Embed details":str(row)
        }
        self.logging_collection.insert_one(doc)

    def log_post_failure(self,row,message,err):
        # Log post failure 
        unique_id = hashlib.sha256((str(datetime.now())+str(row)).encode()).hexdigest()
        doc = {
            "_id":unique_id,
            "Timestamp":datetime.now(),
            "Process":"Post Failure",
            "Details":message,
            "Embed details":str(row),
            "Error":str(err)
        }
        self.logging_collection.insert_one(doc)    

    def log_task_start_exception(self,message,err):
        # Log when a task exception happens
        unique_id = hashlib.sha256((str(datetime.now()+message)).encode()).hexdigest()
        doc = {
            "_id":unique_id,
            "Timestamp":datetime.now(),
            "Process":"Task Start Exception",
            "Details":message,
            "Error":str(err)
        }
        self.logging_collection.insert_one(doc)

    def log_task_exception(self,message,err):
        # Log when an task fails inside the loop
        unique_id = hashlib.sha256((str(datetime.now())+message).encode()).hexdigest()
        doc = {
            "_id":unique_id,
            "Timestamp":datetime.now(),
            "Process":"Task Exception",
            "Details":message,
            "Error":str(err)
        }
        self.logging_collection.insert_one(doc)

    def log_data_scrapped(self,url,message):
        # log when data was scrapped from readme
        unique_id = hashlib.sha256((str(datetime.now())+url).encode()).hexdigest()
        doc = {
            "_id":unique_id,
            "Timestamp":datetime.now(),
            "Process":"Data Scraped",
            "Details":message,
        }
        self.logging_collection.insert_one(doc)

    def log_data_accessor_exception(self,row,message,err):
        # Log when exception/error happens in DataFrameAccessor.py
        unique_id = hashlib.sha256((str(datetime.now()) + str(row)).encode()).hexdigest()
        doc = {
            "_id":unique_id,
            "Timestamp":datetime.now(),
            "Process":"Accessing Row Data",
            "Embed details":str(row),
            "Details":message,
            "Error":str(err)
        }
        self.logging_collection.insert_one(doc)

    def check_space(self):
        # Do not go over Mongodb Atlas limit
        openings_size =  self.db.command("collStats","Openings")['totalSize'] / (1024 * 1024)
        log_size =  self.db.command("collStats","Logs")['totalSize'] / (1024 * 1024)
        print(f'Posts: {openings_size} | Logs: {log_size }')

        if openings_size  > 500:
            unique_id = hashlib.sha256((str(datetime.now())+str(openings_size)).encode()).hexdigest()
            doc = {
            "_id":unique_id,
            "Timestamp":datetime.now(),
            "Process":"Clearing Collection",
            "Details":"Openings Size reaching capacity",
            }
            self.logging_collection.insert_one(doc)
            self.openings_collection.delete_many({})
        if log_size >500:
            unique_id = hashlib.sha256((str(datetime.now())+str(log_size)).encode()).hexdigest()
            doc = {
            "_id":unique_id,
            "Timestamp":datetime.now(),
            "Process":"Clearing Collection",
            "Details":"Logs Size reaching capacity",
            }
            self.logging_collection.delete_many({})
            self.logging_collection.insert_one(doc)

    def update_postings_db(self,post,hash_id):
        # Add postings to db
        try:
            doc =self.openings_collection.find_one({'_id':hash_id})
            if doc is not None:
                return doc
            else:
                doc = post.to_dict()
                doc["_id"]=hash_id
                self.openings_collection.insert_one(doc)
                return None
        except Exception as ex:
            unique_id = hashlib.sha256((str(datetime.now())+post).encode()).hexdigest()
            doc = {
                "_id":unique_id,
                "Timestamp":datetime.now(),
                "Process":"Collection update Exception",
                "Embed details":post,
                "Details":None,
                "Error":str(ex)
            }
            self.logging_collection.insert_one(doc)
            print(ex)            
    
    def check_shared_status(self,hash_id):
        doc = self.openings_collection.find_one({'_id':hash_id}) 
        if doc is not None:
            return doc["Shared"]
            
    def set_sucessful_shared_status(self,hash_id):
        doc = self.openings_collection.find_one({'_id':hash_id}) 
        if doc is not None:
            update = {"$set": {"Shared": True}}
            self.openings_collection.update_one({"_id":hash_id},update)
        
    def set_failed_shared_status(self,hash_id):
        doc = self.openings_collection.find_one({'_id':hash_id}) 
        if doc is not None:
            update = {"$set": {"Shared": False}}
            self.openings_collection.update_one({"_id":hash_id},update)



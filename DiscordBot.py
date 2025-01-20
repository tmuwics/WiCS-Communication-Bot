import discord 
import time
from discord.ext import tasks,commands
import os
import logging
from dotenv import load_dotenv 
from JobPostingFetcher import JobPostingFetcher 
from DataFrameAccessor import DataFrameAccessor
from LoggingService import LoggingService
from TextFormattingHandler import TextFormattingHandler
from JobScrapingService import JobScrapingService
from JobSpyScrape import fetch_unposted_jobs, mark_as_posted, scrape_and_store

# Setup Bot
load_dotenv()

TOKEN = os.getenv("TOKEN")
URI = os.getenv("MONGODB_URI")
CHANNEL_1 = int(os.getenv("CHANNEL_ID_1"))
CANADIAN_CHANNEL = int(os.getenv("CANADIAN_CHANNEL_ID"))
client = commands.Bot(command_prefix="/",intents=discord.Intents.default()) 

# Create instances for postings
logger = LoggingService(URI)
data_accessor = DataFrameAccessor(logger)
formatter = TextFormattingHandler()
data_scraper = JobScrapingService(logger)
job_fetcher = JobPostingFetcher(formatter,data_scraper,data_accessor)

# Define icons for different types of roles
newgrad_icon = "https://cdn-icons-png.flaticon.com/128/1991/1991047.png"
internship_icon = "https://cdn-icons-png.flaticon.com/128/7376/7376577.png"
offseason_icon = "https://cdn-icons-png.flaticon.com/128/2117/2117739.png"
canadian_job_img = "https://i.imghippo.com/files/nav7918c.png"

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    logger.log_startup()

    # Start tasks for sending roles
    try:
        send_new_grad_roles.start()
    except Exception as ex:
        logger.log_task_start_exception("TASK START EXCEPTION: New grad roles",ex)
    try:
        send_summer_roles.start()
    except Exception as ex:
        logger.log_task_start_exception("TASK START EXCEPTION: Summer roles",ex)
    try:
        send_offseason_roles.start()
    except Exception as ex:
        logger.log_task_start_exception("TASK START EXCEPTION: Offseason roles",ex)
    try:
        post_jobs_command.start()
    except Exception as e:
        logging.error(f"Error during calling jobspy scraper: {e}")

@tasks.loop(hours=24)
async def send_new_grad_roles():
    # This function runs every 24 hours and sends new grad roles
    logger.check_space()
    job_channel = client.get_channel(CHANNEL_1)
    df_posting = job_fetcher.latest_newgrad_postings()
    newgrad_color = 0xf2f0ff

    try:
        for i, row in df_posting.iterrows():
            data = row
            hash_id=data_accessor.create_id("newgrad", data)
            doc_exist = logger.update_postings_db(data,hash_id)

            if doc_exist is not None: data = doc_exist

            company = data_accessor.get_company_text(data)
            role = data_accessor.get_role(data)
            date_posted =data_accessor.get_date_posted(data)
            locations = data_accessor.get_locations(data)
            link = data_accessor.get_application_link(data)

            logger.log_posting(data,f"Posting New Grad role for {company}: {role}")

            if logger.check_shared_status(hash_id):
                logger.log_catch_duplicate(data,f"> {company}: {role} was already posted today.\n")
                continue
            else:
                embed=discord.Embed(description="New Grad", title=company, color=newgrad_color)
                embed.set_thumbnail(url=newgrad_icon)
                embed.add_field(name="Role", value=role, inline=True)
                embed.add_field(name="Date Posted", value=date_posted, inline=True)
                embed.add_field(name="Location", value=locations, inline=False)
                embed.add_field(name="Application Link", value=link, inline=False)
                embed.set_footer(text="Resume icons created by juicy_fish - Flaticon")
                
                try:
                    await job_channel.send(embed=embed)
                    logger.set_sucessful_shared_status(hash_id)
                except Exception as ex:
                    logger.set_failed_shared_status(hash_id)
                    logger.log_post_failure(data,f"New grad role {company} failed to send",str(ex))
                time.sleep(5)

    except(AttributeError) as err:
        logger.log_task_exception("TASK ERROR: While sending New Grad roles",err)
        return

@tasks.loop(hours=24)
async def send_summer_roles():
    # This function runs every 24 hours and sends summer roles
    logger.check_space()
    job_channel = client.get_channel(CHANNEL_1)
    df_posting = job_fetcher.latest_internship_postings()
    summer_color = 0xd1c171
    try:
        for i, row in df_posting.iterrows():
            
            data = row
            hash_id=data_accessor.create_id("internship",data)
            doc_exist = logger.update_postings_db(data,hash_id)

            if doc_exist is not None: data = doc_exist

            company = data_accessor.get_company_text(data)
            role = data_accessor.get_role(data)
            date_posted =data_accessor.get_date_posted(data)
            locations = data_accessor.get_locations(data)
            link = data_accessor.get_application_link(data)

            logger.log_posting(data,f"Posting Summer role for {company}: {role}")

            if logger.check_shared_status(hash_id): 
                logger.log_catch_duplicate(data,f"> {company}: {role} was already posted today.\n")
                continue
            else:
                embed=discord.Embed(description="Summer Internship", title=company, color=summer_color)
                embed.set_thumbnail(url=internship_icon)
                embed.add_field(name="Role", value=role, inline=True)
                embed.add_field(name="Date Posted", value=date_posted, inline=True)
                embed.add_field(name="Location", value=locations, inline=False)
                embed.add_field(name="Application Link", value=link, inline=False)
                embed.set_footer(text="Resume icons created by juicy_fish - Flaticon")
                try:
                    await job_channel.send(embed=embed)
                    logger.set_sucessful_shared_status(hash_id)

                except Exception as ex:
                    logger.set_failed_shared_status(hash_id)
                    logger.log_post_failure(data,f"Summer role {company} failed to send",str(ex))
                time.sleep(5)
    except(AttributeError) as err:
        logger.log_task_exception("TASK ERROR: While sending summer roles",err)
        return

@tasks.loop(hours=24)
async def send_offseason_roles():
    # This function runs every 24 hours and sends offseason roles
    logger.check_space()
    job_channel = client.get_channel(CHANNEL_1)
    df_posting = job_fetcher.latest_offseason_postings()
    offseason_color = 0x71b4d1

    try:
        for i, row in df_posting.iterrows():
            data = row
            hash_id=data_accessor.create_id("offseason",data)
            doc_exist = logger.update_postings_db(data,hash_id)

            if doc_exist is not None: data = doc_exist

            company = data_accessor.get_company_text(data)
            role = data_accessor.get_role(data)
            date_posted =data_accessor.get_date_posted(data)
            locations = data_accessor.get_locations(data)
            link = data_accessor.get_application_link(data)
            
            logger.log_posting(data,f"Posting Offseason role for {company}: {role}")

            if logger.check_shared_status(hash_id): 
                logger.log_catch_duplicate(data,f"> {company}: {role} was already posted today.\n")
                continue
            else:
                embed=discord.Embed(description="Offseason Internship", title=company, color=offseason_color)
                embed.set_thumbnail(url=offseason_icon)
                embed.add_field(name="Role", value=role, inline=True)
                embed.add_field(name="Date Posted", value=date_posted, inline=True)
                embed.add_field(name="Term(s)", value=data_accessor.get_terms(row), inline=False)
                embed.add_field(name="Location", value=locations, inline=False)
                embed.add_field(name="Application Link", value=link, inline=False)
                embed.set_footer(text="Resume icons created by juicy_fish - Flaticon")
                
                try:
                    await job_channel.send(embed=embed)
                    logger.set_sucessful_shared_status(hash_id)

                except Exception as ex:
                    logger.set_failed_shared_status(hash_id)
                    logger.log_post_failure(data,f"Offseason role {company} failed to send",str(ex))
                time.sleep(5)

    except(AttributeError) as err:
        logger.log_task_exception("TASK ERROR: While sending Offseason roles",err)
        return

# helper functions for jobspy scrape
# function to process NaN value for date_posted
def process_date_posted(date_value):
    if not date_value or str(date_value).lower() == "nan":
        return "N/A"
    return date_value

# creates embed message
def create_embed(job):
    embed = discord.Embed(
        title=job["title"],
        description=f"Posted by {job['company']}",
        color=0xc2f2cf
    )
    embed.set_thumbnail(url=canadian_job_img)
    embed.add_field(name="Location", value=job["location"], inline=True)
    embed.add_field(name="Date Posted", value=process_date_posted(job["date_posted"]), inline=True)
    embed.add_field(name="Job Post URL", value=f"[Click Here]({job['job_url']})", inline=False)
    # embed.set_footer(text="Powered by JobSpy")
    return embed

@tasks.loop(hours=24)
async def post_jobs_command():
    channel = client.get_channel(CANADIAN_CHANNEL)
    try:
        # await ctx.send("Starting job scraping...")
        await scrape_and_store(URI)
        logging.info("Starting jobspy scraping...")
        # await ctx.send("Job scraping completed and stored in MongoDB.")
    except Exception as e:
        logging.error(f"Error during job scraping: {e}")
        # await ctx.send(f"Error occurred during job scraping: {e}")

    try:
        jobs_to_post = fetch_unposted_jobs(URI)  # Fetch unposted jobs from MongoDB
        for job in jobs_to_post:
            embed = create_embed(job)
            try:
                await channel.send(embed=embed)  # Post job to Discord
                mark_as_posted(URI, job["_id"])  # Mark job as posted in MongoDB
                # logging.info(f"Posted job: {job['title']} at {job['company']}")
            except Exception as e:
                logging.error(f"Failed to post job: {job['title']}. Error: {e}")
        # await ctx.send("Jobs have been posted.")
    except Exception as e:
        logging.error(f"Error during job posting: {e}")
        # await ctx.send(f"Error occurred during job posting: {e}")


client.run(TOKEN) #runs the bot with the login token from the .env file

class JobPostingFetcher:

    def __init__(self,formatter,scraping_service,data_accessor):
        self.formatter = formatter
        self.scraping_service = scraping_service
        self.data_accessor = data_accessor

    def latest_internship_postings(self):
        # Set up dataframe
        data = self.scraping_service.get_github_internship2024()
        df_internships = self.formatter.readme_to_dataframe(data)
        df_internships = self.data_accessor.update_company_column(df_internships)

        # Get latest postings
        df_postings = self.data_accessor.get_reccent_postings(df_internships)
        return df_postings

    def latest_offseason_postings(self):
        # Set up dataframe
        data = self.scraping_service.get_github_offseason2024()
        df_offseason = self.formatter.readme_offseason_to_dataframe(data)
        df_offseason = self.data_accessor.update_company_column(df_offseason)
        
        # Get latest postings
        df_postings = self.data_accessor.get_reccent_postings(df_offseason)
        return df_postings

    def latest_newgrad_postings(self):
        # Set up dataframe
        data = self.scraping_service.get_github_newgrad2024()
        df_newgrad = self.formatter.readme_to_dataframe(data)
        df_newgrad = self.data_accessor.update_company_column(df_newgrad)
        
        # Get latest postings
        df_postings = self.data_accessor.get_reccent_postings(df_newgrad)
        return df_postings
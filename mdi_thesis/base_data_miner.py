"""
Data Miner

Author: Jacqueline Schmatz
Description: Pipeline for data collection.
"""

import time
import csv
import os
from pathlib import Path
from datetime import date, datetime
from typing import Union, List
from dateutil import relativedelta
import mdi_thesis.base.base as base
import mdi_thesis.base.utils as utils


class DataMinePipeline(base.Request):
    """
    Class for GitHub Request
    """
    def __init__(self, language: str, filter_date, repo_nr: int = 0,
                 get_existing_repos: bool = False,
                 repo_list: Union[List, None] = None) -> None:
        """
        :param language: Current programming language
        :param filter_date: Start date for filters in functions
        :param repo_num: Repo number to be queried.
        :param get_existing_repos: True if a file already exists
                                with repositories for the current language
        
        """
        super().__init__(filter_date)
        self.repo_list = repo_list
        self.repo_num = repo_nr
        self.language = language
        self.get_existing_repos = get_existing_repos
        self.query_parameters = ""
        self.query_functions = self.build_pipeline()
        self.search_to_json()
        self.base_data = {}

    def base_data_to_json(self):
        """
        Queries data to json file.
        """
        self.base_data = self.query_repository(
            ["repository",
             "contributors",
             "release",
             "community_health",
             "advisories"],
            filters={})
        for feature, data in self.base_data.items():
            utils.dict_to_json(data=data,
                               data_path=self.output_path,
                               feature=(self.language + "_" + feature))

    def forks_to_json(self,):
        """
        Queries data to json file.
        """
        forks = self.query_repository(["forks"],
                                      filters={},
                                      updated_at_filt=True
                                      )
        utils.dict_to_json(data=forks.get("forks"),
                           data_path=self.output_path,
                           feature=(self.language + "_" + "forks"))

    def pulls_issues_to_json(self):
        """
        Queries data to json file.
        """
        pulls_data = self.query_repository(
            ["pull_requests",
            "issue"],
            filters={
                "state": "all"})
        for feature, data in pulls_data.items():
            utils.dict_to_json(data=data,
                               data_path=self.output_path,
                               feature=(self.language + "_" + feature))  

    def commits_to_json(self):
        """
        Queries data to json file.
        """
        filter_date = self.filter_date - relativedelta.relativedelta(years=1)
        filter_date = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        commits = self.query_repository(
            ["commits"],
            filters={"since": filter_date})  # Check time filters for each metric
        for feature, data in commits.items():
            utils.dict_to_json(data=data,
                               data_path=self.output_path,
                               feature=(self.language + "_" + feature))

    def single_commits_to_json(self):
        """
        Queries data to json file.
        """
        filter_date = self.filter_date - relativedelta.relativedelta(months=6)
        filter_date_str = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        single_commits = self.get_single_object(
            feature="commits",
            filters={
                "since": filter_date_str
                }, output_format="dict")
        utils.dict_to_json(data=single_commits,
                           data_path=self.output_path,
                           feature=(self.language + "_single_commits"))

    def issue_comments_to_json(self):
        """
        Queries data to json file.
        :param obj: Already created base.Request() object
        :param language: Previous selected programming language for filename
        :param start_date: Start date when the code started running
                        For filtering the results consistently.
        """
        filter_date_issues = (self.filter_date -
                              relativedelta.relativedelta(months=6))
        filter_date_issues = filter_date_issues.strftime('%Y-%m-%dT%H:%M:%SZ')
        issue_comments = self.get_single_object(
            feature="issue_comments",
            filters={
                "since": filter_date_issues,
                "state": "all"
                },
                output_format="dict")
        utils.dict_to_json(data=issue_comments,
                           data_path=self.output_path,
                           feature=(self.language + "_issue_comments"))

    def upstream_dependencies_to_json(self):
        """
        Queries data to json file.
        """
        upstream_dependencies = self.get_dependencies()
        utils.dict_to_json(data=upstream_dependencies,
                           data_path=self.output_path,
                           feature=(self.language + "_upstream_dependencies"))

    def downstream_dependencies_to_json(self):
        """
        Queries data to json file.
        """

        downstream_dependencies = self.get_dependents(
            dependents_details=True)
        utils.dict_to_json(data=downstream_dependencies,
                           data_path=self.output_path,
                           feature=(self.language + "_downstream_dependencies"))

    def branches_to_json(self):
        """
        Queries data to json file.
        """
        # Stale branches
        stale_branches = self.get_branches(activity="stale")
        utils.dict_to_json(data=stale_branches,
                           data_path=self.output_path,
                           feature=(self.language + "_stale_branches"))

        time.sleep(300)

        # Active branches
        active_branches = self.get_branches(activity="active")
        utils.dict_to_json(data=active_branches,
                           data_path=self.output_path,
                           feature=(self.language + "_active_branches"))
        # All branches from API
        branches = self.get_single_object(
            feature="branches",
            filters={},
            output_format="dict"
            )
        utils.dict_to_json(data=branches,
                           data_path=self.output_path,
                           feature=(self.language + "_branches"))

    def contributors_to_json(self):
        """
        Queries data to json file.
        """
        base_data = self.query_repository(
            ["contributors"],
            filters={})
        users = {}
        repo_user_organizations = {}
        for ind, (repo, contributors) in enumerate(
                base_data.get("contributors").items()):
            contributor_list = []
            time.sleep(3)
            if ind % 100 == 0:
                self.logger.debug(
                    "Querying repo Nr. %s from %s at organization_users",
                    ind, len(base_data.get("contributors").items()))
                time.sleep(60)
            user_contributions = {}
            total_contributions = 0
            for user in contributors:
                contrib_num = user.get("contributions")
                total_contributions += contrib_num
                login = user.get("login")
                if login != "dependabot[bot]":
                    user_contributions[login] = contrib_num

            contributions_users = {
                k: v for k, v in sorted(user_contributions.items(),
                                        key=lambda item: item[1])}
            twenty_percent = len(contributions_users) * 0.2
            for ind, login in enumerate(contributions_users):
                contributor_list.append(login)
                if ind == twenty_percent:
                    break
                    
            contributor_list = list(user_contributions)
            users = self.query_repository(["organization_users"],
                                          repo_list=contributor_list,
                                          filters={})
            self.logger.debug(
                "Finished querying organization_users for repo %s",
                repo)
            repo_user_organizations[repo] = users.get("organization_users")

        utils.dict_to_json(data=repo_user_organizations,
                           data_path=self.output_path,
                           feature=(self.language + "_organization_users"))

        # Contributor_count
        contributor_count = utils.get_contributors(base_data.get(
            "contributors"),
            check_contrib=False)

        utils.dict_to_json(data=contributor_count,
                           data_path=self.output_path,
                           feature=(self.language + "_contributor_count"))
        contributor_count_checked = utils.get_contributors(base_data.get(
            "contributors"),
            check_contrib=True)

        utils.dict_to_json(data=contributor_count_checked,
                           data_path=self.output_path,
                           feature=(self.language +
                                    "_contributor_count_checked"))

    def contributors_org_to_json(self):
        """
        Get organizations for repository
        """
        repo_organizations = {}
        contributors_data = self.base_data.get("contributors")
        for repo, contributors in contributors_data.items():
            contrib_list = []
            for user in contributors:
                contrib_list.append(user.get("login"))
            users = self.query_repository(["organization_users"],
                                          repo_list=contrib_list,
                                          filters={})
            distinct_organizations = set()
            organization_users = users.get("organization_users")
            if organization_users:
                for user, data in organization_users.items():
                    for organization in data:
                        org_name = organization.get("login")
                        if org_name:
                            distinct_organizations.add(org_name)
                repo_organizations[repo] = len(distinct_organizations)
        utils.dict_to_json(data=repo_organizations,
                           data_path=self.output_path,
                           feature=(self.language + "_" + "repo_organizations")
                           )

    def search_to_json(self):
        """
        Runs through all functions for the current language
        and gathers data.
        """
        # GitHubSearchQuery
        search_query = ("&is:public&template:false&archived:false+" +
                        "pushed:>=2022-12-31&sort=stars&order=desc")

        if self.get_existing_repos:
            self.logger.info("Getting existing repos")
            curr_path = Path(os.path.dirname(__file__))
            filename = (self.language + "_repository.json")
            path = os.path.join(curr_path.parents[0],
                                "outputs", "data", filename)
            data = utils.json_to_dict(path=path)
            self.repo_list = list(data.keys())
        else:
            self.logger.info("Searching repos")
            self.query_parameters = "language:" + self.language + search_query
            self.select_repos(repo_nr=self.repo_num,
                              repo_list=self.repo_list,
                              query_parameters=self.query_parameters)
            self.logger.info("Finished getting repos for language %s",
                             self.language)

            for data_query in self.query_functions:
                self.logger.info("Starting function %s", data_query.__name__)
                repeat = True
                while repeat:
                    try:
                        data_query()
                        repeat = False
                        self.logger.info("Finished function %s successfully",
                                         data_query.__name__)
                        time.sleep(240)
                    except Exception as error:
                        self.logger.error("Error at function %s:%s \
                                    Retry in 10 minutes",
                                    data_query.__name__, error)
                        time.sleep(240)
                        repeat = True

    def build_pipeline(self):
        """
        Pipeline, passing all functions and runs for each language
        """

        query_functions = [
            self.base_data_to_json,
            self.forks_to_json,
            self.pulls_issues_to_json,
            self.commits_to_json,
            self.single_commits_to_json,
            self.issue_comments_to_json,
            self.upstream_dependencies_to_json,
            self.downstream_dependencies_to_json,
            self.branches_to_json,
            self.contributors_org_to_json,
            self.contributors_to_json
        ]
        return query_functions


def run_pipeline(start_date, languages, get_existing_repos, read_csv=""):
    """
    Run data collection pipeline.
    """
    date_file = open("start_date", "w", encoding="utf-8")
    date_file.write(str(start_date))
    date_file.close()

    repo_list = []
    if read_csv:
        raw_csv = open(read_csv, encoding="utf-8-sig")
        reader = csv.reader(raw_csv, delimiter=";")
        repos = list(reader)[1:]
        for row in repos:
            repo_identifier = str(row[0] + "/" + row[1])
            repo_list.append(repo_identifier)
        DataMinePipeline(language="csv",
                         filter_date=start_date,
                         repo_nr=1000,
                         get_existing_repos=get_existing_repos,
                         repo_list=repo_list)

    else:
        for language in languages:
            DataMinePipeline(language=language,
                             filter_date=start_date,
                             repo_nr=1000,
                             get_existing_repos=get_existing_repos,
                             repo_list=repo_list)


def main():
    """
    Setting parameters for pipeline here.
    """
    start_date = date.today()
    # start_date = date(2023, 8, 10)

    languages = ["python", "java", "php", "JavaScript", "cpp"]

    read_repository_json = False
    curr_path = Path(os.path.dirname(__file__))
    csv_path = os.path.join(curr_path.parents[0],
                            "outputs/data/small_sample.csv", )
    run_pipeline(start_date=start_date, languages=languages,
                 get_existing_repos=read_repository_json,
                 read_csv=csv_path)


if __name__ == "__main__":
    main()

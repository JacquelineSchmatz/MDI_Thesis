"""

"""

import logging
import time
import csv
import os
from pathlib import Path
import inspect
from typing import List
from datetime import date, datetime
from dateutil import relativedelta
import mdi_thesis.base.base as base
import mdi_thesis.base.utils as utils

logger = base.get_logger(__name__)
logger.setLevel(logging.DEBUG)


def select_data(repo_nr: int = 0,
                query_parameters: str = "",
                repo_list: List[int] = []
                ):
    """
    Creates initial object with selected repositories for
    further queries.
    :param repo_nr: Number of unique queried repositories
    :param query_parameters: If new repos are queried, a search string
                             has to be passed.
    :param repo_list: If already queried repositories are needed,
                      a list with the repo ids can be passed.
    :return:
    """
    # Create object
    selected_repos = base.Request()
    # Select repositories
    selected_repos.select_repos(
        repo_nr=repo_nr,
        query_parameters=query_parameters,
        repo_list=repo_list)
    return selected_repos


def base_data_to_json(obj:base.Request, language:str):
    """
    Queries data to json file.
    :param obj: Already created base.Request() object
    :param language: Previous selected programming language for filename
    """
    base_data = obj.query_repository(
        ["repository",
         "contributors",
         "release",
         "community_health",
         "advisories"],
         filters={})
    obj.logger.info("Finished querying base_data")
    for feature, data in base_data.items():
        utils.dict_to_json(data=data,
                           data_path=obj.output_path,
                           feature=(language + "_" + feature))
    obj.logger.info("Written %s to json.", base_data.keys())


def forks_to_json(obj:base.Request, language:str):
    """
    Queries data to json file.
    :param obj: Already created base.Request() object
    :param language: Previous selected programming language for filename
    """
    forks = obj.query_repository(["forks"],
                                 filters={},
                                 updated_at_filt=True
                                 )
    utils.dict_to_json(data=forks.get("forks"),
                       data_path=obj.output_path,
                       feature=(language + "_" + "forks"))
    obj.logger.info("Written forks to json.")


def pulls_issues_to_json(obj: base.Request, language: str):
    """
    Queries data to json file.
    :param obj: Already created base.Request() object
    :param language: Previous selected programming language for filename
    """
    pulls_data = obj.query_repository(
        ["pull_requests",
         "issue"],
         filters={
             "state": "all"})
    obj.logger.info("Finished querying pulls data.")
    for feature, data in pulls_data.items():
        utils.dict_to_json(data=data,
                           data_path=obj.output_path,
                           feature=(language + "_" + feature))
    obj.logger.info("Written pulls data to json.")    


def commits_to_json(obj:base.Request, language:str, start_date:date):
    """
    Queries data to json file.
    :param obj: Already created base.Request() object
    :param language: Previous selected programming language for filename
    :param start_date: Start date when the code started running
                       For filtering the results consistently.
    """
    filter_date = start_date - relativedelta.relativedelta(years=1)
    filter_date = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    commits = obj.query_repository(
        ["commits"],
        filters={"since": filter_date})  # Check time filters for each metric
    obj.logger.info("Finished querying commits data.")
    for feature, data in commits.items():
        utils.dict_to_json(data=data,
                           data_path=obj.output_path,
                           feature=(language + "_" + feature))
    obj.logger.info("Written commit data to json.")


def single_commits_to_json(obj:base.Request, language:str, start_date:date):
    """
    Queries data to json file.
    :param obj: Already created base.Request() object
    :param language: Previous selected programming language for filename
    :param start_date: Start date when the code started running
                       For filtering the results consistently.
    """
    filter_date = start_date - relativedelta.relativedelta(months=1)
    filter_date_str = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    single_commits = obj.get_single_object(
        feature="commits",
        filters={
            "since": filter_date_str
            }, output_format="dict")
    obj.logger.info("Finished querying commits for single_commits data.")
    utils.dict_to_json(data=single_commits,
                       data_path=obj.output_path,
                       feature=(language + "_single_commits"))
    obj.logger.info("Written single_commits data to json.")    


def issue_comments_to_json(obj:base.Request, language:str, start_date:date):
    """
    Queries data to json file.
    :param obj: Already created base.Request() object
    :param language: Previous selected programming language for filename
    :param start_date: Start date when the code started running
                       For filtering the results consistently.
    """
    filter_date_issues = (start_date -
                          relativedelta.relativedelta(months=6))
    filter_date_issues = filter_date_issues.strftime('%Y-%m-%dT%H:%M:%SZ')
    issue_comments = obj.get_single_object(
        feature="issue_comments",
        filters={
            "since": filter_date_issues,
            "state": "all"
            },
            output_format="dict")
    obj.logger.info("Finished querying issue_comments data.")
    utils.dict_to_json(data=issue_comments,
                       data_path=obj.output_path,
                       feature=(language + "_issue_comments"))
    obj.logger.info("Written issue_comments data to json.")


def upstream_dependencies_to_json(obj: base.Request, language: str):
    """
    Queries data to json file.
    :param obj: Already created base.Request() object
    :param language: Previous selected programming language for filename
    """
    upstream_dependencies = obj.get_dependencies()
    obj.logger.info("Finished querying upstream_dependencies data.")
    utils.dict_to_json(data=upstream_dependencies,
                       data_path=obj.output_path,
                       feature=(language + "_upstream_dependencies"))
    obj.logger.info("Written upstream_dependencies data to json.")


def downstream_dependencies_to_json(obj:base.Request, language:str):
    """
    Queries data to json file.
    :param obj: Already created base.Request() object
    :param language: Previous selected programming language for filename
    """
    downstream_dependencies = obj.get_dependents(
        dependents_details=True)
    obj.logger.info("Finished querying downstream_dependencies data.")
    utils.dict_to_json(data=downstream_dependencies,
                       data_path=obj.output_path,
                       feature=(language + "_downstream_dependencies"))
    obj.logger.info("Written downstream_dependencies data to json.")    


def branches_to_json(obj:base.Request, language:str):
    """
    Queries data to json file.
    :param obj: Already created base.Request() object
    :param language: Previous selected programming language for filename
    """
    stale_branches = obj.get_branches(activity="stale")
    obj.logger.info("Finished querying stale branches data.")
    utils.dict_to_json(data=stale_branches,
                       data_path=obj.output_path,
                       feature=(language + "_stale_branches"))
    obj.logger.info("Written stale_branches data to json.")
    time.sleep(300)
    # Active branches
    active_branches = obj.get_branches(activity="active")
    obj.logger.info("Finished querying active branches data.")
    utils.dict_to_json(data=active_branches,
                       data_path=obj.output_path,
                       feature=(language + "_active_branches"))
    obj.logger.info("Written active_branches data to json.")


def contributors_to_json(obj:base.Request, language:str):
    """
    Queries data to json file.
    :param obj: Already created base.Request() object
    :param language: Previous selected programming language for filename
    """
    base_data = obj.query_repository(
        ["contributors"],
         filters={})
    users = {}
    repo_user_organizations = {}
    for ind, (repo, contributors) in enumerate(
        base_data.get("contributors").items()):
        contributor_list = []
        time.sleep(3)
        if ind % 100 == 0:
            obj.logger.debug("Querying repo Nr. %s from %s at organization_users",
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
        users = obj.query_repository(["organization_users"],
                                     repo_list=contributor_list,
                                     filters={})
        obj.logger.debug("Finished querying organization_users for repo %s",
                         repo)
        repo_user_organizations[repo] = users.get("organization_users")

    obj.logger.info("Finished querying organization_users data.")
    utils.dict_to_json(data=repo_user_organizations,
                       data_path=obj.output_path,
                       feature=(language + "_organization_users"))
    obj.logger.info("Written organization_users data to json.")

    # Contributor_count
    contributor_count = utils.get_contributors(base_data.get(
        "contributors"),
        check_contrib=False)
    obj.logger.info("Finished querying contributors_count data.")
    utils.dict_to_json(data=contributor_count,
                       data_path=obj.output_path,
                       feature=(language + "_contributor_count"))
    contributor_count_checked = utils.get_contributors(base_data.get(
        "contributors"),
        check_contrib=True)
    obj.logger.info("Finished querying contributors_count data.")
    utils.dict_to_json(data=contributor_count_checked,
                       data_path=obj.output_path,
                       feature=(language + "_contributor_count_checked"))
    obj.logger.info("Written contributor_count data to json.")


def search_to_json(language: str,
                   start_date: date,
                   functions: List,
                   get_existing_repos: bool=False):
    """
    Runs through all functions for the current language
    and gathers data.
    :param language: Current programming language
    :param start_date: Start date for filters in functions
    :param functions: List with functions storing data to json
    :param get_existing_repos: True if a file already exists
                               with repositories for the current language
    """
    header = ["language", "repo_id", "repo_name",
              "repo_owner_login", "size",
              "stargazers_count", "watchers_count"]
    filter = "&is:public&template:false&archived:false+pushed:>=2022-12-31&sort=stars&order=desc" #GitHubSearchQuery
    csv_filename = language + "_repo_sample_large.csv"
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        query = "language:" + language + filter
        if get_existing_repos:
            curr_path = Path(os.path.dirname(__file__))
            filename = (language + "_repository.json")
            path = os.path.join(curr_path.parents[0],
                                "outputs", "data",filename)
            data = utils.json_to_dict(path=path)
            repo_list = list(data.keys())
            obj = select_data(repo_list=repo_list)
        else:
            obj = select_data(query_parameters=query, repo_nr=1000)
        print(f"Finished getting repos for language {language}")

        for data_query in functions:
            args = str(inspect.signature(data_query))
            repeat = True
            while repeat:
                try:
                    if "start_date" in args:
                        data_query(obj=obj,
                                   language=language,
                                   start_date=start_date)
                    else:
                        data_query(obj=obj, language=language)
                    repeat = False
                    time.sleep(240)
                except Exception as error:
                    logger.error("Error at function %s:%s \
                                 Retry in 10 minutes",
                                 data_query, error)
                    time.sleep(600)
                    repeat = True
            

def query_pipeline(start_date: date, languages: List):
    """
    Pipeline, passing all functions and runs for each language
    :param start_date: Start date from Pipeline for filters
                       in queries
    :param languages: List with the gathered programming languages
    """
    read_repository_json = True
    query_functions = [
        # base_data_to_json,
        # forks_to_json,
        # pulls_issues_to_json,
        # commits_to_json,
        # single_commits_to_json,
        # issue_comments_to_json,
        # upstream_dependencies_to_json,
        downstream_dependencies_to_json,
        # branches_to_json
            # ,
        # contributors_to_json
    ]

    for lang in languages:
        logger.info("Starting language %s at %s", lang,
                    datetime.now())
        logger.debug("Getting repos with language: %s", lang)

        search_to_json(language=lang,
                       start_date=start_date,
                       functions=query_functions,
                       get_existing_repos=read_repository_json)

        logger.info("Finished languages %s at %s", lang,
                    datetime.now())
        time.sleep(240)


def main():
    start_time = datetime.now()
    f = open("start_time", "a")
    f.write(str(start_time))
    f.close()
    logger.info("Starting process at %s", start_time)

    # start_date = date.today()
    start_date = date(2023, 8, 10)

    # languages = ["python", "java", "php", "JavaScript", "cpp"]
    languages = ["python", "JavaScript"]
    # languages = ["php"]
    # languages = ["python"]

    query_pipeline(start_date=start_date, languages=languages)

    logger.info("Finished process at %s", datetime.now())


if __name__ == "__main__":
    main()

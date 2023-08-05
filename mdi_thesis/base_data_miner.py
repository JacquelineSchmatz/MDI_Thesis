"""

"""

import logging
import time
import csv
import os
from typing import List
from dateutil import relativedelta
from datetime import date, datetime
import mdi_thesis.base.base as base
import mdi_thesis.base.utils as utils

logger = base.get_logger(__name__)
logger.setLevel(logging.DEBUG)


def select_data(repo_nr: int = 0,
                path: str = "",
                query_parameters: str = "",
                repo_list: List[int] = []
                ):
    """
    :param path:
    :return:
    """
    selected_repos = base.Request()
    if path:
        # Statement for selecting repositories according to list
        repo_ids = utils.__get_ids_from_txt__(path=path)
        selected_repos.select_repos(repo_list=repo_ids, repo_nr=repo_nr)
    else:
        # Statement for selecting number of queried repositories
        selected_repos.select_repos(
            repo_nr=repo_nr,
            query_parameters=query_parameters,
            repo_list=repo_list)
    return selected_repos


def results_to_json(obj, language, start_date):
    """
    Queries data from already selected repositories
    and stores them in json files.
    """
    # General base data
    base_data = obj.query_repository(["repository",
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
    time.sleep(300)
    # Forks
    forks = obj.query_repository(["forks"],
                                 filters={},
                                 updated_at_filt=True
    )
    utils.dict_to_json(data=forks,
                       data_path=obj.output_path,
                       feature=(language + "_" + "forks"))
    obj.logger.info("Written forks to json.")
    time.sleep(300)

    # Pull Requests and Issues
    # Check state requirements for each metric
    pulls_data = obj.query_repository(["pull_requests",
                                       "issue"],
                                       filters={
                                           "state": "all"})
    obj.logger.info("Finished querying pulls data.")
    for feature, data in pulls_data.items():
        utils.dict_to_json(data=data,
                           data_path=obj.output_path,
                           feature=(language + "_" + feature))
    obj.logger.info("Written pulls data to json.")
    time.sleep(300)
    # Commits
    filter_date = start_date - relativedelta.relativedelta(years=1)
    filter_date = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    commits = obj.query_repository(["commits"],
                                   filters={"since": filter_date})  # Check time filters for each metric
    obj.logger.info("Finished querying commits data.")
    for feature, data in commits.items():
        utils.dict_to_json(data=data,
                           data_path=obj.output_path,
                           feature=(language + "_" + feature))
    obj.logger.info("Written commit data to json.")
    time.sleep(300)
    # Single commits
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
    time.sleep(300)
    # Issue comments
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
    time.sleep(300)
    # Dependencies Upstream
    upstream_dependencies = obj.get_dependencies()
    obj.logger.info("Finished querying upstream_dependencies data.")
    utils.dict_to_json(data=upstream_dependencies,
                        data_path=obj.output_path,
                        feature=(language + "_upstream_dependencies"))
    obj.logger.info("Written upstream_dependencies data to json.")
    time.sleep(300)
    # Dependencies Downstream
    downstream_dependencies = obj.get_dependents(
        dependents_details=False)
    obj.logger.info("Finished querying downstream_dependencies data.")
    utils.dict_to_json(data=downstream_dependencies,
                       data_path=obj.output_path,
                       feature=(language + "_downstream_dependencies"))
    obj.logger.info("Written downstream_dependencies data to json.")
    time.sleep(300)
    # Stale branches
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
    time.sleep(300)
    # Contributor's organizations
    users = {}
    for contributors in base_data.get("contributors").values():
        user_contributions = {}
        for user in contributors:
            login = user.get("login")
            if login != "dependabot[bot]":
                contributions = user.get("contributions")
                user_contributions[login] = contributions
        contributor_list = list(user_contributions)
        users = obj.query_repository(["organization_users"],
                                     repo_list=contributor_list,
                                     filters={})
    obj.logger.info("Finished querying organization_users data.")
    utils.dict_to_json(data=users.get("organization_users"),
                       data_path=obj.output_path,
                       feature=(language + "_organization_users"))
    obj.logger.info("Written organization_users data to json.")
    time.sleep(300)
    # Contributors
    contributor_count = utils.get_contributors(base_data.get(
        "contributors"),
        check_contrib=False)
    obj.logger.info("Finished querying contributors_count data.")
    utils.dict_to_json(data=contributor_count,
                       data_path=self.output_path,
                       feature=(language + "_contributor_count"))
    obj.logger.info("Written contributor_count data to json.")


def search_to_json(language, start_date, get_existing_repos=False):
    """
    
    """
    header = ["language", "repo_id", "repo_name",
              "repo_owner_login", "size",
              "stargazers_count", "watchers_count"]
    # filter = "&sort=stars&order=desc&is:public&template:false&archived:false&pushed:>=2022-12-31"
    filter = "&is:public&template:false&archived:false+pushed:>=2022-12-31&sort=stars&order=desc"
    # TODO: RECONSIDER TIME FILTER FOR REPOSITORIES!!!!!!!!!!!!!
    # filter = "&sort=stars&order=desc"

    with open('repo_sample_large.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        query = "language:" + language + filter
        if get_existing_repos:
            path = os.path.join(language, "_repository")
            data = utils.json_to_dict(path=path)
            repo_list = list(data.keys())
            obj = select_data(repo_list=repo_list)
        else:
            obj = select_data(query_parameters=query, repo_nr=1000)
        print(f"Finished getting results for language {language}")
        results_to_json(obj=obj, language=language, start_date=start_date)
        # repos = obj.query_repository(["repository"], filters={})
        # for repo, data in repos.get("repository").items():
        #     try:
        #         language = data.get("language")
        #         name = data.get("name")
        #         owner = data.get("owner").get("login")
        #         size = data.get("size")
        #         stargazers_count = data.get("stargazers_count")
        #         watchers_count = data.get("watchers_count")
        #         row = [language, repo, name, owner, size, stargazers_count, watchers_count]
        #     except AttributeError:
        #         logger.debug(f"Could not query repo {repo}")
        #         row = f"Could not query repo {repo}"
        #     writer.writerow(row)


def main():
    print(datetime.now())
    logger.info("Starting process at %s", datetime.now())
    start_date = date.today()
    languages = ["python", "java", "php", "JavaScript", "cpp"]
    # languages = ["java", "php", "JavaScript", "cpp"]
    # languages = ["python"]
    for lang in languages:
        logger.info("Starting languages %s at %s", lang,
                    datetime.now())
        logger.debug("Getting repos with language: %s", lang)
        search_to_json(lang, start_date)
        logger.info("Finished languages %s at %s", lang,
            datetime.now())
        time.sleep(240)
    print(datetime.now())
    logger.info("Finished process at %s", datetime.now())

if __name__ == "__main__":
    main()

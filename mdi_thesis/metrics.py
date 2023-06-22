"""
Module for metric calculations.
"""
import logging
import time
from datetime import date, datetime
from dateutil import relativedelta
from typing import Dict, List, Any

import mdi_thesis.base.base as base
import mdi_thesis.base.utils as utils
import mdi_thesis.external as external

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s %(name)-12s %(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def select_data(repo_nr: int = 0,
                path: str = "",
                order: str = "desc"
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
            order=order,
            repo_list=[])
    return selected_repos


def maturity_level(data_object) -> Dict[int, int]:
    """
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Repositories with corresponding results.
    """
    base_data = data_object.query_repository(["repository"], filters={})
    today = date.today()
    repo_data = base_data.get("repository")
    age_score = utils.get_repo_age_score(repo_data=repo_data)
    filter_issues = today - relativedelta.relativedelta(months=6)
    filter_issues = filter_issues.strftime('%Y-%m-%dT%H:%M:%SZ')
    filter_issues = {"since": filter_issues}
    issue_data = data_object.query_repository(["issue"], filters=filter_issues)
    issue_score = utils.get_repo_issue_score(issue_data)
    filter_release = today - relativedelta.relativedelta(months=12)
    filter_release = filter_release.strftime('%Y-%m-%dT%H:%M:%SZ')
    filter_release = {"since": filter_release}
    release_data = data_object.query_repository(
        ["release"], filters=filter_release)
    release_score = utils.get_repo_release_score(release_data)
    repo_metric_dict = {}
    for repo, score in age_score.items():
        score_sum = score + issue_score[repo] + release_score[repo]
        result = int(score_sum/3 * 100)
        repo_metric_dict[repo] = result
    return repo_metric_dict


def osi_approved_license(data_object) -> Dict[int, bool]:
    """
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Repositories with corresponding results.
    """
    base_data = data_object.query_repository(["repository"], filters={})
    osi_licenses = external.get_osi_json()
    results = {}
    for repo, data in base_data.get("repository").items():
        license_info = data[0].get("license")
        if not license_info:
            results[repo] = False
        else:
            spdx_id = license_info.get("spdx_id").strip()
            for osi_license in osi_licenses:
                id = osi_license.get("licenseId").strip()
                if spdx_id == id:
                    osi_approved = osi_license.get("isOsiApproved")
                    results[repo] = osi_approved
    return results


def technical_fork():
    """
    Technical Fork left out due to too much calculation costs. 
    May reconsider different metric instead.
    """
    pass


def criticality_score(data_object):
    """
    IN PROGRESS!!!!!!!!!!!!!
    """
    today = datetime.today()
    age_in_months = {}
    filter_date = date.today() - relativedelta.relativedelta(years=1)
    filter_date = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    # base_data = data_object.query_repository(["repository",
    #                                           "contributors"],
    #                                          filters={})
    # for repo, data in base_data.get("repository").items():
    #     created_at = data[0].get("created_at")
    #     created_at = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
    #     updated_at = data[0].get("updated_at")
    #     updated_at = datetime.strptime(updated_at, '%Y-%m-%dT%H:%M:%SZ')
    #     dates = relativedelta.relativedelta(today, created_at)
    #     months = dates.months + (dates.years*12)
    #     age_in_months[repo] = months
    #     diff_updated_today = relativedelta.relativedelta(today, updated_at)
    #     diff_updated_today = diff_updated_today.months + (
    #         diff_updated_today.years*12)
        
        # print(f"Updated since: {diff_updated_today}")
    # repo_contributions = utils.get_contributors(base_data.get("contributors"))
    # repo_organizations = utils.get_organizations(
    #     contributors_data=base_data.get("contributors"),
    #     data_object=data_object)
    # print(repo_organizations)

    base_data = data_object.query_repository(["commits", "release"],
                                             filters={"since": filter_date})
    repo_commits = {}
    for repo, data in base_data.get("commits").items():
        repo_commit_dates = []
        for commit in data:
            commit_date = commit.get("commit").get("author").get("date")
            commit_date = datetime.strptime(commit_date, '%Y-%m-%dT%H:%M:%SZ')
            repo_commit_dates.append(commit_date)
        # repo_commits[repo] = repo_commit_dates

        if repo_commit_dates:
            # Sort the datetime list
            repo_commit_dates.sort()
            earliest_date = repo_commit_dates[0].date()
            latest_date = repo_commit_dates[-1].date()
            num_weeks = (latest_date - earliest_date).days // 7 + 1
            # Count the number of elements per week
            elements_per_week = [0] * num_weeks
            for commit_datetime in repo_commit_dates:
                week_index = (commit_datetime.date() - earliest_date).days // 7
                elements_per_week[week_index] += 1
            average_per_week = sum(elements_per_week) / num_weeks
            repo_commits[repo] = average_per_week
        else:
            repo_commits[repo] = []
    
    releases_per_repo = {}
    for repo, data in base_data.get("release").items():
        release_list = []
        print(repo)
        for release in data:
            published_at = release.get("published_at")
            published_at = datetime.strptime(
                published_at, '%Y-%m-%dT%H:%M:%SZ')
            dates = relativedelta.relativedelta(today, published_at)
            if dates.years == 0:
                release_list.append(published_at)
        num_releases = len(release_list)
        releases_per_repo[repo] = num_releases
    # print(repo_commits)
    # print(releases_per_repo)
    # print("Average number of elements per week:", average_per_week)
    # print(age_in_months)




def pull_requests():
    pass


def project_velocity():
    pass


def github_community_health_percentage():
    pass


def issues():
    pass


def support_rate():
    pass


def upstream_code_dependency():
    pass


def branch_patch_ratio():
    pass


def bus_factor():
    pass


def pareto_principle():
    pass


def contributors_per_file():
    pass


def number_of_support_contributors():
    pass


def elephant_factor():
    pass


def size_of_community():
    pass


def churn():
    pass


def branch_lifecycle():
    pass


def main():
    """
    Main in progress
    """
    repo_ids_path = "mdi_thesis/preselected_repos.txt"

    # selected_repos.select_repos(repo_list=repo_ids)
    obj = select_data(path=repo_ids_path)
    # obj = select_data(repo_nr=1, order="desc")
    print(obj)
    # print(maturity_level(obj))
    # print(osi_approved_license(obj))
    # print(obj.selected_repos_dict)
    print(criticality_score(obj))

    # print(selected_repos.get_single_object(feature="commits"))
    # print(selected_repos.query_repository(["advisories"]))
    # print(selected_repos.query_repository(["commits"]))
    # print(selected_repos.get_context_information(main_feature="contributors", sub_feature="users"))
    # .get("community_health")  # .get(191113739))
    # print(len(selected_repos.query_repository(["contributors"])))
    # .get("community_health")  # .get(191113739)))


if __name__ == "__main__":
    main()
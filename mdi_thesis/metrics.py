"""
Module for metric calculations.
"""
import timeit
import json
import logging
from datetime import date, datetime
# import time
import numpy as np
from typing import Dict  # , List, Any
from dateutil import relativedelta

import mdi_thesis.base.base as base
import mdi_thesis.base.utils as utils
import mdi_thesis.external as external

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s %(name)-12s %(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.ERROR)




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
        result = round(score_sum/3 * 100)
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


def technical_fork(data_object):
    """
    Use number of forks as raw number from repository information!
    """
    pass


def criticality_score(data_object) -> Dict[int, float]:
    """
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: criticality_score per repository.
    """

    scores_per_repo = {}
    today = datetime.today()
    base_data = data_object.query_repository(["repository",
                                              "contributors",
                                              "release"],
                                             filters={})

    # created_since, updated_since
    logger.info("Getting created_since and updated_since...")
    for repo, data in base_data.get("repository").items():
        created_at = data[0].get("created_at")
        created_at = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
        updated_at = data[0].get("updated_at")
        updated_at = datetime.strptime(updated_at, '%Y-%m-%dT%H:%M:%SZ')
        dates = relativedelta.relativedelta(today, created_at)
        months = dates.months + (dates.years*12)
        diff_updated_today = relativedelta.relativedelta(today, updated_at)
        diff_updated_today = diff_updated_today.months + (
            diff_updated_today.years*12)
        scores_per_repo[repo] = {"created_since": months,
                                 "updated_since": diff_updated_today}
    logger.info("Getting contributor_count...")
    # contributor_count
    contributor_count = utils.get_contributors(base_data.get("contributors"))
    for repo, cont_count in contributor_count.items():
        scores_per_repo[repo].update({"contributor_count": cont_count})
    logger.info("Getting org_count...")
    # org_count
    org_count = utils.get_organizations(
        contributors_data=base_data.get("contributors"),
        data_object=data_object)
    for repo, org_count in org_count.items():
        scores_per_repo[repo].update({"org_count": org_count})

    # commit_frequency
    logger.info("Getting commit_frequency...")
    filter_date = date.today() - relativedelta.relativedelta(years=1)
    filter_date = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    commits = data_object.query_repository(["commits"],
                                           filters={"since": filter_date})
    for repo, data in commits.get("commits").items():
        repo_commit_dates = []
        for commit in data:
            try:
                commit_date = commit.get("commit").get("author").get("date")
                commit_date = datetime.strptime(
                    commit_date, '%Y-%m-%dT%H:%M:%SZ')
                repo_commit_dates.append(commit_date)
            except Exception as key_error:
                logger.debug(key_error)
                continue
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
            average_per_week = np.mean(elements_per_week)  # sum(elements_per_week) / num_weeks

        else:
            average_per_week = 0
            # commit_frequency[repo] = []
        scores_per_repo[repo].update({"commit_frequency": average_per_week})

    # recent_releases_count
    logger.info("Getting recent_releases_count...")
    for repo, data in base_data.get("release").items():
        release_list = []
        for release in data:
            published_at = release.get("published_at")
            published_at = datetime.strptime(
                published_at, '%Y-%m-%dT%H:%M:%SZ')
            dates = relativedelta.relativedelta(today, published_at)
            if dates.years == 0:
                release_list.append(published_at)
        num_releases = len(release_list)
        scores_per_repo[repo].update({"recent_releases_count": num_releases})

    # closed_issues_count & updated_issues_count
    logger.info("Getting closed_issues_count and updated_issues_count...")
    filter_date_issues = date.today() - relativedelta.relativedelta(days=90)
    filter_date_issues = filter_date_issues.strftime('%Y-%m-%dT%H:%M:%SZ')
    issues = data_object.query_repository(
        ["issue"],
        filters={
            "since": filter_date_issues,
            "state": "all"
            })
    for repo, data in issues.get("issue").items():
        closed_issues = 0
        updated_issues = 0
        for issue in data:
            closed_at = issue.get("closed_at")
            updated_at = issue.get("updated_at")
            if closed_at:
                closed_date = datetime.strptime(closed_at,
                                                '%Y-%m-%dT%H:%M:%SZ')
                closed_diff = today - closed_date
                if closed_diff.days <= 90:
                    closed_issues += 1
            if updated_at:
                updated_date = datetime.strptime(updated_at,
                                                 '%Y-%m-%dT%H:%M:%SZ')
                updated_diff = today - updated_date
                if updated_diff.days <= 90:
                    updated_issues += 1
        scores_per_repo[repo].update({"closed_issues_count": closed_issues,
                                      "updated_issues_count": updated_issues})
    # comment_frequency
    logger.info("Getting comment_frequency...")
    issue_comments = data_object.get_single_object(
        feature="issue_comments",
        filters={
            "since": filter_date_issues,
            "state": "all"
            },
        output_format="list")
    for repo, data in issue_comments.items():
        comment_count_list = []
        for issue in data:
            for comments in issue.values():
                comment_count = len(comments)
                comment_count_list.append(comment_count)
        if comment_count_list:
            avg_comment_count = round(np.mean(comment_count_list), 0)
        else:
            avg_comment_count = 0
        scores_per_repo[repo].update({"comment_frequency": avg_comment_count})
    # dependents_count
    logger.info("Getting dependents_count...")
    dependents_count = data_object.get_dependents()
    for repo, dep_count in dependents_count.items():
        scores_per_repo[repo].update({"dependents_count": dep_count})

    criticality_score_per_repo = {}
    weights_json = open(
        "mdi_thesis\criticality_score_weights.json",
        encoding="utf-8")
    weights = json.load(weights_json)
    weight_sum = 0
    for elements in weights.values():
        weight = elements.get("weight")
        weight_sum += weight

    for repo, param in scores_per_repo.items():
        form_1 = 1/weight_sum
        sum_alpha = 0
        for param_name, value in param.items():
            log_1 = np.log(1 + value)
            max_threshold = weights.get(param_name).get("max_threshold")
            log_2 = np.log(1 + max(value, max_threshold))
            if log_2 == 0:
                res_fraction = 1
            else:
                res_fraction = log_1/log_2
            weight = weights.get(param_name).get("weight")
            res_1 = weight*res_fraction
            sum_alpha += res_1
        res_2 = round((form_1*sum_alpha), 2)
        criticality_score_per_repo[repo] = res_2
    return criticality_score_per_repo


def pull_requests(data_object) -> Dict[int, Dict[str, float]]:
    """
    Contains information about:
    - Total number of pulls
    - Average closing time (Difference of creation and close date)
    - Ratio per state (open, closed and merged)
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Parameter names and values
    """
    pulls_data = data_object.query_repository(["pull_requests"],
                                              filters={"state": "all"})
    pull_results = {}
    for repo, data in pulls_data.get("pull_requests").items():
        state_open = 0
        state_closed = 0
        pulls_merged = 0
        total_pulls = len(data)
        date_diffs = []
        for pull in data:
            state = pull.get("state")
            closed_at = pull.get("closed_at")
            created_at = pull.get("created_at")
            merged_at = pull.get("merged_at")
            created_at = datetime.strptime(created_at,
                                           '%Y-%m-%dT%H:%M:%SZ')
            if closed_at:
                closed_at = datetime.strptime(closed_at,
                                              '%Y-%m-%dT%H:%M:%SZ')
            if merged_at:
                merged_at = datetime.strptime(merged_at,
                                              '%Y-%m-%dT%H:%M:%SZ')
                pulls_merged += 1
                if closed_at:
                    if closed_at == merged_at:
                        date_diff = closed_at - created_at
                        date_diffs.append(date_diff.days)
            if state == "open":
                state_open += 1
            elif state == "closed":
                state_closed += 1
        avg_date_diff = round(np.mean(date_diffs))
        ratio_open = round((state_open / total_pulls), 2)
        ratio_closed = round((state_closed / total_pulls), 2)
        ratio_merged = round((pulls_merged / total_pulls), 2)
        pull_results[repo] = {"total_pulls": total_pulls,
                              "avg_pull_closed_days": avg_date_diff,
                              "ratio_open_total": ratio_open,
                              "ratio_closed_total": ratio_closed,
                              "ratio_merged_total": ratio_merged}

    return pull_results


def project_velocity(data_object) -> Dict[int, Dict[str, float]]:
    """
    Calculates information about a projects velocity concerning
    issues and their resolving time. Issues also include pulls,
    bc. all pulls are issues, but not issues are pulls
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Values for each information including the
    total number of issues, the average issue resolving time in days,
    the ratio of open and closed issues to total issues and
    information about the number of pulls.
    """
    velocity_results = {}
    issues_pulls = data_object.query_repository(
        ["issue"],
        filters={"state": "all"})
    for repo, data in issues_pulls.get("issue").items():
        closed_issues = 0
        open_issues = 0
        total_issues = len(data)
        date_diffs = []
        pull_issue_list = []
        for issue in data:
            pull_request_id = issue.get("pull_request")
            is_pull_request = bool(pull_request_id)
            pull_issue_list.append(is_pull_request)
            state = issue.get("state")
            created_at = issue.get("created_at")
            created_at = datetime.strptime(created_at,
                                           '%Y-%m-%dT%H:%M:%SZ')
            if state == "open":
                open_issues += 1
            if state == "closed":
                closed_issues += 1
                closed_at = issue.get("closed_at")
                if closed_at:
                    closed_at = datetime.strptime(closed_at,
                                                  '%Y-%m-%dT%H:%M:%SZ')
                date_diff = closed_at - created_at
                date_diffs.append(date_diff.days)
        pull_count = pull_issue_list.count(True)
        no_pull_count = pull_issue_list.count(False)
        avg_date_diff = round(np.mean(date_diffs))
        ratio_open = round((open_issues / total_issues), 2)
        ratio_closed = round((closed_issues / total_issues), 2)
        ratio_pull_issue = round((pull_count / total_issues), 2)
        velocity_results[repo] = {"total_issues": total_issues,
                                  "pull_count": pull_count,
                                  "no_pull_count": no_pull_count,
                                  "ratio_pull_issue": ratio_pull_issue,
                                  "avg_issue_resolving_days": avg_date_diff,
                                  "ratio_open_total": ratio_open,
                                  "ratio_closed_total": ratio_closed}
    return velocity_results


def github_community_health_percentage(data_object):
    """
    Retrieves information about the GitHub community health percentage metric.
    As the formula introduced by GitHub is questionable, potential relevant
    information is summarized by indicating,
    if it is available (True) or not (False).
    This is implied by the outdated formula,
    referring to the existence of certain files
    (readme, contributing, license, code of conduct).
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Scores and potentially relevant information
    """
    community_health_info = {}
    community_health = data_object.query_repository(
        ["community_health"],
        filters={})
    for repo, data in community_health.get("community_health").items():
        data = data[0]
        score = data.get("health_percentage")
        description = bool(data.get("description"))
        documentation = bool(data.get("documentation"))
        code_of_conduct = bool(data.get("files").get("code_of_conduct"))
        contributing = bool(data.get("files").get("contributing"))
        issue_template = bool(data.get("files").get("issue_template"))
        pull_request_template = bool(
            data.get("files").get("pull_request_template"))
        license_bool = bool(data.get("files").get("license"))
        readme = bool(data.get("files").get("readme"))
        info_list = [description, documentation, code_of_conduct,
                     contributing, issue_template, pull_request_template,
                     license_bool, readme]
        true_count = info_list.count(True)
        false_count = info_list.count(False)
        infos = {"community_health_score": score,
                 "true_count": true_count,
                 "false_count": false_count,
                 "description": description,
                 "documentation": documentation,
                 "code_of_conduct": code_of_conduct,
                 "contributing": contributing,
                 "issue_template": issue_template,
                 "pull_request_template": pull_request_template,
                 "license": license_bool,
                 "readme": readme}
        community_health_info[repo] = infos
    return community_health_info


def issues(data_object) -> Dict[int, Dict[str, float]]:
    """
    Returns information about issues, excluding pulls.
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Selected information about a repositories issue activities
    """
    issues_infos = {}
    filter_date_issues = date.today() - relativedelta.relativedelta(days=90)
    filter_date_issues = filter_date_issues.strftime('%Y-%m-%dT%H:%M:%SZ')
    all_issues = data_object.query_repository(
        ["issue"],
        filters={"since": filter_date_issues,
                 "state": "all"})

    issue_comments = data_object.get_single_object(
        feature="issue_comments",
        filters={
            "since": filter_date_issues,
            "state": "all"
            },
        output_format="dict")
    for repo, data in all_issues.get("issue").items():
        closed_issues = 0
        open_issues = 0
        total_issues = 0
        issue_close_times = []
        issue_first_response_times = []
        issue_creation_times = []
        comment_count_list = []
        for issue in data:
            pull_request_id = issue.get("pull_request")
            is_pull_request = bool(pull_request_id)
            if not is_pull_request:
                total_issues += 1
                state = issue.get("state")
                issue_created_at = issue.get("created_at")
                issue_created_at = datetime.strptime(issue_created_at,
                                                     '%Y-%m-%dT%H:%M:%SZ')
                issue_creation_times.append(issue_created_at)
                issue_number = issue.get("number")
                try:
                    total_comments = len(issue_comments.get(
                        repo).get(issue_number))
                    comment_count_list.append(total_comments)
                    first_comment_date = issue_comments.get(
                        repo).get(issue_number)[0].get("created_at")
                    if first_comment_date:
                        first_comment_date = datetime.strptime(
                            first_comment_date,
                            '%Y-%m-%dT%H:%M:%SZ')
                        first_response_time = (first_comment_date -
                                               issue_created_at)
                        first_response_time = first_response_time.days
                        issue_first_response_times.append(first_response_time)
                    else:
                        first_response_time = None
                except KeyError:
                    continue
                except IndexError:
                    continue
                # Count states
                if state == "open":
                    open_issues += 1
                if state == "closed":
                    closed_issues += 1
                    closed_at = issue.get("closed_at")
                    if closed_at:
                        closed_at = datetime.strptime(closed_at,
                                                      '%Y-%m-%dT%H:%M:%SZ')
                    date_diff = closed_at - issue_created_at
                    issue_close_times.append(date_diff.days)

        if issue_creation_times:
            # Sort the datetime list
            issue_creation_times.sort()
            earliest_date = issue_creation_times[0].date()
            latest_date = issue_creation_times[-1].date()
            num_weeks = (latest_date - earliest_date).days // 7 + 1
            # Count the number of elements per week
            elements_per_week = [0] * num_weeks
            for issue_datetime in issue_creation_times:
                week_index = (issue_datetime.date() - earliest_date).days // 7
                elements_per_week[week_index] += 1
            average_per_week = round(np.mean(elements_per_week))  # sum(elements_per_week) / num_weeks
        else:
            average_per_week = 0

        if issue_close_times:
            avg_date_diff = round(np.mean(issue_close_times))
        else:
            avg_date_diff = None
        if issue_first_response_times:
            avg_first_response_time_days = round(np.mean(
                issue_first_response_times))
        else:
            avg_first_response_time_days = None
        if comment_count_list:
            avg_issue_comments = round(np.mean(comment_count_list))
        else:
            avg_issue_comments = None
        if total_issues:
            ratio_open = round((open_issues / total_issues), 2)
            ratio_closed = round((closed_issues / total_issues), 2)
        else:
            ratio_open = None
            ratio_closed = None
        issues_infos[repo] = {"total_issues": total_issues,
                              "open_issues": open_issues,
                              "closed_issues": closed_issues,
                              "average_issue_created_per_week":
                              average_per_week,
                              "avg_issue_comments": avg_issue_comments,
                              "avg_issue_resolving_days": avg_date_diff,
                              "avg_first_response_time_days":
                              avg_first_response_time_days,
                              "ratio_open_total": ratio_open,
                              "ratio_closed_total": ratio_closed}

    return issues_infos


def support_rate():
    pass


def upstream_code_dependency(data_object):
    # Dependencies via Dependency Graph
    dependencies_1 = data_object.get_dependencies()
    print(dependencies_1)
    # print(base_data)
    # Dependencies via Content files (requirements.txt or setup.py)
    dependency_data = data_object.get_dependency_packages()
    dependency_count = {}
    for repo, dependencies in dependency_data.items():
        dependency_count[repo] = len(dependencies)
    print(dependency_count)

# Dependency Graph vs. content files
# {191113739: 0 - 191113739: 0
# 307260205: 24 - 307260205: 6
# 101138315: 5 - 101138315: 5
# 537603333: 12 - 537603333: 6
# 34757182: 2 - 34757182: 2
# 84533158: 14 - 84533158: 0
# 573819845: 22 - 573819845: 6
# 222751131: 6 - 222751131: 0
# 45723377: 0 - 45723377: 0
# 2909429: 583 - 2909429: 6
# 74073233: 23 - 74073233: 0
# 80990461: 9 - 80990461: 9
# 138331573: 1 - 138331573: 0
# 41654081: 0 - 41654081: 0
# 8162715: 1139 - 8162715: 162
# 152166877: 11 - 152166877: 6
# 59720190: 35 - 59720190: 11
# 253601257: 13 - 253601257: 7
# 221723816: 112 - 221723816: 0
# 143328315: 308 - 143328315: 0
# 7053637: 39 - 7053637: 4
# 10332822: 3 - 10332822: 0
# 65593050: 3 - 65593050: 3
# 36895421: 18 - 36895421: 8
# 143460965: 944 - 143460965: 0
# 189840: 28 - 189840: 3
# 617798408: 189 - 617798408: 0


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
    start = timeit.timeit()
    repo_ids_path = "mdi_thesis/preselected_repos.txt"

    # selected_repos.select_repos(repo_list=repo_ids)
    obj = select_data(path=repo_ids_path)
    # obj = select_data(repo_nr=1, order="desc")
    print(obj)
    # print(maturity_level(obj))
    # print(osi_approved_license(obj))
    # print(obj.selected_repos_dict)
    # print(criticality_score(obj))
    # print(pull_requests(obj))
    # print(project_velocity(obj))
    # print(github_community_health_percentage(obj))
    print(issues(obj))
    end = timeit.timeit()
    print(end - start)
    # print(selected_repos.get_single_object(feature="commits"))
    # print(selected_repos.query_repository(["advisories"]))
    # print(selected_repos.query_repository(["commits"]))
    # print(selected_repos.get_context_information(main_feature="contributors", sub_feature="users"))
    # .get("community_health")  # .get(191113739))
    # print(len(selected_repos.query_repository(["contributors"])))
    # .get("community_health")  # .get(191113739)))


if __name__ == "__main__":
    main()

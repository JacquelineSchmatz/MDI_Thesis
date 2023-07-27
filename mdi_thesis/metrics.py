"""
Module for metric calculations.
"""
import timeit
import json
import logging
import collections
import math
import csv
from datetime import date, datetime
import time
import regex as re
from typing import Dict, Tuple, Union  # , List, Any
import numpy as np
from dateutil import relativedelta

import mdi_thesis.base.base as base
import mdi_thesis.base.utils as utils
import mdi_thesis.external as external

# logger = logging.getLogger(__name__)
# handler = logging.StreamHandler()
# formatter = logging.Formatter(
#     "%(asctime)s %(name)-12s %(levelname)-8s %(message)s")
# handler.setFormatter(formatter)
# logger.addHandler(handler)
# logger.setLevel(logging.DEBUG)


def select_data(repo_nr: int = 0,
                path: str = "",
                query_parameters: str = "",
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
            query_parameters=query_parameters,
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
    contributor_count = utils.get_contributors(base_data.get("contributors"),
                                               check_contrib=True)
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
    dependents = data_object.get_dependents(dependents_details=False)
    for repo, dep_count in dependents.items():
        scores_per_repo[repo].update({"dependents_count": dep_count.get("total_dependents")})

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


def github_community_health_percentage(
        data_object) -> Dict[int, Dict[str, Union[float, bool]]]:
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
        custom_health_percentage = (len(info_list)/sum(info_list))
        infos = {"community_health_score": score,
                 "custom_health_score": custom_health_percentage,
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
                              "average_issues_created_per_week":
                              average_per_week,
                              "average_issue_comments": avg_issue_comments,
                              "average_issue_resolving_days": avg_date_diff,
                              "average_first_response_time_days":
                              avg_first_response_time_days,
                              "ratio_open_total": ratio_open,
                              "ratio_closed_total": ratio_closed}

    return issues_infos


def support_rate(data_object) -> Dict[int, float]:
    """
    The support rate uses issues and pulls which received a response
    in the last 6 months. Pulls are excluded from the issues
    (bc. pulls are also included in queried issues data).
    Pulls are filtered seperately, since the time filter
    recognizes merges too,
    yet this metric focuses only on comments as responses.
    param data_object: Request object, required to gather data
    of already selected repositories.
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Support rate for each repository.
    """
    support_rate_results = {}
    filter_date = date.today() - relativedelta.relativedelta(months=6)
    filter_date_str = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    # All issues required to get information about pulls in issue data
    issues_pulls = data_object.query_repository(
        ["issue"],
        filters={"since": filter_date_str,
                 "state": "all"})
    issue_flag = {}

    for repo, data in issues_pulls.get("issue").items():
        for issue in data:
            pull_request_id = issue.get("pull_request")
            is_pull_request = bool(pull_request_id)
            issue_number = issue.get("number")
            issue_flag[issue_number] = is_pull_request

    issue_comments = data_object.get_single_object(
        feature="issue_comments",
        filters={
            "since": filter_date_str,
            "state": "all"
            },
        output_format="list")

    for repo, data in issue_comments.items():
        issues_with_response = 0
        total_issues = 0
        total_pulls = 0
        pulls_with_response = 0
        for repo_issues in data:
            for issue, comments in repo_issues.items():
                # If issue is no pull
                if not issue_flag.get(issue):
                    print(issue)
                    total_issues += 1
                    if comments:
                        issues_with_response += 1
                else:
                    total_pulls += 1
                    if comments:
                        pulls_with_response += 1
        if total_issues == 0:
            issue_support = 0
        else:
            issue_support = issues_with_response / total_issues
        if total_pulls == 0:
            pulls_support = 0
        else:
            pulls_support = pulls_with_response / total_pulls
        support_rate_val = ((issue_support + pulls_support)/2)*100
        support_rate_results[repo] = round(support_rate_val, 2)

    return support_rate_results


def code_dependency(data_object) -> Dict[int, Dict]:
    """
    Dependencies retrieved from GitHub's Dependency Graph.
    Upstream dependencies show on how many other projects
    the passed repositories depend on -> GitHub Dependencies.
    Downstream shoe how many other repositories depend on the
    passed repositories -> GitHub Dependents.
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: total upstream and downstream dependencies +
    Visible downstream dependencies
    """
    dependencies = {}
    upstream_dependencies = data_object.get_dependencies()
    downstream_dependencies = data_object.get_dependents(
        dependents_details=False)
    for repo, data in downstream_dependencies.items():
        total_upstream = len(upstream_dependencies.get(repo))
        total_downstream = data.get("total_dependents")
        visible_downstream = data.get("visible_dependents")
        dependencies[repo] = {"total_upstream": total_upstream,
                              "total_downstream": total_downstream,
                              "visible_downstream": visible_downstream}

    return dependencies


# replaces branch_patch_ratio
def security_advisories(data_object) -> \
    Tuple[Dict[int, Dict[str, Union[int, float, None]]],
          Dict[int, Dict[str, Union[int, float, str, bool]]]]:
    """
    Uses GitHub's security advisories to retrieve information and calculate
    basic scores.
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Two dictionaries, containing scores and raw information
    """
    repo_advisories = data_object.query_repository(
        ["advisories"],
        filters={})
    advisory_infos = {}
    advisory_scores = {}
    for repo, advisory in repo_advisories.get("advisories").items():
        advisories_available = bool(advisory)
        advisories = {}
        vuln_patched = 0
        vuln_not_patched = 0
        cvss_scores = []
        closed_adv = 0
        severities = []
        for adv in advisory:
            # On GitHub, advisories can only be set to withdrawn
            # by contacting the support if the advisory was made in error.
            withdrawn_at = bool(adv.get("withdrawn_at"))
            if withdrawn_at:
                continue
            adv_id = adv.get("ghsa_id")
            cve_id = adv.get("cve_id")
            severity = adv.get("severity")  # low, medium, high, critical
            severities.append(severity)
            state = adv.get("state")  # triage, draf, published or closed
            if state == "closed":
                closed_adv += 1
            published_at = adv.get("published_at")
            cvss_score = adv.get("cvss").get("score")
            if not cvss_score:
                if cve_id:
                    # if no score was provided but an id is available,
                    # NVD is checked.
                    cvss_score = external.get_nvds(cve_id)
            if cvss_score:
                cvss_scores.append(cvss_score)
            cwes = adv.get("cwes")
            vulnerabilities = adv.get("vulnerabilities")
            if vulnerabilities:
                for vul_dict in vulnerabilities:
                    # package_name = vul_dict.get("package").get("name")
                    package_patched = bool(vul_dict.get("patched_versions"))
                    if package_patched:
                        vuln_patched += 1
                    else:
                        vuln_not_patched += 1

            advisories[adv_id] = {"cve_id": cve_id,
                                  "severity": severity,
                                  "state": state,
                                  "published_at": published_at,
                                  "cvss_score": cvss_score,
                                  "cwes": cwes}
        severity_high_count = severities.count("high")
        severity_critical_count = severities.count("critical")
        severity_high_critical_total = (severity_high_count +
                                        severity_critical_count)
        if severities:
            ratio_severity_high_crit = (severity_high_critical_total /
                                        len(severities))
        else:
            ratio_severity_high_crit = None
        if cvss_scores:
            mean_cvs_score = np.mean(cvss_scores)
        else:
            mean_cvs_score = None
        total_vuln = vuln_patched + vuln_not_patched
        if total_vuln > 0:
            patch_ratio = vuln_patched / total_vuln
        else:
            patch_ratio = None
        scores = {"advisories_available": advisories_available,
                  "patch_ratio": patch_ratio,
                  "closed_advisories": closed_adv,
                  "mean_cvss_score": mean_cvs_score,
                  "ratio_severity_high_crit":
                  ratio_severity_high_crit}

        advisory_scores[repo] = scores
        advisory_infos[repo] = advisories
    return advisory_scores, advisory_infos


def contributions_distributions(data_object) -> Dict[int, Dict[str, Union[int, float]]]:
    """
    Includes Bus Factor and Scores representing the Pareto Principle.
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Information about the distribution of the contributions per
    contributors by calculating the bus factor and the pareto principle
    for each repository.
    """
    filter_date = date.today() - relativedelta.relativedelta(years=1)  # years = 1
    filter_date = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    commits = data_object.query_repository(["commits"],
                                           filters={"since": filter_date})
    repo_pareto = {}
    for repo, commits in commits.get("commits").items():
        total_committer = []
        no_committer = 0
        for commit in commits:
            contributor = None
            co_author = None
            try:
                committer_email = commit.get("commit").get("committer").get("email")
                author_email = commit.get("commit").get("author").get("email")
                message = commit.get("commit").get("message")
                co_author_line = re.findall(r"Co-authored-by:(.*?)>", message)
                for value in co_author_line:
                    co_author = value.split("<")[-1]
                    total_committer.append(co_author)
                if committer_email != author_email:
                    contributor = author_email
                else:
                    contributor = committer_email

            except AttributeError:
                no_committer += 1
            total_committer.append(contributor)
        committer_counter = collections.Counter(total_committer).values()
        commits_sorted = sorted(committer_counter, reverse=True)
        t_1 = sum(committer_counter) * 0.5
        t_2 = 0
        bus_factor_score = 0

        total_contributions = sum(commits_sorted)
        total_contributer = len(commits_sorted)
        # Round up since no half contributors exist
        twenty_percent = math.ceil(total_contributer * 0.2)
        eighty_percent = math.ceil(total_contributions * 0.8)
        running_contributions = 0
        pareto_ist = 0
        for contrib, contributions in enumerate(commits_sorted, start=1):
            running_contributions += contributions
            if contrib == twenty_percent:
                # twenty_per_contributions = contrib
                pareto_ist = running_contributions
            if t_2 <= t_1:
                t_2 += contributions
                bus_factor_score += 1
        prot_diff = np.round(np.absolute((eighty_percent - pareto_ist)) / (
            (eighty_percent + pareto_ist) / 2), 2)
        pareto_results = {"bus_factor_score": bus_factor_score,
                          "twenty_percent_contributor":
                          twenty_percent,
                          "eighty_percent_contributions_soll":
                          eighty_percent,
                          "eighty_percent_contributions_ist":
                          pareto_ist,
                          "diff_pareto_soll_ist_percent":
                          prot_diff}
        repo_pareto[repo] = pareto_results
    return repo_pareto


def contributors_per_file(data_object) -> Dict[int, float]:
    """
    Iterates through commits and gets the committer and the
    trees (subdirectories) which lead to files recursevly,
    until the edited file is found to get all committers
    for each file.
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Average number of contributors per each file
    """
    filter_date = date.today() - relativedelta.relativedelta(months=1)
    filter_date_str = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    results_dict = {}
    single_commits = data_object.get_single_object(
        feature="commits",
        filters={
            "since": filter_date_str
            }, output_format="dict")
    for repo, commit in single_commits.items():
        file_committer = {}
        for features in commit.values():
            for row in features:
                files = row.get("files")
                committer = row.get("commit").get("committer").get("email")
                author = row.get("commit").get("author").get("email")
                verification = row.get("commit").get(
                    "verification").get("verified")
                if verification:
                    contributor = author
                else:
                    contributor = committer
                for file in files:
                    filename = file.get("filename")
                    if filename not in file_committer:
                        file_committer[filename] = {contributor}
                    else:
                        file_committer[filename].add(contributor)

        if file_committer:
            num_contributors_per_files = []
            for committer_ids in file_committer.values():
                num_contributors_per_files.append(len(committer_ids))
            avg_num_contributors_per_file = np.ceil(
                np.mean(num_contributors_per_files))
        else:
            avg_num_contributors_per_file = None
        results_dict[repo] = avg_num_contributors_per_file
    return results_dict


def number_of_support_contributors(data_object) -> Dict[int, int]:
    """
    Calculates the number of active contributors per repository
    in the last 6 months and assigns a score to each.
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Score for the number of active contributors
    """
    filter_date = date.today() - relativedelta.relativedelta(months=6)
    filter_date = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    commits = data_object.query_repository(["commits"],
                                           filters={"since": filter_date})
    support_contributors = {}
    for repo, commits in commits.get("commits").items():
        total_committer = set()
        for commit in commits:
            try:
                committer_id = commit.get("committer").get("id")
                total_committer.add(committer_id)
            except AttributeError:
                pass
        total_committer = len(total_committer)
        score = 0
        if total_committer < 5:
            score = 1
        elif total_committer >= 5 and total_committer <= 10:
            score = 2
        elif total_committer > 10 and total_committer <= 20:
            score = 3
        elif total_committer > 20 and total_committer <= 50:
            score = 4
        elif total_committer > 50:
            score = 5

        result_score = score/5*100
        support_contributors[repo] = result_score
    return support_contributors


def elephant_factor(data_object) -> Dict[int, int]:
    """
    Calculates the elephant factor (distribution of contributions
    by organizations user belong to) for each repository.
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Elephant factor for each repository
    """
    base_data = data_object.query_repository([
        "contributors"], filters={})
    repo_elephant_factor = {}
    for repo, contributors in base_data.get("contributors").items():
        org_contributions = {}
        user_contributions = {}
        for user in contributors:
            login = user.get("login")
            contributions = user.get("contributions")
            user_contributions[login] = contributions
        contributor_list = list(user_contributions)
        users = data_object.query_repository(["organization_users"],
                                             repo_list=contributor_list,
                                             filters={})
        for user, data in users.get("organization_users").items():
            for organization in data:
                try:
                    org_name = organization.get("login")
                except AttributeError:
                    continue
                if org_name:
                    if org_name not in org_contributions:
                        org_contributions[org_name] = user_contributions.get(user)
                    else:
                        org_contributions[org_name] += user_contributions.get(user)
        t_1 = sum(org_contributions.values()) * 0.5
        t_2 = 0
        orgs_sorted = sorted(org_contributions.values(), reverse=True)
        elephant_factor_score = 0
        for org_count in orgs_sorted:
            if t_2 <= t_1:
                t_2 += org_count
                elephant_factor_score += 1
        repo_elephant_factor[repo] = elephant_factor_score
    return repo_elephant_factor


def size_of_community(data_object) -> Dict[int, float]:
    """
    The size of community includes contributors and subscribers.
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Size of community score for each repository
    """
    repo_community = {}
    base_data = data_object.query_repository(
        ["repository",
         "contributors"],
         filters={}
         )
    contributor_count = utils.get_contributors(base_data.get("contributors"),
                                               check_contrib=False)
    for repo, data in base_data.get("repository").items():
        score = 0
        subscribers_count = data.get("subscribers_count")
        cont_count = contributor_count.get(repo)
        community_count = subscribers_count + cont_count
        if community_count < 50:
            score = 1
        elif community_count >= 50 and community_count <= 100:
            score = 2
        elif community_count > 100 and community_count <= 200:
            score = 3
        elif community_count > 200 and community_count <= 300:
            score = 4
        elif community_count > 300:
            score = 5
        community_score = (score/5) * 100
        repo_community[repo] = int(community_score)
    return repo_community


def churn(data_object) -> Dict[int, float]:
    """
    Score, representing the code change turn ratio.
    :param data_object: Request object, required to gather data
    of already selected repositories.
    :return: Churn score each repository
    """
    filter_date = date.today() - relativedelta.relativedelta(months=1)
    filter_date_str = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    results_dict = {}
    single_commits = data_object.get_single_object(
        feature="commits",
        filters={
            "since": filter_date_str
            }, output_format="dict")
    for repo, commit in single_commits.items():
        lines_added = 0
        lines_deleted = 0
        for features in commit.values():
            for row in features:
                stats = row.get("stats")
                additions = stats.get("additions")
                deletions = stats.get("deletions")
                lines_added += additions
                lines_deleted += deletions
        churn_score = lines_deleted / lines_added
        results_dict[repo] = round(churn_score, 2)
    return results_dict
     


def branch_lifecycle(data_object):
    """
    
    """
    pass


def select_to_csv(logger):
    languages = ["python", "java", "php", "JavaScript", "cpp"]
    # languages = ["python"]
    header = ["language", "repo_id", "repo_name", "repo_owner_login", "size", "stargazers_count", "watchers_count"]
    filter = "&sort=stars&order=desc&is:public&template:false&archived:false&pushed:>=2022-12-31"
    # filter = "&sort=stars&order=desc"
    with open('repo_sample_large.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for lang in languages:
            logger.debug(f"Getting language: {lang}")
            logger.debug(f"Getting repos with language: {lang}")
            query = "language:" + lang + filter
            obj = select_data(query_parameters=query, repo_nr=1000)
            print(f"Finished getting search results for language {lang}")
            repos = obj.query_repository(["repository"], filters={})
            for repo, data in repos.get("repository").items():
                try:
                    language = data.get("language")
                    name = data.get("name")
                    owner = data.get("owner").get("login")
                    size = data.get("size")
                    stargazers_count = data.get("stargazers_count")
                    watchers_count = data.get("watchers_count")
                    row = [language, repo, name, owner, size, stargazers_count, watchers_count]
                except AttributeError:
                    logger.debug(f"Could not query repo {repo}")
                    row = f"Could not query repo {repo}"
                writer.writerow(row)
            time.sleep(240)
        

def main():
    """
    Main in progress
    """
    print(datetime.now())
    logger = base.get_logger(__name__)
    logger.setLevel(logging.DEBUG)
    repo_ids_path = "mdi_thesis/preselected_repos.txt"

    # selected_repos.select_repos(repo_list=repo_ids)
    # obj = select_data(path=repo_ids_path)
    # obj = select_data(repo_nr=1, order="desc")
    # print(elephant_factor(obj))

    # print(obj)
    # print(maturity_level(obj))
    # print(osi_approved_license(obj))
    # print(obj.selected_repos_dict)
    # print(criticality_score(obj))
    # print(pull_requests(obj))
    # print(project_velocity(obj))
    # print(github_community_health_percentage(obj))
    # print(support_rate(obj))
    # print(code_dependency(obj))
    # print(security_advisories(obj))
    # print(bus_factor(obj))
    # print(contributions_distributions(obj))
    # print(contributors_per_file(obj))
    # print(number_of_support_contributors(obj))
    # TODO: Update dependents of criticality score (distinct values, source not content)
    # print(size_of_community(obj))
    select_to_csv(logger=logger)
    

    # print(selected_repos.get_single_object(feature="commits"))
    # print(selected_repos.query_repository(["advisories"]))
    # print(selected_repos.query_repository(["commits"]))
    # print(selected_repos.get_context_information(main_feature="contributors", sub_feature="users"))
    # .get("community_health")  # .get(191113739))
    # print(len(selected_repos.query_repository(["contributors"])))
    # .get("community_health")  # .get(191113739)))
    print(datetime.now())
if __name__ == "__main__":
    main()

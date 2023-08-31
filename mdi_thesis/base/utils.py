"""
Module for functions required to gather information
from the GitHub API
"""
import logging
import json
import os
import re
from typing import Dict, List, Any, Union
import requests

logger = logging.getLogger(__name__)


def __get_ids_from_txt__(path: str) -> List[int]:
    with open(path) as f:
        lines = f.read().splitlines()
        ids = [int(i) for i in lines]
        return ids


def invert_dict(dictionary: Dict):
    """
    Change dictionary values to keys.
    """
    inverse = dict()
    for key in dictionary:
        for item in dictionary[key]:
            if item not in inverse:
                inverse[item] = [key]
            else:
                inverse[item].append(key)
    return inverse


def clean_results(
    results: List[Any],
) -> Dict[int, Dict[str, Any]]:
    """
    Removes unwanted information from the queried repository data.
    :param results: Results to be clean in dictionary form
    :param key_list: List of keys to be taken
    :returns: dictionary with clean lists
    """
    dictionary_of_list = {}
    key_list = ["id", "node_id", "name", "owner", "html_url"]
    item_counter = 0
    test_dict = {}
    for item in results:
        if "id" in item:
            item_counter += 1
            repo_id = item["id"]
            repo_name = item["name"]
            repo_owner = item["owner"]
            selected_items = {k: v for k, v in item.items() if k in key_list}
            test_dict[repo_id] = [item_counter, repo_name, repo_owner]
            dictionary_of_list[repo_id] = selected_items
    return dictionary_of_list


def get_subfeatures(
    session: requests.Session,
    headers: Dict[str, str],
    features: List[str],
    object_id: int,
    object_url: str,
    sub_url: str,
    logger
) -> Dict[int, List[Dict[str, Any]]]:
    """
    :param session: Active request session
    :param headers: Headers for query with active session
    :param features: Which features are queried from GitHub
    :param object_id: Object ID,
     from which the concerning comments are queryied (e.g. pull, issue)
    :param object_url:
    Base url to which the object id is added to query the information.
    :param sub_url: Sub url referring to the subfeatures of a certain
    information (e.g. comments as subfeatures for issues as features)
    :return: Dictionary with the object id and the concerning comments
    """
    logger.info("Starting querying subfeatures.")
    subfeature_dict = {}
    url = object_url + "/" + str(object_id) + sub_url
    url_param = "?per_page=100&page=1"  # "?simple=yes&per_page=100&page=1"
    logger.info("Getting page 1")
    start_url = url + url_param
    response = session.get(start_url, headers=headers, timeout=100)
    results = response.json()
    if "last" in response.links:
        nr_of_pages = response.links.get(
            "last").get("url").split("&page=", 1)[1]
        if results:
            if int(nr_of_pages) > 1:
                for page in range(2, int(nr_of_pages) + 1):
                    url_repo = f"{url}?simple=yes&per_page=100&page={page}"
                    res = session.get(url_repo, headers=headers, timeout=100)
                    logger.info("Query page %s of %s", page, nr_of_pages)
                    logging.info("Extending results...")
                    try:
                        # TODO Check dict object has no attribute extend error
                        next_result = res.json()
                        results.extend(next_result)
                    except Exception as error:
                        logger.error("Could not extend: %s...\nError: %s",
                                    next_result, error)
        else:
            results = {}
    element_dict = {}  # type: dict[str, Any]
    subfeature_list = []
    if isinstance(results, list):
        for element in results:
            element_dict = {}
            for feature in features:
                element_dict[feature] = element.get(feature)
            subfeature_list.append(element_dict)
        subfeature_dict[object_id] = subfeature_list
    elif isinstance(results, dict):
        for feature in features:
            element_dict[feature] = results.get(feature)
        subfeature_list.append(element_dict)
        subfeature_dict[object_id] = subfeature_list
    else:
        subfeature_dict[object_id] = []
    return subfeature_dict


def get_contributors(contributors_data, check_contrib=False) -> Dict[int, int]:
    """
    Gets number of contributors.
    :param contributors_data: Data with user and their contributions
    :param check_contrib: True if for contributions has to be checked
    :return: Number of contributors per repository
    """
    repo_contributors = {}
    for repo, data in contributors_data.items():
        contributors_nr = 0
        if check_contrib:
            for user in data:
                if isinstance(user, dict):
                    try:
                        contributions = user.get("contributions")
                        if contributions:
                            contributors_nr += 1
                    except AttributeError as att_err:
                        print(f"Attribute error {att_err} at data {data} and user{user}")
        else:
            contributors_nr = len(data)
        repo_contributors[repo] = contributors_nr
    return repo_contributors


def get_contributor_per_files(commit):
    """
    """

    file_committer = {}
    for features in commit.values():
        for row in features:
            files = row.get("files")
            try:
                co_authors = set()
                committer_email = row.get("commit").get("committer").get("email")
                author_email = row.get("commit").get("author").get("email")
                message = row.get("commit").get("message")
                co_author_line = re.findall(r"Co-authored-by:(.*?)>", message)
                verification = row.get("commit").get(
                    "verification").get("verified")
                for value in co_author_line:
                    co_author = value.split("<")[-1]
                    co_authors.add(co_author)
                    # ntotal_committer.append(co_author)
                if committer_email != author_email:
                    contributor = author_email
                else:
                    if verification:
                        contributor = author_email
                    else:
                        contributor = committer_email
            except AttributeError as atterr:
                logger.error("Attribute error: %s", atterr)
                raise
            if co_authors:
                contributors = {contributor} | co_authors
            else:
                contributors = {contributor}
            for file in files:
                filename = file.get("filename")
                if filename not in file_committer:
                    file_committer[filename] = contributors
                else:
                    existing_file = file_committer.get(filename)
                    if existing_file:
                        file_committer[filename] = existing_file.union(
                            contributors)
    return file_committer


def dict_to_json(data: Union[Dict, List], data_path: str, feature: str):
    """
    Helper function to write file.
    :param data: data to be written
    :param data_path: Path where file should be written.
    :param feature: Feature for filename.
    """
    json_object = json.dumps(data, indent=4)
    file_name = os.path.join(data_path, (feature + ".json"))
    with open(file_name, "w", encoding='utf-8') as outfile:
        outfile.write(json_object)


def json_to_dict(path: str) -> Dict:
    """
    Helper function
    :param path: Path to json file
    :return: dictionary with json content
    """
    with open(path, encoding='utf-8') as json_file:
        data = json.load(json_file)
    return data

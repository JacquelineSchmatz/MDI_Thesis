import requests
import logging

logger = logging.getLogger(__name__)


def __get_ids_from_txt__(path: str) -> list:
    with open(path) as f:
        lines = f.read().splitlines()
        ids = [int(i) for i in lines]
        return ids


def clean_results(
    results: dict,
    key_list: list = ["id", "node_id", "name", "owner", "html_url"],
) -> dict:
    """
    :param results: Results to be clean in dictionary form
    :param key_list: List of keys to be taken
    :returns: dictionary with clean lists
    """
    dictionary_of_list = {}

    for item in results:
        if "id" in item:
            repo_id = item["id"]
            selected_items = {k: v for k, v in item.items() if k in key_list}
            dictionary_of_list[repo_id] = selected_items
        else:
            pass
    return dictionary_of_list


def get_comments(
    headers: dict, features: list, comment_object: int, object_url: str
) -> dict:
    """
    TODO: Add "since" parameter, bc. otherwise only data from 1. page are queried
    :param object: Object from which the concerning comments are queryied (e.g. pull, issue)
    :param object_url: Base url to which the object id is added to query the information.
    :return: Dictionary with the object id and the concerning comments
    """

    comment_dict = {}
    url = object_url + str(comment_object) + "/comments"
    response = requests.get(url, headers=headers, timeout=100)
    results = response.json()
    element_dict = {}
    if results:
        for element in results:
            element_dict = {}
            for feature in features:
                element_dict[feature] = element.get(feature)
        comment_dict[comment_object] = element_dict
    else:
        comment_dict[comment_object] = {}
    return comment_dict


def get_subfeatures(
    session: requests.Session,
    headers: dict,
    features: list,
    object_id: int,
    object_url: str,
    sub_url: str,
) -> dict:
    """
    :param object: Object from which the concerning comments are queryied (e.g. pull, issue)
    :param object_url: Base url to which the object id is added to query the information.
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
    # print(results)
    # TODO: CHECK WHY DIFFERENT OUTPUT THEN DOCUMENTATION!
    # IF NECESSARY SKIP INFORMATION ABOUT COMMENTS PER USER AND ONLY USE NUMBER OF COMMENTS
    # quit()
    print(len(results))
    if "last" in response.links:
        nr_of_pages = response.links.get("last").get("url").split("&page=", 1)[1]
        print(response.links.get("last"))
        if results:
            if int(nr_of_pages) > 1:
                for page in range(2, int(nr_of_pages) + 1):
                    url_repo = f"{url}?simple=yes&per_page=100&page={page}"
                    res = session.get(url_repo, headers=headers, timeout=100)
                    logger.info("Query page %s of %s", page, nr_of_pages)
                    logging.info("Extending results...")
                    # print(res.json())
                    try:
                        results.extend(res.json())
                    except Exception as error:
                        print(f"Error: {error}")
                        print(f"Could not extend: {res.json()}")
        else:
            results = {}
        # while "next" in response.links.keys():
        #    res = requests.get(response.links["next"]["url"], headers=headers)
        #   results.extend(res.json())
    print(results)
    quit()
    element_dict = {}
    subfeature_list = []
    if isinstance(results, list):
        for element in results:
            element_dict = {}
            for feature in features:
                element_dict[feature] = element.get(feature)
                print(object_id)
                print(element_dict)
        subfeature_list.append(element_dict)
        subfeature_dict[object_id] = subfeature_list
    elif isinstance(results, dict):
        for feature in features:
            element_dict[feature] = results.get(feature)
        subfeature_list.append(element_dict)
        subfeature_dict[object_id] = subfeature_list
    else:
        subfeature_dict[object_id] = {}

    return subfeature_dict


def get_users(user_list: list):
    """
    TODO: Placeholder for getting users to check if they belong to a company.
    :param user_list: list with user ids
    :return:

    """
    feature_list = ["login", "id", "name", "company"]
    for user in user_list:
        request_url = "https://api.github.com/users/" + str(user)

    pass


def get_commits():
    feature_list = ["comment_count", "stats", "files"]
    # https://api.github.com/repos/OWNER/REPO/commits/REF


def get_dependency_diff(commits):
    """
    TODO: Note from the documentation conc. BASEHEAD:
    "The base and head Git revisions to compare.
    ...
    This parameter expects the format {base}...{head}."

    :param commits: refers to the head parameter.
    :return:
    """
    request_url_1 = "https://api.github.com/repositories/"
    request_url_2 = "/dependency-graph/compare/BASEHEAD"
    feature_list = [
        "change_type",
        "ecosystem",
        "name",
        "license",
        "vulnerabilities",
    ]

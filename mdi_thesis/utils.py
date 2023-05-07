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


def get_comments(comment_object: int, object_url: str) -> dict:
    """
    TODO: Add "since" parameter, bc. otherwise only data from 1. page are queried
    :param object: Object from which the concerning comments are queryied (e.g. pull, issue)
    :param object_url: Base url to which the object id is added to query the information.
    :return: Dictionary with the object id and the concerning comments
    """
    feature_list = [
        "id",
        "created_at",
        "updated_at",
    ]
    comment_dict = {}
    url = object_url + str(comment_object) + "/comments"
    response = requests.get(url, headers=self.headers, timeout=100)
    results = response.json()
    if results:
        for element in results:
            element_dict = {}
            for feature in feature_list:
                element_dict[feature] = element.get(feature)
        comment_dict[comment_object] = element_dict
    else:
        comment_dict[comment_object] = {}
    return comment_dict


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

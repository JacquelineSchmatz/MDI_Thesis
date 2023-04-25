"""
mdi_thesis base module.

This is the principal module of the mdi_thesis project.
here you put your main classes and objects.

Be creative! do whatever you want!

If you want to replace this with a Flask application run:

    $ make init

and then choose `flask` as template.
"""
from datetime import date
import requests
import constants

# import numpy as np


class Request:
    """
    Class for GitHub Request
    """

    def __init__(self) -> None:
        self.token = constants.API_TOKEN
        self.headers = {"Authorization": "token " + self.token}
        self.url = ""
        self.response = requests.Response()
        self.response_dict = {}
        self.results_dict = {}
        self.selected_repos_dict = self.select_repos()

    def select_repos(
        self,
        repo_nr: int = 100,
        language: str = "python",
        sort: str = "stars",
        repo_list: list = [],
    ) -> list:
        """
        Select Repositories according to Parameters
        :param repo_nr: Number of queried repositories.
        :param language: Programming language of queried repositories.
        :param sort: Factor by which the repositories are sorted.
        :param repo_list:
        :returns: List with dictionaries of selected repositories
        """
        if repo_list:
            self.selected_repos_list = []
            for item in repo_list:
                url = f"https://api.github.com/repositories/{item}"
                response = requests.get(url, headers=self.headers, timeout=100)
                results_dict = response.json()
                self.selected_repos_list.append(results_dict)

        else:
            self.url = (
                "https://api.github.com/search/repositories?q=language:"
                + language
                + "&sort="
                + sort
                + "&access_token="
                + self.token
            )
            self.response = requests.get(self.url, headers=self.headers, timeout=100)
            self.response_dict = self.response.json()
            self.results_dict = self.response_dict["items"]
            self.selected_repos_list = self.results_dict[:repo_nr]

        self.dictionary_of_list = self.clean_results(self.selected_repos_list)
        # Switching from list with dictionaries to dictionary with lists

        # self.switched_repo_dict = {
        #     key: [i[key] for i in self.repo_dict] for key in self.repo_dict[0]
        # }
        # self.selected_repos_urls = self.switched_repo_dict["html_url"]
        return self.selected_repos_list

    def clean_results(
        self,
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


class Results(Request):
    """
    Class for cleaned returned results.
    """

    def __init__(self) -> None:
        super().__init__()
        self.data_dict = {}

    def get_repo_request(
        self,
        repository=False,
        issue=False,
        release=False,
        license=False,
        forks=False,
        pull_requests=False,
        contributors=False,
        commits=False,
        issue_comment=False,
        community_health=False,
    ):
        """
        TODO: Replace function with lookup json file (query_features.json)
        Calls functions which perform actual query.
        :param repository: If repository data is required 1, else 0
        :param issue: If issue data is required 1, else 0
        """
        if repository:
            request_url_1 = "https://api.github.com/repositories/"
            feature_list = [
                "name",
                "owner",
                "created_at",
                "updated_at",
                "pushed_at",
                "size",
                "stargazers_count",
                "watchers_count",
                "language",
                "has_issues",
                "forks_count",
                "license",
                "open_issues",
                "subscribers_count",
            ]

        if issue:
            # Pull requests are included in issues and are identified by the pull_request key
            request_url_1 = "https://api.github.com/repositories/"
            request_url_2 = "/issues?state=all"
            feature_list = [
                "id",
                "number",
                "state",
                "title",
                "created_at",
                "updated_at",
                "closed_at",
                "pull_request",
            ]

        if issue_comment:
            # TODO: Check if pull requests are included in issues
            request_url_1 = "https://api.github.com/repositories/"
            request_url_2 = "/issues/comments"
            feature_list = [
                "id",
                "created_at",
                "updated_at",
            ]

        if release:
            request_url_1 = "https://api.github.com/repositories/"
            request_url_2 = "/releases"
            feature_list = ["id", "tag_name", "prerelease", "published_at"]

        if license:
            # Most projects only have one license, henve the metric should be redefined eventually
            request_url_1 = "https://api.github.com/repositories/"
            request_url_2 = "/license"
            feature_list = ["license"]

        if forks:
            request_url_1 = "https://api.github.com/repositories/"
            request_url_2 = "/forks"
            feature_list = [
                "id",
                "name",
                "owner",
                "fork",
                "is_template",
                "pushed_at",
                "created_at",
            ]

        if pull_requests:
            request_url_1 = "https://api.github.com/repositories/"
            request_url_2 = "/pulls"
            feature_list = [
                "id",
                "number",
                "state",
                "created_at",
                "updated_at",
                "closed_at",
                "pushed_at",
                "merged_at",
                "head",  # head required to see if merged branch is a fork ("fork"=true/false)
            ]

        if contributors:
            request_url_1 = "https://api.github.com/repositories/"
            request_url_2 = "/contributors"
            feature_list = [
                "id",
                "login",
                "contributions",
            ]
        if commits:
            request_url_1 = "https://api.github.com/repositories/"
            request_url_2 = "/commits"
            feature_list = [
                "commit",
                "committer",
            ]
        if community_health:
            request_url_1 = "https://api.github.com/repositories/"
            request_url_2 = "/community/profile"
            feature_list = [
                "health_percentage",
                "updated_at",
                "description",
                "documentation",
                "files",
            ]
        #    feature_list = []
        #    request_url = " "
        # else:
        #   feature_list = []
        #    request_url = " "
        data_dict = self.get_repository_data(
            feature_list=feature_list,
            request_url_1=request_url_1,
            request_url_2=request_url_2,
        )

        return data_dict

    def get_users(self, user_list: list):
        """
        TODO: Placeholder for getting users to check if they belong to a company.
        :param user_list: list with user ids
        :return:

        """
        feature_list = ["login", "id", "name", "company"]
        for user in user_list:
            request_url = "https://api.github.com/users/" + str(user)

        pass

    def get_dependency_diff(self, commits):
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

    def __get_comments(self, comment_object: int, object_url: str) -> dict:
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

    def get_issue_comment_per_issue(self):
        """
        Function to retrieve issues andd the comments for each.
        Note: Issues also contain pull requests.
        TODO: Add "since" parameter, bc. otherwise only data from 1. page are queried
        :return: A dictionary with the repository id, its issue ids and the comments per issue.
        """
        request_url_1 = "https://api.github.com/repositories/"
        request_url_2 = "/issues/"
        issues_per_repo = self.get_repo_request(issue=True)
        issue_comment_dict = {}
        for repository in issues_per_repo:
            issues_list = []
            url = request_url_1 + str(repository) + request_url_2
            issues = issues_per_repo.get(repository)
            # print(repository)
            # print(issues)
            for issue in issues:
                issue_id = issue.get("number")
                comment_dict = self.__get_comments(object=issue_id, object_url=url)
                issues_list.append(comment_dict)
            issue_comment_dict[repository] = issues_list
        return issue_comment_dict

    def get_repository_data(
        self, feature_list: list, request_url_1: str, request_url_2: str
    ):
        """
        Query data from repositories
        :param feature_list: Features are the information which should be stored after querying to avoid gathering unwanted data.
        :param request_url_1: First part of the url, split bc. in some cases information such as the repository id must be in the middle of the url.
        :param request_url_2: Second part of the url, pointing to the GitHub API subcategory.

        :return:
        """
        self.data_dict = {}
        for repo_id in self.dictionary_of_list:
            # url_repositories = f"https://api.github.com/repositories/{repo_id}"
            if request_url_2:
                url_repo = str(request_url_1 + str(repo_id) + request_url_2)
            else:
                url_repo = str(request_url_1 + str(repo_id))
            response = requests.get(url_repo, headers=self.headers, timeout=100)
            results = response.json()
            if isinstance(results, list):
                # print(results[0])
                return_data = []
                for element in results:
                    element_dict = {}
                    for feature in feature_list:
                        element_dict[feature] = element.get(feature)
                    return_data.append(element_dict)

            elif isinstance(results, dict):
                return_data = {}
                for feature in feature_list:
                    return_data[feature] = results.get(feature)
            # print(return_dict)
            self.data_dict[repo_id] = return_data
        return self.data_dict


def main():
    """
    Main in progress
    """
    repo_ids = [
        307260205,
        101138315,
        191113739,
        537603333,
        34757182,
        84533158,
        573819845,
        222751131,
        45723377,
        2909429,
        74073233,
        80990461,
        138331573,
        41654081,
        8162715,
        152166877,
        59720190,
        182097305518,
        253601257,
        221723816,
        143328315,
        7053637,
        10332822,
        65593050,
        36895421,
        143460965,
        189840,
        617798408,
        31912224,
    ]
    selected_repos = Results()
    # Statement for selecting top 25 repositories
    # selected_repos.select_repos(repo_nr=25)

    # Statement for selecting repositories according to list (for developing)
    selected_repos.select_repos(repo_list=repo_ids)
    # selected_repos.select_repos()
    # print(selected_repos.get_repository_data().get(31912224))
    print(selected_repos.get_repo_request(issue=True).get(617798408))  #
    # print(selected_repos.get_issue_comment_per_issue().get(617798408))


if __name__ == "__main__":
    main()

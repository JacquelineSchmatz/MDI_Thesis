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
        self, results, key_list=["id", "node_id", "name", "owner", "html_url"]
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

        # self.name = self.response_dict["name"]
        # self.owner = self.response_dict["owner"]["login"]
        # self.stars = self.response_dict["stargazers_count"]
        # self.repository = self.response_dict["html_url"]
        # self.created = self.response_dict["created_at"]
        # self.updated = self.response_dict["updated_at"]
        # self.desc = self.response_dict["description"]


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
    # selected_repos.select_repos(repo_nr=25)
    # test = selected_repos.select_repos(repo_list=repo_ids)
    # print(test[0])
    selected_repos.select_repos(repo_list=repo_ids)
    # selected_repos.select_repos()
    print(selected_repos.dictionary_of_list.keys())
    # print(selected_repos.dictionary_of_list.get(31912224))


if __name__ == "__main__":
    main()

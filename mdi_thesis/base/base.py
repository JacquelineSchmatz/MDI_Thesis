"""
mdi_thesis base module.

If you want to replace this with a Flask application run:

    $ make init

and then choose `flask` as template.
"""

import json
import time
from typing import Dict, List, Any
import logging
import math
from pathlib import Path
from dateutil import relativedelta
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import mdi_thesis.constants as constants
import mdi_thesis.base.utils as utils
import os


# logger = logging.getLogger(__name__)
# handler = logging.StreamHandler()
# formatter = logging.Formatter(
#     "%(asctime)s %(name)-12s %(levelname)-8s %(message)s")
# handler.setFormatter(formatter)
# logger.addHandler(handler)
# logger.setLevel(logging.ERROR)
def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Prevent logging from propagating to the root logger
        logger.propagate = 0
        console = logging.StreamHandler()
        logger.addHandler(console)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - line: %(lineno)s - %(funcName)s - %(module)s - %(message)s')
        console.setFormatter(formatter)
        logger.setLevel(logging.DEBUG)
        curr_path = Path(os.path.dirname(__file__))
        log_path = curr_path.parents[1]
        file_name = datetime.now().strftime('logger_%Y%m%d_%H_%M')
        file_path = os.path.join("outputs/logs/", file_name)
        fileHandler = logging.FileHandler("{0}/{1}.log".format(log_path, file_path))
        fileHandler.setFormatter(formatter)
        logger.addHandler(fileHandler)
        # consoleHandler = logging.StreamHandler()
        # consoleHandler.setFormatter(formatter)
        # logger.addHandler(consoleHandler)

    return logger


class Request:
    """
    Class for GitHub Request
    """
    def __init__(self) -> None:
        self.token = constants.API_TOKEN
        self.results_per_page = 100
        self.headers = {"Authorization": "token " + self.token}
        self.session = requests.Session()
        self.response = requests.Response()
        self.selected_repos_dict = {}  # type: dict[int, dict]
        self.repository_dict = {}  # type: dict[int, list[dict[str, Any]]]
        # TODO: Move filepath to other location
        query_features_file = open(
            "mdi_thesis/query_features.json", encoding="utf-8")
        self.query_features = json.load(query_features_file)
        self.logger = get_logger(__name__)
        curr_path = Path(os.path.dirname(__file__))
        self.output_path = os.path.join(curr_path.parents[1],
                                        "outputs/data/", )
        self.today = datetime.today()

    def select_repos(
        self,
        repo_nr: int,
        repo_list: List[int],
        query_parameters: str = ""
    ):
        """
        Select Repositories according to Parameters
        :param repo_nr: Number of queried repositories.
        :param language: Programming language of queried repositories.
        :param sort: Factor by which the repositories are sorted.
        :param repo_list: List with repositories if preselected
        :returns: List with dictionaries of selected repositories
        """
        selected_repos = []
        results_items = []
        if repo_nr < self.results_per_page:
            res_per_page = repo_nr
        else:
            res_per_page = self.results_per_page
        if repo_list:
            for item in repo_list:
                url = f"https://api.github.com/repositories/{item}"
                response = self.session.get(
                    url, headers=self.headers, timeout=100)
                results = response.json()
                while "next" in response.links.keys():
                    res = self.session.get(
                        response.links["next"]["url"], headers=self.headers
                    )
                    results.extend(res.json())
                selected_repos.append(results)
            self.selected_repos_dict = utils.clean_results(selected_repos)

        else:
            search_url = (
                "https://api.github.com/search/repositories?q="
                + query_parameters
                + "&access_token="
                + self.token
                + "&per_page="  
                # + "?simple=yes&per_page="
                + str(res_per_page)
            )
            initial_search_url = (
                search_url
                + "&page=1"
            )
            self.logger.debug("Initial search query: %s", initial_search_url)

            results = []
            cleaned_results = {}
            # Buffer with two pages in case of duplicate results
            repo_nr_buffer = repo_nr + (2 * (self.results_per_page))
            while len(cleaned_results) < repo_nr:
                try:
                    self.logger.info("Query page 1")
                    response = self.session.get(
                        initial_search_url, headers=self.headers, timeout=100)
                    results = response.json()
                    results_items = results["items"]
                    if repo_nr <= 100:
                        selected_repos.extend(results_items)
                        break
                    if response.links.get('next'):
                        results = self.get_next_pages(
                            response=response,
                            results=results_items,
                            target_num=repo_nr_buffer)
                        selected_repos.extend(results)
                        cleaned_results = utils.clean_results(selected_repos)
                    else:
                        continue
                except KeyError as key_err:
                    self.logger.error("Key error: %s", key_err)
                    time.sleep(10)
                else:
                    time.sleep(1)
            repo_counter = 0
            for repo, element in cleaned_results.items():
                self.selected_repos_dict[repo] = element
                repo_counter += 1
                if repo_counter == repo_nr:
                    break
            print("-----")
            print(len(self.selected_repos_dict))

    def check_rate_limit(self, response):
        # try:
        unix_time_to_reset = response.headers.get(
            "X-RateLimit-Reset")
        datetime_to_reset = datetime.fromtimestamp(int(unix_time_to_reset))
        time_till_rerun = datetime_to_reset - datetime.now()
        minutes_till_rerun = math.ceil(
            time_till_rerun.total_seconds() / 60)
        self.logger.critical("API rate exceeded. Sleeping %s minutes.",
                             minutes_till_rerun)
        time.sleep(time_till_rerun.total_seconds())
        # except AttributeError:
            # raise AttributeError
            
    def get_next_pages(self, response, results, target_num):
        """
        """
        while response.links.get('next'):
            try:
                self.logger.debug("Search query: %s",
                                  response.links.get("next").get("url"))
                response = self.session.get(response.links['next']['url'],
                                            headers=self.headers)
                next_result = response.json()["items"]
                results.extend(next_result)
                if len(results) >= target_num:
                    break
                # else:
                #     time.sleep(1)

            except KeyError as key_error:
                self.logger.error(
                    "Query failed...\nError: %s \nRetry in 5 seconds",
                    key_error)
                time.sleep(5)
                continue
        return results

    def query_repository(
        self,
        queried_features: List[str],
        filters: Dict[str, Any],
        updated_at_filt: bool = False,
        repo_list: List[int] = []
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calls functions which perform actual query.
        :param queried_features: List with gathered features
        :return:
        """
        self.logger.info("Getting request information for feature(s): %s",
                    queried_features)
        feature_list = []  # type: list[str]
        query_dict = {}  # type: dict[str, list]

        if queried_features:
            for feature in queried_features:
                feature_list = (
                    self.query_features.get(feature).get("feature_list")
                )
                request_url_1 = (
                    self.query_features.get(feature).get("request_url_1")
                )
                request_url_2 = (
                    self.query_features.get(feature).get("request_url_2")
                )
                query_dict[feature] = [
                    feature_list, request_url_1, request_url_2]
        request_data_dict = {}
        for param, query in query_dict.items():
            param_list = self.get_repository_data(
                feature_list=query[0],
                request_url_1=query[1],
                request_url_2=query[2],
                filters=filters,
                repo_list=repo_list,
                updated_at_filt=updated_at_filt
            )
            request_data_dict[param] = param_list
            time.sleep(600)
        return request_data_dict

    def get_single_object(self,
                          feature: str,
                          filters: Dict[str, Any],
                          output_format: str
                          ) -> Dict[int,
                                    List[Dict[int,
                                              List[Dict[str,
                                                        Any]]]]]:
        """
        Function to retrieve issues and the comments for each.
        Note: Issues also contain pull requests.
        :param feature: Feature that is to be queried (e.g. commits)
        :return: A dictionary with the repository id,
        its issue ids and the comments per issue.
        """
        request_url_1 = self.query_features.get(
            feature).get("request_url_1")
        request_url_2 = self.query_features.get(
            feature).get("request_url_2")
        request_url_3 = self.query_features.get(
            feature).get("request_url_3")
        self.logger.info("Starting query for repository request...")
        # objects_per_repo = []  # objects_per_repo type: List[Dict[str, Any]]
        objects_per_repo = self.query_repository(
            queried_features=[feature], filters=filters).get(
            feature
        )  # Object e.g. issue or commit
        self.logger.info("Finished query for repository request.")
        object_key = self.query_features.get(feature).get("feature_key")
        single_object_dict = {}
        subfeature_list = self.query_features.get(
            feature).get("subfeature_list")
        if objects_per_repo:
            for repo_num, repository in enumerate(objects_per_repo, start=1):
                if repo_num % 100 == 0:
                    self.logger.info("Getting repo Nr. %s of %s",
                                     repo_num, len(objects_per_repo))
                if output_format.lower() == "dict":
                    object_storage = {}
                else:
                    object_storage = []
                url = request_url_1 + str(repository) + request_url_2
                objects = objects_per_repo.get(repository)
                object_counter = 0
                for obj in objects:
                    object_counter += 1
                    if object_counter % 100 == 0:
                        self.logger.info(
                            "Get object Nr. %s of %s", object_counter, len(objects))
                    object_id = obj.get(object_key)
                    if object_id:
                        comment_dict = utils.get_subfeatures(
                            session=self.session,
                            headers=self.headers,
                            features=subfeature_list,
                            object_id=object_id,
                            object_url=url,
                            sub_url=request_url_3,
                        )
                    else:
                        comment_dict = {}
                    if output_format == "list":
                        object_storage.append(comment_dict)
                    else:
                        object_storage.update(comment_dict)
                single_object_dict[repository] = object_storage
                # time.sleep(1)
        else:
            single_object_dict = {}
        return single_object_dict

    def get_repository_data(
        self, feature_list: List[str], request_url_1: str,
        request_url_2: str, filters: Dict[str, Any],
        repo_list: List[int],
        updated_at_filt: bool = False
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Query data from repositories
        :param feature_list: Features are the information,
         which should be stored
        after querying to avoid gathering unwanted data.
        :param request_url_1: First part of the url,
        split bc. in some cases
        information such as the repository id must be in the middle of the url.
        :param request_url_2: Second part of the url,
         pointing to the GitHub API subcategory.

        :return: Repository data of the selected features.
        """
        repository_dict = {}
        results = {}
        filter_str = ""
        if filters:
            for key, value in filters.items():
                filter_str = filter_str + key + "=" + value + "&"
        self.logger.info(
            "Getting repository data of %s repositories",
            len(self.selected_repos_dict)
        )
        if repo_list:
            # repositories = repo_list
            repositories = [repo for repo in repo_list if repo is not None]
        else:
            repositories = self.selected_repos_dict
        one_year_ago = self.today - relativedelta.relativedelta(years=1)
        for repo_num, repo_id in enumerate(repositories, start=1):
            if repo_num % 100 == 0:
                self.logger.info("Getting repo Nr. %s of %s",
                        repo_num, len(repositories))
            complete_results = False
            while not complete_results:
                self.logger.info("Getting repository %s", repo_id)
                if request_url_2:
                    url_repo = str(request_url_1 + str(repo_id) + request_url_2)
                else:
                    url_repo = str(request_url_1 + str(repo_id))
                self.logger.info("Getting page 1")
                start_url = (str(url_repo) +
                             "?simple=yes&" +
                             str(filter_str) +
                             "per_page=" +
                             str(self.results_per_page) +
                             "&page=1"
                            )
                self.logger.info("Start URL: %s", start_url)
                try:
                    response = self.session.get(
                        start_url, headers=self.headers, timeout=100)
                    if response.status_code in [403, 429]:
                        self.logger.critical("Status code: %s", response.status_code)
                        self.check_rate_limit(response=response)
                    elif response in [400, 401, 404, 406, 410]:
                        self.logger.critical("Status code: %s", response.status_code)
                        self.logger.error("Query for repo %s failed: %s",
                                          repo_id, response)
                        break
                    elif response.status_code in [500, 502, 503, 504]:
                        self.logger.critical("Status code: %s", response.status_code)
                        self.logger.debug("Connection failed at repo %s:%s",
                                          repo_id, response)
                        raise ConnectionError
                    if response.links.get("last"):
                        nr_of_pages = (
                            response.links.get(
                                "last").get("url").split("&page=", 1)[1]
                                )
                    else:
                        nr_of_pages = 1
                    self.logger.info("Querying total pages: %s", nr_of_pages)
                    results = response.json()
                    if response.status_code == 200 and nr_of_pages == 1:
                        complete_results = True
                        continue

                    if response.links.get('next'):
                        while response.links.get('next'):
                            try:
                                self.logger.debug("Search query: %s",
                                                  response.links.get(
                                                    "next").get("url"))
                                response = self.session.get(
                                    response.links['next']['url'],
                                    headers=self.headers)
                                if response.status_code in [403, 429]:
                                    self.check_rate_limit(response=response)
                                elif response.status_code in [400, 401,
                                                              404, 406, 410]:
                                    self.logger.error(
                                        "Query repo %s failed:%s",
                                        repo_id, response)
                                    break
                                elif response.status_code in [500, 502,
                                                              503, 504]:
                                    self.logger.debug(
                                        "Connection failed at repo %s:%s",
                                        repo_id, response)
                                    raise ConnectionError
                                next_result = response.json()
                                results.extend(next_result)
                                if updated_at_filt:
                                    updated_at = next_result[-1].get(
                                        "updated_at")
                                    upd_datetime = datetime.strptime(
                                        updated_at,
                                        '%Y-%m-%dT%H:%M:%SZ')
                                    if one_year_ago > upd_datetime:
                                        complete_results = True
                                        break
                                    
                                # time.sleep(1)
                            except Exception:
                                self.logger.error(
                                    "Error at querying all pages...")
                                time.sleep(10)
                        complete_results = True
                        continue

                except Exception as repo_error:
                    self.logger.error(
                        "Could not query Repo:%s\nError: %s",
                        repo_id, repo_error)
                    self.logger.debug("Could not query results from Repo: %s \
                                      ...Retry in 5 minutes.", repo_id)
                    # failed_repo_id = repo_id
                    complete_results = False
                    time.sleep(10)
            # time.sleep(1)
            self.logger.info("Finished getting responses for all queries.")
            element_list = []  # element_list type: List[Dict[str, Any]]
            if isinstance(results, list):
                for element in results:
                    element_dict = {}  # element_dict type: Dict[str, Any]
                    if updated_at_filt:
                        updated_at = element.get("updated_at")
                        upd_datetime = datetime.strptime(
                            updated_at,
                            '%Y-%m-%dT%H:%M:%SZ')
                        if one_year_ago > upd_datetime:
                            continue
                    for feature in feature_list:
                        try:
                            element_dict[feature] = element.get(feature)
                        except AttributeError as att_error:
                            self.logger.error(
                                "Encountered Attribute Error %s \
                                    /n At feature %s /n At element %s",
                                    att_error, feature, element)
                        continue
                    element_list.append(element_dict)

            elif isinstance(results, dict):
                element_dict = {}  # element_dict type: Dict[str, Any]
                for feature in feature_list:
                    element_dict[feature] = results.get(feature)
                element_list = element_dict  # [element_dict]
            repository_dict[repo_id] = element_list

        self.logger.info("Done getting repository data.")
        return repository_dict

    def get_dependents(self, dependents_details: bool) -> Dict[int, int]:
        """
        Get dependencies of a repository
        :param keyword: Keyword to select either dependents or dependencies
        :return: Repository ids and the number of dependents or dependencies
        """
        dependents_results = {}
        repositories = self.selected_repos_dict.items()
        for repo_num, (repo, data) in enumerate(repositories, start=1):
            if repo_num % 100 == 0:
                self.logger.info("Getting repo Nr. %s of %s",
                                 repo_num,
                                 len(repositories))
            repo_name = data.get("name")
            repo_owner_login = data.get("owner").get("login")
            self.logger.info("Getting repository %s", repo)
            url_1 = self.query_features.get("dependents").get("request_url_1")
            url_2 = self.query_features.get("dependents").get("request_url_2")
            url = url_1 + str(repo_owner_login) + "/" + str(repo_name) + url_2
            nextExists = True
            result_cnt = 500000
            total_dependents = 0
            visible_dependents = []
            menu = None
            for run in range(3):
                response = self.session.get(url)
                soup = BeautifulSoup(response.content, "html.parser")
                dependents_box = soup.find("div", {"id": "dependents"})
                if dependents_box:
                    menu = dependents_box.select(
                        "details",
                        {"class":
                        "select-menu.float-right.position-relative.details-reset.details-overlay"})
                    break
                else:
                    self.logger.error("""
                                      Could not find dependency
                                      box at %s try.
                                      Retry in 1 minute.
                                      """, run + 1)
                    time.sleep(10)
                    continue
            if menu:
                options = menu[0].find_all(
                    "div", {"class": "select-menu-list"})
                if options:
                    for row in options[0].find_all("a", href=True):
                        time.sleep(1)
                        href = re.search(
                            "href=\"(.+?)\"\s",
                            str(row)).group(1)
                        pattern = "dependents?"
                        href_split = href.replace(pattern,
                                                  f" {pattern} ").split(" ")
                        href_url = (url_1 +
                                    href_split[0] +
                                    href_split[1] +
                                    "dependent_type=REPOSITORY&" +
                                    href_split[2])
                        tmp_href_response = self.session.get(
                                    href_url)
                        tmp_href_soup = BeautifulSoup(
                                    tmp_href_response.content,
                                    "html.parser")
                        box = tmp_href_soup.find(
                                    "a", {"class": "btn-link selected"}
                                    ).text
                        total_dependents += int(
                            box.strip().split(" ")[0].replace(",", ""))
                        if dependents_details:
                            while (nextExists
                                   and len(visible_dependents) <
                                   result_cnt):
                                try:
                                    href_response = self.session.get(
                                        href_url)
                                    href_soup = BeautifulSoup(
                                        href_response.content,
                                        "html.parser")
                                    dependents_box = href_soup.find(
                                        "div", {"id": "dependents"})
                                    if not dependents_box:
                                        break
                                    dependents = dependents_box.find("div", {"class": "Box"})
                                    dependents_elements = dependents.find_all(
                                        "div", {"class": "Box-row d-flex flex-items-center",
                                                "data-test-id": "dg-repo-pkg-dependent"})
                                    if dependents_elements:
                                        for element in dependents_elements:
                                            cell = element.find(
                                                "span", {"class": "f5 color-fg-muted"})
                                            try:
                                                user = cell.find(
                                                    "a", {"data-hovercard-type": "user"}).text
                                            except AttributeError:
                                                user = cell.find("a", {"data-hovercard-type": "organization"}).text
                                            repository = element.find(
                                                "a", {"class": "text-bold", "data-hovercard-type": "repository"}).text
                                            visible_dependents.append([user, repository])
                                    else:
                                        break
                                    try:
                                        selector = dependents_box.find(
                                            "div", {"class": "BtnGroup"})
                                        for u in selector:
                                            if u.text == "Next":
                                                nextExists = True
                                                href_url = u["href"]
                                            else:
                                                nextExists = False
                                            
                                    except Exception as href_info:
                                        self.logger.info(href_info)
                                        time.sleep(1)
                                        nextExists = True
                                        break
                                except requests.exceptions.ConnectionError:
                                    continue
                            
            dependents_results[repo] = {"total_dependents":
                                        total_dependents,
                                        "visible_dependents":
                                        visible_dependents}
        return dependents_results

    def get_dependencies(self) -> Dict[int, int]:
        """
        NOTE: Dependency graph from GitHub is still in progress!
        Changes in near future can cause errors!
        Get dependencies of a repository.
        :return: Repository ids and the number of dependencies
        """
        dependency_results = {}
        repositories = self.selected_repos_dict.items()
        for repo_num, (repo, data) in enumerate(repositories, start=1):
            if repo_num % 100 == 0:
                self.logger.info("Getting repo Nr. %s of %s",
                                 repo_num,
                                 len(repositories))
            repo_name = data.get("name")
            repo_owner_login = data.get("owner").get("login")
            self.logger.info("Getting repository %s", repo)
            url_1 = self.query_features.get(
                "dependencies").get("request_url_1")
            url_2 = self.query_features.get(
                "dependencies").get("request_url_2")
            url = url_1 + str(repo_owner_login) + "/" + str(repo_name) + url_2
            self.logger.debug("Getting url: %s", url)
            nextExists = True
            result_cnt = 500000
            results = set()
            dependencies = None
            while nextExists and len(results) < result_cnt:
                for run in range(3):
                    try:
                        response = self.session.get(url)
                        soup = BeautifulSoup(response.content, "html.parser")
                        dependencies_box = soup.find(
                            "div", {"id": "dependencies"})
                        dependencies = dependencies_box.find(
                            "div", {"class": "Box", "data-view-component": "true"})
                        if dependencies_box:
                            break
                        else:
                            self.logger.error("""
                                            Could not find dependency
                                            box at %s try.
                                            Retry in 1 minute.
                                            """, run + 1)
                            time.sleep(10)
                            continue
                    except AttributeError:
                        self.logger.error(
                            "Attribute Error at repo_num %s, repo_id = %s",
                            repo_num, repo)
                if dependencies:
                    for element in dependencies.find_all(
                        "li", {"class": "Box-row",
                               "data-view-component": "true"}):
                        time.sleep(1)
                        try:
                            text = element.find(
                                "a", {"class": "h4 Link--primary no-underline"}
                                ).text.strip()
                        except AttributeError:
                            text = element.find(
                                "div", {"class": "d-flex flex-items-baseline"}
                                ).text.strip()
                        results.add(text)
                else:
                    self.logger.debug("No dependencies for repo %s",
                                      repo)
                    break
                nextExists = False
                try:
                    for u in soup.find(
                        "div",
                        {"class": "paginate-container"}).find_all('a'):
                        if u.text == "Next":
                            nextExists = True
                            url = url_1 + u["href"]
                except Exception as href_info:
                    self.logger.info(href_info)
                    time.sleep(1)
                    nextExists = True
            dependency_results[repo] = sorted(results)  # len(results)
        return dependency_results
    
    def get_branches(self, activity: str = "all") -> Dict[int, Dict[str, str]]:
        """
        NOTE: Dependency graph from GitHub is still in progress!
        Changes in near future can cause errors!
        Get dependencies of a repository.
        :return: Repository ids and the number of dependencies
        """
        branches_results = {}
        repositories = self.selected_repos_dict.items()
        for repo_num, (repo, data) in enumerate(repositories, start=1):
            if repo_num % 100 == 0:
                self.logger.info("Getting repo Nr. %s of %s",
                                 repo_num,
                                 len(repositories))
            repo_name = data.get("name")
            repo_owner_login = data.get("owner").get("login")
            self.logger.info("Getting repository %s", repo)
            url_1 = "https://github.com/"
            url_2 = "/branches"
            url = (url_1 +
                    str(repo_owner_login) +
                    "/" +
                    str(repo_name) +
                    url_2 +
                    ("/") +
                    activity
                    )
            nextExists = True
            result_cnt = 500000
            results = {}
            while nextExists and len(results) < result_cnt:
                response = self.session.get(url)
                soup = BeautifulSoup(response.content, "html.parser")
                all_branches = soup.find("div", {"data-target": "branch-filter.result"})
                time.sleep(1)
                if all_branches:
                    for element in all_branches.find_all("li", {"class": "Box-row position-relative"}):
                        branch_name = ""
                        branch_status = ""
                        element = element.find("branch-filter-item")
                        try:
                            branch_name = element.select('a[class*="branch-name"]')[0].text
                            if element.select('span[class*="State State"]'):
                                branch_status = element.select('span[class*="State State"]')[0].text.strip()
                            elif element.select('a[class*="btn "]'):
                                branch_status = element.select('a[class*="btn "]')[0].text.strip()
                            else:
                                branch_status = ""
                        except AttributeError:
                            self.logger.error(AttributeError)
                        results[branch_name] = branch_status
                else:
                    break
                nextExists = False
                try:
                    for u in soup.find(
                        "div", {"class": "paginate-container"}).find_all('a'):
                        if u.text == "Next":
                            nextExists = True
                            url = u["href"]
                except Exception as href_info:
                    self.logger.info(href_info)
                    time.sleep(1)
                    nextExists = True
            branches_results[repo] = results  # len(results)
            time.sleep(1)
        return branches_results

    def get_context_information(self, main_feature: str,
                                sub_feature: str, filters: Dict[str, Any]
                                ) -> Dict[int, List[Dict[str, Any]]]:
        """
        :param main_feature: Feature which concerns the main information.
        :param sub_feature: Feature which concerns the context information.
        :return: Dictionary with context information of main feature.
        """
        main_data = self.query_repository([main_feature], filters=filters)
        request_url_1 = self.query_features.get(
            sub_feature).get("request_url_1")
        request_url_2 = self.query_features.get(
            sub_feature).get("request_url_2")
        feature_list = self.query_features.get(
            sub_feature).get("feature_list")
        feature_key = self.query_features.get(
            sub_feature).get("feature_key")
        return_data = {}
        repositories = main_data.get(main_feature).items()
        for repo_num, (repo, data) in enumerate(repositories, start=1):
            if repo_num % 100 == 0:
                self.logger.info("Getting repo Nr. %s of %s",
                                 repo_num,
                                 len(repositories))
            data_list = []
            for element in data:
                element_dict = {}
                key = element.get(feature_key)
                element_url = request_url_1 + str(key) + request_url_2
                result = self.session.get(
                            element_url, headers=self.headers, timeout=100)
                sub_data = result.json()
                for feature in feature_list:
                    if isinstance(sub_data, dict):
                        element_dict[feature] = sub_data.get(feature)
                    else:
                        element_dict[feature] = sub_data
                data_list.append(element_dict)
            return_data[repo] = data_list
            time.sleep(1)
        return return_data

        
    def __del__(self):
        self.session.close()




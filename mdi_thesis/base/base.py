"""
mdi_thesis base module.

If you want to replace this with a Flask application run:

    $ make init

and then choose `flask` as template.
"""
# from datetime import date
import json
import time
from bs4 import BeautifulSoup
from typing import Dict, List, Any
import requests
import mdi_thesis.constants as constants
import mdi_thesis.base.utils as utils
import logging
import os
import base64
import re


logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s %(name)-12s %(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.ERROR)


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
        sub_results = {}

    def select_repos(
        self,
        repo_nr: int,
        repo_list: List[int],
        language: str = "python",
        sort: str = "stars",
        order: str = "desc",
        help_wanted_issues: str = "True",
        
    ) -> List[Dict[str, Any]]:
        """
        Select Repositories according to Parameters
        :param repo_nr: Number of queried repositories.
        :param language: Programming language of queried repositories.
        :param sort: Factor by which the repositories are sorted.
        :param repo_list: List with repositories if preselected
        :returns: List with dictionaries of selected repositories
        """
        selected_repos = []
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

        else:
            search_url = (
                "https://api.github.com/search/repositories?q=language:"
                + language
                + "&sort="
                + sort
                + "&order="
                + order
                + "&help-wanted-issues="
                + help_wanted_issues
                + "&access_token="
                + self.token
                + "?per_page="  # "?simple=yes&per_page="
                + str(self.results_per_page)
                + "&page=1"
            )
            repo_nr_queried = 0
            response = self.session.get(
                search_url, headers=self.headers, timeout=100)
            results = response.json()
            try:
                results_items = results["items"]
            except Exception as err:
                logger.error("Unexpected %s, %s", err, type(err))
                logger.debug("Error raised at data result: %s", results)
                raise
            
            if "last" in response.links:
                # nr_of_pages = response.links.get(
                #     "last").get("url").split("&page=", 1)[1]
                nr_of_pages = round(repo_nr/self.results_per_page)
                if results:
                    if int(nr_of_pages) > 1 and repo_nr_queried < repo_nr:
                        repo_nr_queried += self.results_per_page
                        for page in range(2, int(nr_of_pages) + 1):
                            url_repo = (
                                f"{search_url}?simple=yes"
                                f"&per_page=100&page={page}"
                            )
                            res = self.session.get(
                                url_repo, headers=self.headers, timeout=100)
                            logger.info("Query page %s of %s",
                                        page, nr_of_pages)
                            logging.info("Extending results...")
                            try:
                                if "items" in res.json():
                                    next_res = res.json()["items"]
                                    results_items.extend(next_res)
                            except Exception as error:
                                logger.error(
                                    "Could not extend: %s...\nError: %s",
                                    res.json(), error)

            selected_repos = results_items[:repo_nr]
        self.selected_repos_dict = utils.clean_results(
            selected_repos)

        return selected_repos

    def query_repository(
        self,
        queried_features: List[str],
        filters: Dict[str, Any],
        repo_list: List[int] = []
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calls functions which perform actual query.
        :param queried_features: List with gathered features
        :return:
        """
        logger.info("Getting request information for feature(s): %s",
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
                repo_list=repo_list
            )
            request_data_dict[param] = param_list
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
        logger.info("Starting query for repository request...")
        objects_per_repo = []  # objects_per_repo type: List[Dict[str, Any]]
        objects_per_repo = self.query_repository(
            queried_features=[feature], filters=filters).get(
            feature
        )  # Object e.g. issue or commit
        logger.info("Finished query for repository request.")
        object_key = self.query_features.get(feature).get("feature_key")
        single_object_dict = {}
        subfeature_list = self.query_features.get(
            feature).get("subfeature_list")
        for repository in objects_per_repo:
            if output_format.lower() == "dict":
                object_storage = {}
            else:
                object_storage = []
            url = request_url_1 + str(repository) + request_url_2
            objects = objects_per_repo.get(repository)
            object_counter = 0
            for obj in objects:
                object_counter += 1
                logger.info(
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
        return single_object_dict

    def get_repository_data(
        self, feature_list: List[str], request_url_1: str,
        request_url_2: str, filters: Dict[str, Any],
        repo_list: List[int]
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
        filter_str = ""
        if filters:
            for key, value in filters.items():
                filter_str = filter_str + key + "=" + value + "&"
        logger.info(
            "Getting repository data of %s repositories",
            len(self.selected_repos_dict)
        )
        if repo_list:
            repositories = repo_list
        else:
            repositories = self.selected_repos_dict

        for repo_id in repositories:
            logger.info("Getting repository %s", repo_id)
            if request_url_2:
                url_repo = str(request_url_1 + str(repo_id) + request_url_2)
            else:
                url_repo = str(request_url_1 + str(repo_id))
            logger.info("Getting page 1")
            start_url = (str(url_repo) +
                         "?simple=yes&" +
                         str(filter_str) +
                         "per_page=" +
                         str(self.results_per_page) +
                         "&page=1"
                         )
            response = self.session.get(
                start_url, headers=self.headers, timeout=100)
            results = response.json()

            if "last" in response.links:
                nr_of_pages = (
                    response.links.get("last").get("url").split("&page=", 1)[1]
                )

                if int(nr_of_pages) > 1:
                    logger.info("Getting responses for all pages...")
                    for page in range(2, int(nr_of_pages) + 1):
                        logger.info("Query page %s of %s", page, nr_of_pages)
                        url = (str(url_repo) +
                               "?simple=yes&" +
                               str(filter_str) +
                               "per_page=" +
                               str(self.results_per_page) +
                               "&page=" +
                               str(page))
                        res = self.session.get(
                            url, headers=self.headers, timeout=100)
                        logging.info("Extending results...")
                        try:
                            results.extend(res.json())
                        except Exception as error:
                            logger.info(
                                "Could not extend data: %s:%s",
                                res.json(), error)

            logger.info("Finished getting responses for all queries.")
            element_list = []  # element_list type: List[Dict[str, Any]]
            if isinstance(results, list):
                for element in results:
                    element_dict = {}  # element_dict type: Dict[str, Any]
                    for feature in feature_list:
                        try:
                            element_dict[feature] = element.get(feature)
                        except AttributeError as att_error:
                            logger.error("Encountered Attribute Error %s \
                                         /n At feature %s /n At element %s",
                                         att_error, feature, element)
                        continue
                    element_list.append(element_dict)

            elif isinstance(results, dict):
                element_dict = {}  # element_dict type: Dict[str, Any]
                for feature in feature_list:
                    element_dict[feature] = results.get(feature)
                element_list = [element_dict]
            repository_dict[repo_id] = element_list
        logger.info("Done getting repository data.")
        return repository_dict

    def get_dependents(self, dependents_details: bool) -> Dict[int, int]:
        """
        Get dependencies of a repository
        :param keyword: Keyword to select either dependents or dependencies
        :return: Repository ids and the number of dependents or dependencies
        """
        dependents_results = {}
        for repo, data in self.selected_repos_dict.items():
            repo_name = data.get("name")
            repo_owner_login = data.get("owner").get("login")
            logger.info("Getting repository %s", repo)
            url_1 = self.query_features.get("dependents").get("request_url_1")
            url_2 = self.query_features.get("dependents").get("request_url_2")
            url = url_1 + str(repo_owner_login) + "/" + str(repo_name) + url_2
            nextExists = True
            result_cnt = 500000
            total_dependents = 0
            visible_dependents = []
            response = self.session.get(url)
            soup = BeautifulSoup(response.content, "html.parser")
            dependents_box = soup.find("div", {"id": "dependents"})
            menu = dependents_box.select(
                "details",
                {"class": "select-menu.float-right.position-relative.details-reset.details-overlay"})
            if menu:
                options = menu[0].find_all(
                    "div", {"class": "select-menu-list"})
                if options:
                    for row in options[0].find_all("a", href=True):
                        href = re.search(
                            "href=\"(.+?)\"\s",
                            str(row)).group(1)
                        pattern = "dependents?"
                        href_split = href.replace(pattern, f" {pattern} ").split(" ")
                        href_url = url_1 + href_split[0] + href_split[1] + "dependent_type=REPOSITORY&" + href_split[2]
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
                            while nextExists and len(visible_dependents) < result_cnt:
                                try:
                                    href_response = self.session.get(
                                        href_url)
                                    href_soup = BeautifulSoup(
                                        href_response.content,
                                        "html.parser")
                                    dependents_box = href_soup.find("div", {"id": "dependents"})
                                    if not dependents_box:
                                        break
                                    dependents = dependents_box.find("div", {"class": "Box"})
                                    dependents_elements = dependents.find_all("div", {"class": "Box-row d-flex flex-items-center", "data-test-id": "dg-repo-pkg-dependent"})
                                    if dependents_elements:
                                        for element in dependents_elements:
                                            # print(element)
                                            cell = element.find("span", {"class": "f5 color-fg-muted"})
                                            # print(test)
                                            try:
                                                user = cell.find("a", {"data-hovercard-type": "user"}).text
                                            except AttributeError:
                                                user = cell.find("a", {"data-hovercard-type": "organization"}).text
                                            repository = element.find("a", {"class": "text-bold", "data-hovercard-type": "repository"}).text
                                            visible_dependents.append([user, repository])
                                    else:
                                        break
                                    try:
                                        selector = dependents_box.find(
                                            "div", {"class": "BtnGroup"})# .find_all('a')
                                        for u in selector:
                                            if u.text == "Next":
                                                nextExists = True
                                                href_url = u["href"]
                                            else:
                                                nextExists = False
                                            
                                    except Exception as href_info:
                                        logger.info(href_info)
                                        time.sleep(2)
                                        nextExists = True
                                        break
                                except requests.exceptions.ConnectionError:
                                    continue
            
            dependents_results[repo] = {"total_dependents": total_dependents,
                                        "visible_dependents": visible_dependents}
        return dependents_results


    def get_dependencies(self) -> Dict[int, int]:
        """
        NOTE: Dependency graph from GitHub is still in progress!
        Changes in near future can cause errors!
        Get dependencies of a repository.
        :return: Repository ids and the number of dependencies
        """
        dependency_results = {}
        for repo, data in self.selected_repos_dict.items():
            repo_name = data.get("name")
            repo_owner_login = data.get("owner").get("login")
            logger.info("Getting repository %s", repo)
            url_1 = self.query_features.get("dependencies").get("request_url_1")
            url_2 = self.query_features.get("dependencies").get("request_url_2")
            url = url_1 + str(repo_owner_login) + "/" + str(repo_name) + url_2
            nextExists = True
            result_cnt = 500000
            results = set()
            while nextExists and len(results) < result_cnt:
                response = self.session.get(url)
                soup = BeautifulSoup(response.content, "html.parser")
                dependencies_box = soup.find("div", {"id": "dependencies"})
                dependencies = dependencies_box.find("div", {"class": "Box", "data-view-component": "true"})
                if dependencies:
                    print(repo)
                    for element in dependencies.find_all("li", {"class": "Box-row", "data-view-component": "true"}):
                        # print(element)
                        try:
                            text = element.find("a", {"class": "h4 Link--primary no-underline"}).text.strip()
                        except AttributeError:
                            text = element.find("div", {"class": "d-flex flex-items-baseline"}).text.strip()
                        results.add(text)
                else:
                    break
                nextExists = False
                try:
                    for u in soup.find(
                        "div", {"class": "paginate-container"}).find_all('a'):
                        if u.text == "Next":
                            nextExists = True
                            url = url_1 + u["href"]
                except Exception as href_info:
                    logger.info(href_info)
                    time.sleep(2)
                    nextExists = True
            dependency_results[repo] = sorted(results)  # len(results)
            # for element in results:
            #    print(element["name"] + ", " + str(element["stars"]))
        return dependency_results

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
        request_url_3 = self.query_features.get(
            sub_feature).get("request_url_3")
        feature_list = self.query_features.get(
            sub_feature).get("feature_list")
        feature_key = self.query_features.get(
            sub_feature).get("feature_key")
        return_data = {}
        for repository, data in main_data.get(main_feature).items():
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
            return_data[repository] = data_list
        return return_data

    def get_dependency_packages(self):
        """
        Get dependencies from the requirements.txt file.
        If no file is found, the setup.py file is retrieved.
        """
        request_url_1 = (
            self.query_features.get("dependencies_alt").get("request_url_1")
        )
        request_url_2 = (
            self.query_features.get("dependencies_alt").get("request_url_2")
        )
        request_url_3 = (
            self.query_features.get("dependencies_alt").get("request_url_3")
        )
        dependency_dict = {}
        encoding = "utf-8"
        for repo_id in self.selected_repos_dict:
            dependency_packages = []
            url = request_url_1 + str(repo_id) + request_url_2
            response = self.session.get(url, headers=self.headers, timeout=100)
            if response.status_code == 200:
                content_data = response.json()
                encoded_content = content_data['content']
                requirements_content = base64.b64decode(
                    encoded_content).decode(
                    encoding)

                dependencies = requirements_content.split("\n")
                dependency_packages = [dependency.strip()
                                       for dependency in dependencies
                                       if dependency.strip()]
            else:
                logger.info("Failed to fetch requirements.txt file: %s",
                            response.status_code)
                url = request_url_1 + str(repo_id) + request_url_3
                response = self.session.get(url,
                                            headers=self.headers,
                                            timeout=100)
                if response.status_code == 200:
                    content_data = response.json()
                    encoded_content = content_data['content']
                    requirements_content = base64.b64decode(
                        encoded_content).decode(
                        encoding)
                    dependencies = re.findall(r"install_requires\s*=\s*\[([^\]]+)\]",
                                              requirements_content)
                    if not dependencies:
                        dependencies = re.findall(r"requirements\s*=\s*\[([^\]]+)\]",
                                                  requirements_content)
                    if dependencies:
                        dependencies = dependencies[0].replace(
                            "'", "").replace(
                            '"', "").split(
                            ",")
                        dependency_packages = [dependency.strip()
                                               for dependency in dependencies
                                               if dependency != ""]
            dependency_dict[repo_id] = dependency_packages

        return dependency_dict


#    def __del__(self):
#       self.session.close()

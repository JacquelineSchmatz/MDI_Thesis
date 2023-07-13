"""
Modle for imports from other sources than GitHub
"""
import requests
from bs4 import BeautifulSoup

def get_osi_json():
    """
    Use licenseId to check for matching entries
    with retrieved data from GitHub to check,
    if license is OSI approved (isOsiApproved)
    """
    url = ("https://raw.githubusercontent.com/" +
    "spdx/license-list-data/master/json/licenses.json")
    response = requests.get(url, timeout=100)
    results_dict = response.json().get("licenses")
    return results_dict


def get_nvds(cve_id: str):
    """
    :param cve_id: CVE id, used to find the cve in the nvd database.
                   e.g. CVE-2022-35920
    :return: base score from NVD or None, if nothing was found
    """
    url = "https://nvd.nist.gov/vuln/detail/" + cve_id
    score = None
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        severity_box = soup.find("div", {"id": "Vuln3CvssPanel"})
        # print(severity_box)
        for row in severity_box.find_all("div", {"class": "row no-gutters"}):
            if row.find("span", {"class": "wrapData"}).text == "NVD":
                base_score = severity_box.find("span", {"class": "severityDetail"}).text
                score = float(base_score.split()[0])
    except:
        score = None
    return score


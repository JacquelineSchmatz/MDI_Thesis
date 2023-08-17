"""
Metrics pipeline

Author: Jacqueline Schmatz
Description: Calculates all metrics
"""

# Imports
import json
import os
import sys
import inspect
from typing import Dict, List, Any, Union
from datetime import date, datetime
from dateutil import relativedelta
import mdi_thesis.base.base as base
import mdi_thesis.base.utils as utils
import mdi_thesis.metrics as metrics


class MetricsPipeline():
    """
    Pipeline which reads data, calculates metrics and stores the
    results in json files.
    """
    def __init__(self, filter_date: date):
        self.logger = base.get_logger(__name__)
        self.results_dict = {}
        self.languages = []
        self.data_dict = self.read_json()
        self.filter_date = filter_date
        metrics_objective_mapping = open(
            "mdi_thesis/metrics_data_mapping.json", encoding="utf-8")
        self.metrics_objective_mapping = json.load(metrics_objective_mapping)

        parent_dir = os.path.abspath('.')
        if parent_dir not in sys.path:
            sys.path.append(parent_dir)
        self.output_path = os.path.join(parent_dir, "outputs", "results")

    def read_json(self):
        """
        Reads all json files returned by base_data_miner.py
        Stores results in dictionary by objective and language.
        """
        parent_dir = os.path.abspath('.')
        if parent_dir not in sys.path:
            sys.path.append(parent_dir)
        combined_dict = {}
        path = os.path.join(parent_dir, "outputs", "data")
        self.logger.info("Reading json files from path %s", path)
        for filename in os.listdir(path):
            objective = filename.split(".")[0].split("_", 1)[1]
            language = filename.split("_")[0]
            self.languages.append(language)
            file_path = os.path.join(path, filename)
            tmp_dict = utils.json_to_dict(path=file_path)
            lang_dict = {}
            lang_dict[language] = tmp_dict
            if objective in combined_dict:
                combined_dict[objective].update(lang_dict)
            else:
                combined_dict[objective] = lang_dict
        return combined_dict

    def filter_data(self, data: Dict,
                    filter_parameter: str,
                    filter_period: date):
        """
        Filters data according to parameter.
        :param data: Data to be filtered
        :param filter_parameter: Parameter of GitHub object
        on which the filter is applied.
        :param filter_period: Filter period for which the object
        is filtered.
        """
        self.logger.info("Filtering data by Parameter: %s and Period %s",
                         filter_parameter, filter_period)
        filtered_data = {}
        for repo, content in data.items():
            content_filt = None
            if isinstance(content, List):
                content_filt = []
                for element in content:
                    element_date = element.get(filter_parameter)
                    if element_date:
                        filter_date = (
                            self.filter_date -
                            relativedelta.relativedelta(filter_period))
                        filter_date = filter_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                        if filter_date > element_date:
                            content_filt.append(element)
                
            if isinstance(content, Dict):
                content_filt = {}
                for element_id, element in content.items():
                    if isinstance(element, Dict):
                        element_date = element.get(filter_parameter)
                        if element_date:
                            element_date = datetime.strptime(
                                element_date, '%Y-%m-%dT%H:%M:%SZ').date()
                            filter_date = (
                                self.filter_date -
                                relativedelta.relativedelta(
                                    filter_period))
                            if filter_date > element_date:
                                content_filt[element_id] = element
                    elif isinstance(element, List):
                        for elem in element:
                            element_date = elem.get(filter_parameter)
                            if element_date:
                                element_date = datetime.strptime(
                                    element_date, '%Y-%m-%dT%H:%M:%SZ').date()
                                filter_date = (
                                    self.filter_date -
                                    relativedelta.relativedelta(
                                        filter_period))
                                if filter_date > element_date:
                                    content_filt[element_id] = element

            filtered_data[repo] = content_filt
        return filtered_data

    def prep_data(self, language: str,
                  objectives: Dict):
        """
        Collects required data of one language and multiple objectives.
        :param language: Programming language
        :param objectives: List with required objectives.
        """
        self.logger.info("Data Preparation of language %s",
                         language)
        prep_data = {}
        for objective, filters in objectives.items():
            objective_dict = self.data_dict.get(objective)
            data_dict = {}
            if objective_dict:
                data_dict = objective_dict.get(language)
                if data_dict:
                    if filters:
                        param = filters[0]
                        period = filters[1]
                        self.logger.debug(
                            "Filtering objective %s for language %s",
                            objective, language)
                        filtered_data = self.filter_data(
                            data=data_dict,
                            filter_parameter=param,
                            filter_period=period)
                        prep_data[objective] = filtered_data
                    else:
                        prep_data[objective] = data_dict
        return prep_data

    def run_metrics_to_json(self):
        """
        Run metric functions and store results in json files.
        """
        self.logger.info("Starting calculating metrics to json files.")
        for lang in self.languages:
            metrics_results = {}
            for metric, objectives in self.metrics_objective_mapping.items():
                try:
                    data = self.prep_data(language=lang, objectives=objectives)
                    function_path = getattr(metrics, metric)
                    function_args = str(inspect.signature(function_path))
                    metric_return = {}
                    if data:
                        if "filter_date" in function_args:
                            metric_return = function_path(
                                base_data=data,
                                filter_date=self.filter_date)
                        else:
                            metric_return = function_path(base_data=data)

                    metrics_results[metric] = metric_return
                except AttributeError:
                    continue
            utils.dict_to_json(data=metrics_results,
                               data_path=self.output_path,
                               feature=lang + "_metrics.json"
                               )
            self.results_dict[lang] = metrics_results


def run_pipeline(start_date: date):
    """
    Run pipeline.
    """
    pipeline = MetricsPipeline(filter_date=start_date)
    pipeline.run_metrics_to_json()


def main():
    """
    Set start for pipeline filters
    """
    start_date = date(2023, 8, 10)
    run_pipeline(start_date=start_date)


if __name__ == "__main__":
    main()

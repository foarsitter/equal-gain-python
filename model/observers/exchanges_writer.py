import os
from typing import List

from .. import base
from ..helpers import CsvWriter
from ..observers import observer


class ExchangesWriter(observer.Observer):
    """
    There are three stages of externalities
    By exchange, by issue set and by actor
    """

    def __init__(self, observable: observer.Observable):
        super().__init__(observable)

    def _create_directory(self, repetition: int):
        if not os.path.exists("{0}/exchanges/{1}".format(self.output_directory, repetition)):
            os.makedirs("{0}/exchanges/{1}".format(self.output_directory, repetition))

        if not os.path.exists("{0}/exchanges/{1}/initial".format(self.output_directory, repetition)):
            os.makedirs("{0}/exchanges/{1}/initial".format(self.output_directory, repetition))

    def before_iterations(self, repetition):
        self._create_directory(repetition)

    def before_loop(self, iteration: int, repetition: int = None):
        """
        Writes all the possible exchanges to the filesystem
        :param iteration: 
        :param repetition:
        """

        self.model_ref.sort_exchanges()

        writer = CsvWriter.CsvWriter()
        writer.write('{0}/exchanges/{2}/initial/before.{1}.csv'.format(self.output_directory, iteration, repetition),
                     self.model_ref.exchanges)

    def after_loop(self, realized: List[base.AbstractExchange], iteration: int, repetition: int):
        """
        Writes al the executed exchanges to the filesystem
        :param repetition: 
        :param realized: 
        :param iteration:
        """
        writer = CsvWriter.CsvWriter()
        writer.write("{0}/exchanges/{2}/round.{1}.csv".format(self.output_directory, iteration + 1, repetition),
                     realized)

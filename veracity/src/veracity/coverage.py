from abc import ABC as _ABC
from enum import Enum as _Enum
from abc import abstractmethod as _abstractmethod
from typing import List as _List
import random as _random
# @todo: implement max_bins on covergroup

class Status(_Enum):
    PASSED = 0
    SKIPPED = 1
    FAILED = 2


class Coverage(_ABC):


    _group = []
    _counter = 0

    def __init__(self, name: str, bypass: bool=False):
        self._name = name
        self._bypass = bypass
        Coverage._group += [self]
        pass


    @_abstractmethod
    def to_str(self, verbose: bool) -> str:
        '''
        Convert the coverage into a string for readibility to the end-user.
        '''
        pass


    @_abstractmethod
    def cover(self, item) -> bool:
        pass


    @_abstractmethod
    def passed(self) -> bool:
        '''
        Returns `True` if the coverage met its goal.
        '''
        pass


    def log(self, verbose: bool=True) -> str:
        '''
        Convert the coverage into a string for user logging purposes. Setting `verbose` to `True`
        will provide more details in the string contents.
        '''
        label = 'Coverpoint' if issubclass(type(self), Coverpoint) else 'Covergroup'
        if verbose == False:
            return label + ": " + self._name + ': ' + self.to_str(verbose) + ' ...'+str(self.status().name)
        else:
            return label + ": " + self._name + ':' + ' ...'+str(self.status().name) + '\n    ' + self.to_str(verbose)


    def skipped(self) -> bool:
        '''
        Checks if this coverage is allowed to be bypassed during simulation due
        to an external factor making it impossible to pass.
        '''
        return self._bypass 
    

    def status(self) -> Status:
        '''
        Determine the status of the Coverage node.
        '''
        if self.skipped() == True:
            return Status.SKIPPED
        elif self.passed() == True:
            return Status.PASSED
        else:
            return Status.FAILED
        

    @staticmethod
    def all_passed(timeout: int=-1) -> bool:
        '''
        Checks if each coverage specification has met its goal.

        If a coverage specification is bypassed, it counts as meeting its
        goal. If the timeout is set to -1, it will be disabled and only return
        `True` once all cases are covered.
        '''
        # force the simulation to pass if enough checks are evaluated
        if timeout > 0 and Coverage._counter >= timeout:
            return True        
        # check every cover-node
        cov: Coverage
        for cov in Coverage._group:
            if cov.skipped() == False and cov.passed() == False:
                # increment the counter
                Coverage._counter += 1
                return False
        return True


    @staticmethod
    def report(verbose: bool=True) -> str:
        '''
        Compiles a report of the coverage statistics and details. Setting `verbose`
        to `False` will only provide minimal details to serve as a quick summary.
        '''
        contents = ''
        if verbose == True:
                contents += "Test Count: " + str(Coverage.count()) + '\n'
                contents += "Coverage: "   + str(Coverage.percent()) + ' %\n'
        cov: Coverage
        for cov in Coverage._group:
            contents += cov.log(verbose) + '\n'
        return contents
    

    @staticmethod
    def save_report(file: str):
        '''
        Writes the coverage report with verbosity to the file `file`.
        '''
        with open(file, 'w') as cf:
            cf.write(Coverage.report(True))
    

    @staticmethod
    def count() -> int:
        '''
        Returns the number of times the Coverage class has called the 'all_passed'
        function. If 'all_passed' is called once every transaction, then it gives
        a sense of how many test cases were required in order to achieve full
        coverage.
        '''
        return Coverage._counter
    

    @staticmethod
    def percent() -> float:
        '''
        Return the percent of all coverages that met their goal. Each covergroup's bin
        is tallied individually instead of tallying the covergroup as a whole.

        Coverages that have a status of `SKIPPED` are not included in the tally.

        Returns `None` if there are no coverages to tally. The percent value is
        from 0.00 to 100.00 percent, with rounding to 2 decimal places.
        '''
        total_covers = 0
        covers_passed = 0
        cov: Coverage
        for cov in Coverage._group:
            if cov.status() == Status.SKIPPED:
                continue
            total_covers += 1
            if cov.status() == Status.PASSED:
                covers_passed += 1
            pass
        return round((covers_passed/total_covers) * 100.0, 2) if total_covers > 0 else None
    pass


class Covergroup(Coverage):

    group = []

    def __init__(self, name: str, bins: _List, goal: int=1, bypass: bool=False, max_bins=64):
        # contains the count for each item in the bin under the item itself
        self._bins = dict()
        # initialize the bins
        for item in set(bins):
            self._bins[item] = 0
        # set the goal for each bin
        self._goal = goal
        # initialize the total count of all covers
        self._total_count = 0
        super().__init__(name, bypass)
    pass


    def cover(self, item):
        '''
        Return's true if it got the entire group closer to meeting coverage.

        This means that the item covered is under the goal.
        '''
        success = self._bins.get(item) != None and self._bins[item] < self._goal
        # check if its in the covered bin
        if self._bins.get(item) != None:
            # update the map with the value
            self._bins[item] += 1
            # update the total count
            self._total_count += 1
            pass
        return success
    

    def next(self, rand=False):
        '''
        Returns the next item currently not meeting the coverage goal.

        Enabling `rand` will allow for a random item to be picked, rather than
        sequentially.

        Returns `None` if no item is left (all goals are reached and coverage is
        passing).
        '''
        available = []
        # filter out the elements who have not yet met the goal
        for (item, count) in self._bins.items():
            if count < self._goal:
                available += [item]
            pass
        if len(available) == 0:
            return None
        if rand == True:
            return _random.choice(available)
        # provide 1st available if random is disabled
        return available[0]

    
    def passed(self) -> bool:
        '''
        Checks if each bin within the `Covergroup` has met or exceeded its goal. 
        If any of the bins has not, then whole function fails and returns `False`.
        '''
        for val in self._bins.values():
            # fail on first failure
            if val < self._goal:
                return False
        return True
    

    def to_str(self, verbose: bool) -> str:
        result = ''
        # print each individual bin and its goal status
        if verbose == True:
            longest_len = 0
            for key in self._bins.keys():
                if len(str(key)) > longest_len:
                    longest_len = len(str(key))
                pass
            is_first = True
            for (key, val) in self._bins.items():
                if is_first == False:
                    result += '\n    '
                result += str(key) + ': ' + (' ' * (longest_len-len(str(key)))) + str(val) + '/' + str(self._goal)
                is_first = False
        # print the number of bins that reached their goal
        else:
            bins_reached = 0
            for count in self._bins.values():
                if count >= self._goal:
                    bins_reached += 1
                pass
            result += str(bins_reached) + '/' + str(len(self._bins))
        return result
    pass


    def lump(self, max_bins):
        '''
        Lump bins into groups
        '''
        # @todo
        pass

class Coverpoint(Coverage):
    '''
    Coverpoints track when particular events occur.
    '''

    def __init__(self, name: str, goal: int, bypass=False):
        self._count = 0
        self._goal = goal
        super().__init__(name, bypass)
        pass


    def cover(self, cond: bool):
        '''
        Returns `True` if the `cond` was satisfied and updates the internal count
        as the coverpoint tries to met or exceed its goal.
        '''
        if cond == True:
            self._count += 1
        return cond


    def passed(self):
        return self._count >= self._goal
    

    def to_str(self, verbose: bool):
        return str(self._count) + '/' + str(self._goal)
    
    pass
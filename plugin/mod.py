# File: mod.py
# Engineer: Chase Ruskin
# Details:
#   Common functions used across plugins written in Python.
#
import os
from typing import List
from enum import Enum
import argparse


def quote_str(s: str) -> str:
    '''Wraps the string `s` around double quotes `\"` characters.'''
    return '\"' + s + '\"'


class Generic:
    def __init__(self, key: str, val: str):
        self.key = key
        self.val = val
        pass
    pass


    @classmethod
    def from_str(self, s: str):
        # split on equal sign
        words = s.split('=', 1)
        if len(words) != 2:
            return None
        return Generic(words[0], words[1])
    

    @classmethod
    def from_arg(self, s: str):
        result = Generic.from_str(s)
        if result is None:
            msg = "Generic "+quote_str(s)+" is missing <value>"
            raise argparse.ArgumentTypeError(msg)
        return result


    def to_str(self) -> str:
        return self.key+'='+self.val
    pass


class Env:
    @staticmethod
    def read(key: str, default: str=None, missing_ok: bool=True) -> None:
        value = os.environ.get(key)
        # do not allow empty values to trigger variable
        if value is not None and len(value) == 0:
            value = None
        if value is None:
            if missing_ok == False:
                exit("error: Environment variable "+quote_str(key)+" does not exist")
            else:
                value = default
        return value
    pass


class Status(Enum):
    OKAY = 0
    FAIL = 101
    pass


    @staticmethod
    def from_int(code: int):
        if code == 0:
            return Status.OKAY
        else:
            return Status.FAIL


    def unwrap(self):
        # print an error message
        if self == Status.FAIL:
            exit(Status.FAIL.value)
        pass
    pass


class Command:
    def __init__(self, command: str):
        self._command = command
        self._args = []


    def args(self, args: List[str]):
        if args is not None and len(args) > 0:
            self._args += args
        return self
    

    def arg(self, arg: str):
        # skip strings that are empty
        if arg is not None and str(arg) != '':
            self._args += [str(arg)]
        return self
    

    def spawn(self, verbose: bool=False) -> Status:
        job = quote_str(self._command)
        for c in self._args:
            job = job + ' ' + quote_str(c)
        if verbose == True:
            print('info:', job)
        status = os.system(job)
        return Status.from_int(status)
    pass
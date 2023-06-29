__all__ = ["coverage", "model"]

import unittest as _ut
import math as _math

# --- Classes and Functions ----------------------------------------------------

def pow2m1(width: int):
    '''
    Computes the following formula: `2^(width)-1`   
    '''
    return (2**width)-1


def pow(base: int, exp: int):
    '''
    Computes the followng formula: `base^exp`
    '''
    return base**exp


def to_logic(n, width: int=None, trunc: bool=True, big_endian=True) -> str:
    '''
    Converts the integer `n` to a binary string.

    If `n` is negative, the two's complement representation will be returned.
    When translating a list, the 0th index corresponds to the LSB when `big_endian`
    is set to true. In other words, big-endianness will assume the `n[0]` is the LSB.

    ### Parameters
    - `n`: integer number or list of 1s and 0s to transform
    - `width`: specify the number of bits (never truncates) 
    - `trunc`: trim upper-most bits if width is less than required bit count
    - `big_endian`: if true, store MSB bit first (LHS) and use range 'downto'

    ### Returns
    - `str` of 1's and 0's
    '''
    logic_vec = ''
    # handle vector of ints (1s and 0s)
    if isinstance(n, list) == True:
        for bit in n: logic_vec += str(bit)
        # flip to default big-endianness
        logic_vec = logic_vec[::-1]
        if width is None:
            width = len(n)
    # handle pure integer values
    elif isinstance(n, int) == True:
        bin_str = bin(n)
        is_negative = bin_str[0] == '-'
        # auto-define a width
        if width == None:
            width = 1 if n == 0 else _math.ceil(_math.log(abs(n) + 0.5, 2))
            # extend to use negative MSB
            if is_negative == True:
                width += 1
        # compute 2's complement representation
        if is_negative == True:
            bin_str = bin(2**width + n)
        # assign to outer variable
        logic_vec = bin_str[2:]
        pass
    
    # fill with zeros on the left depending on 'width' (never truncates)
    logic_vec = logic_vec.zfill(width)

    # truncate upper bits
    if trunc == True and width < len(logic_vec):
        logic_vec = logic_vec[len(logic_vec)-width:]

    # flip based on endianness
    if big_endian == False:
        logic_vec = logic_vec[::-1]

    return logic_vec


def from_logic(b: str, signed: bool=False) -> int:
    '''
    Converts the binary string `b` to an integer representation.
    
    ### Parameters
    - `b`: binary string to convert (example: '011101')
    - `signed`: apply two's complement when MSB = '1' during conversion

    ### Returns
    - `b` as integer form (decimal)
    '''
    if signed == True and b[0] == '1':
        # flip all bits
        flipped = ''
        for bit in b: flipped += str(int(bit, base=2) ^ 1)
        return (int('0b'+flipped, base=2)+1) * -1
    else:
        return int('0b'+b, base=2)


def get_generics(entity: str=None) -> dict:
    '''
    Fetches generics and their (optional) default values from an HDL `entity`.
    
    If no `entity` is provided, then it will invoke the `orbit` program to detect
    the entity to get with the $ORBIT_BENCH environment variable.

    All values returned in the dictionary are left in `str` representation with 
    no pre-determined casting. It it the programmer's job to determine how to cast
    the values to the Python programming language.

    Generics set on the command-line override generic values found in the HDL source code
    file. 

    ### Parameters
    - `entity`: HDL entity identifier to fetch generic interface

    ### Returns
    - dictionary of generic identifiers (`str`) as keys and optional values (`str`) as values
    '''
    import subprocess, os, argparse
    gens = dict()
    BENCH = entity if entity != None else os.environ.get('ORBIT_BENCH')

    # grab default values from testbench
    command_success = True
    try:
        signals = subprocess.check_output(['orbit', 'get', BENCH, '--signals']).decode('utf-8').strip()
    except: 
        if BENCH is not None:
            print('warning: Failed to extract generics from entity \"'+BENCH+'\"')
        else:
            print('warning: No testbench set as environment variable \"ORBIT_BENCH\"')
        command_success = False

    # act on the data returned from `Orbit` if successfully ran
    if command_success == True:
        # filter for constants
        gen_code = []
        for line in signals.splitlines():
            i = line.find('constant ')
            if i > -1 :
                gen_code += [line[i+len('constant '):line.find(';')]]

        # extract the constant name
        for gen in gen_code:
            # identify name
            name = gen[:gen.find(' ')]
            gens[name] = None
            # identify a default value if has one
            def_val_i = gen.find(':= ')
            if def_val_i > -1:
                gens[name] = gen[def_val_i+len(':= '):]
        pass

    # override defaults with any values found on the command-line
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('-g', '--generic', action='append', nargs='*', type=str)
    args, _unknown = parser.parse_known_args()
    if args.generic != None:
        arg: str
        for arg in args.generic:
            value = None
            name = arg[0]
            if arg[0].count('=') > 0:
                name, value = arg[0].split('=', maxsplit=1)
            gens[name] = value

    return gens


from .model import SuperBfm as __SuperBfm


def parse_args(bfm: __SuperBfm):
    '''
    Checks the command-line for any args.
    '''
    import argparse

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--code', action='store_true', default=False)
    args, _unknown = parser.parse_known_args()
   
    # print code and exit
    if args.code == True:
        # print the VHDL code for the bfm record type to connect to UUT
        print(bfm.get_vhdl_record_bfm())
        # print VHDL code to make procedure in DRIVER stage
        print(bfm.get_vhdl_process_inputs())
        # print VHDL code to make procedure in the CHECKER stage
        print(bfm.get_vhdl_process_outputs())
        exit(0)
    pass


__seed = None

def get_seed(default: int=None) -> int:
    '''
    Returns a seed integer value to be used to set the random number generator.

    Parses command-line arguments for '--seed' [SEED]. If [SEED] is not given, then
    `None` will be returned. If '--seed' is not given, then the `default` will be
    returned.
    '''
    import argparse, sys, random
    global __seed

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--seed', action='store', type=int, nargs='?', default=default, const=None)
    args, _unknown = parser.parse_known_args()

    if __seed is None:
        __seed = random.randrange(sys.maxsize)
    # set the seed value
    return args.seed if args.seed is not None else __seed


def interp_vhdl_bool(s: str) -> bool:
    '''
    Interprets a string `s` encoded as a vhdl boolean datatype and casts it
    to a Python `bool`.
    '''
    return s.lower() == 'true'


def interp_vhdl_opt(s: str) -> bool:
    '''
    Interprets a string `s` encoded as a vhdl option datatype and casts it
    to a Python `bool`.
    '''
    return s.lower() == 'enable'


# --- Tests --------------------------------------------------------------------

class __Test(_ut.TestCase):

    def test_to_logic_using_int(self):
        self.assertEqual('001', to_logic(1, width=3))

        self.assertEqual('10', to_logic(2))

        self.assertEqual('1011', to_logic(-5))

        self.assertEqual('101', to_logic(5))

        self.assertEqual('0', to_logic(0))

        self.assertEqual('11', to_logic(-1))

        self.assertEqual('01111', to_logic(15, 5))
        # truncate upper bits to keep lower 2 bits
        self.assertEqual('11', to_logic(15, width=2, trunc=True))
        # keep upper two bits
        self.assertEqual('00', to_logic(3, width=4)[:2])
        # represent a number that requires more than 32 bits
        self.assertEqual('100000000000000000000000000000000', to_logic(2**32))

        self.assertEqual('011', to_logic(6, big_endian=False))

        self.assertEqual('110', to_logic(6, big_endian=True))

        self.assertEqual('01', to_logic(6, width=2, big_endian=False))
        pass


    def test_to_logic_using_list(self):
        vec = [0, 1, 1, 0]
        self.assertEqual(to_logic(vec), '0110')

        vec = [1, 1, 1, 0, 0, 0]
        self.assertEqual(to_logic(vec), '000111')

        vec = [1, 1, 1, 0, 0, 0]
        self.assertEqual(to_logic(vec, big_endian=False), '111000')

        vec = [1, 0, 1, 0]
        self.assertEqual(to_logic(vec, width=3), '101')

        vec = [1, 1, 0, 0, 1]
        self.assertEqual(to_logic(vec, width=2, big_endian=False), '11')
        pass


    def test_from_logic(self):
        self.assertEqual(10, from_logic('1010'))

        self.assertEqual(-6, from_logic('1010', signed=True))

        self.assertEqual(5, from_logic('00000101'))
        pass


    def test_pow2m1(self):
        self.assertEqual(pow2m1(0), 0)

        self.assertEqual(pow2m1(1), 1)

        self.assertEqual(pow2m1(3), 7)

        self.assertEqual(pow2m1(4), 15)

        self.assertEqual(pow2m1(8), 255)
        pass


    def test_pow(self):
        self.assertEqual(pow(3, 4), 81)
        pass

    pass

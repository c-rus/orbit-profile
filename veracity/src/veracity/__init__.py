__all__ = ["coverage", "model"]

import io as _io
import unittest as _ut
import math as _math
from typing import List as _List

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


def to_bin(n: int, width: int=None, trunc: bool=True) -> str:
    '''
    Converts the integer `n` to a binary string.

    If `n` is negative, the two's complement representation will be returned.

    ### Parameters
    - `n`: integer number to convert
    - `width`: specify the number of bits (never truncates) 
    - `trunc`: trim upper-most bits if width is less than required bit count

    ### Returns
    - `str` of 1's and 0's
    '''
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
    # fill with zeros on the left depending on 'width' (never truncates)
    bin_str = bin_str[2:].zfill(width)
    # truncate upper bits
    if trunc == True and width < len(bin_str):
        return bin_str[len(bin_str)-width:]
    else:
        return bin_str


def from_bin(b: str, signed: bool=False) -> int:
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


def write_bits(file: _io.TextIOWrapper, *args) -> None:
    '''
    Writes binary representations to an opened text file `file`.

    Each value is written with a ',' after the preceeding value in the 
    argument list. A newline is formed after all arguments

    ### Parameters
    - `file`: opened writeable text file
    - `*args`: integers or binary strings to write to file in order given

    ### Returns
    - None
    '''
    for a in args:
        # auto-format as binary number
        if type(a) == int:
            file.write(to_bin(a)+',')
        # assume already formatted as binary number
        else:
            file.write(str(a)+',')
        pass
    file.write('\n')
    pass


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
    # check if a testbench is provided
    if BENCH == None:
        print('warning: No generics to extract because no entity is set')
    
    # grab default values from testbench
    command_success = True
    try:
        signals = subprocess.check_output(['orbit', 'get', BENCH, '--signals']).decode('utf-8').strip()
    except:
        print('warning: Failed to extract generics from entity \''+BENCH+'\'')
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
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', '--generic', action='append', nargs='*', type=str)
    args = parser.parse_args()
    if args.generic != None:
        for arg in args.generic:
            value = None
            name = arg[0]
            if arg[0].count('=') > 0:
                name, value = arg[0].split('=', maxsplit=1)
            gens[name] = value

    return gens


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


def vec_int_to_str(vec: _List[int], big_endian=True) -> str:
    '''
    Casts a list containing `int` to a `str` as big-endian.

    Big-endianness will assume the vec[0] is the LSB.
    '''
    word = ''
    for bit in vec: word += str(bit)
    if big_endian == True:
        word = word[::-1]
    return word


# --- Example Logic ------------------------------------------------------------

# example code for replicating logic behavior in software

# INPUT_FILE = open('inputs.dat', 'w')
# OUTPUT_FILE = open('outputs.dat', 'w')

# WIDTH = 8

# for i in range(0, 100):
#     # generate random inputs
#     in_a = random.randint(0, 2**WIDTH-1)
#     in_b = random.randint(0, 2**WIDTH-1)
#     c_in = random.randint(0, 1)

#     # write inputs to file
#     write_bits(INPUT_FILE, 
#         to_bin(in_a, WIDTH), 
#         to_bin(in_b, WIDTH), 
#         c_in,
#         )

#     # replicate logic behavior
#     result = in_a + in_b + c_in

#     # transform to binary representation
#     result_b = to_bin(result, WIDTH+1) 
#     # write outputs to file
#     write_bits(OUTPUT_FILE,
#         result_b[0],  # cout
#         result_b[1:], # sum
#         )
#     pass

# INPUT_FILE.close()
# OUTPUT_FILE.close()


# --- Tests --------------------------------------------------------------------

class __Test(_ut.TestCase):

    def test_to_bin(self):
        self.assertEqual('001', to_bin(1, width=3))
        self.assertEqual('10', to_bin(2))
        self.assertEqual('1011', to_bin(-5))
        self.assertEqual('101', to_bin(5))
        self.assertEqual('0', to_bin(0))
        self.assertEqual('11', to_bin(-1))
        self.assertEqual('01111', to_bin(15, 5))
        # truncate upper bits to keep lower 2 bits
        self.assertEqual('11', to_bin(15, width=2, trunc=True))
        # keep upper two bits
        self.assertEqual('00', to_bin(3, width=4)[:2])
        # represent a number that requires more than 32 bits
        self.assertEqual('100000000000000000000000000000000', to_bin(2**32))
        pass


    def test_from_bin(self):
        self.assertEqual(10, from_bin('1010'))
        self.assertEqual(-6, from_bin('1010', signed=True))
        self.assertEqual(5, from_bin('00000101'))
        pass


    def test_vec_int_to_str(self):
        vec = [0, 1, 1, 0]
        self.assertEqual(vec_int_to_str(vec), '0110')

        vec = [1, 1, 1, 0, 0, 0]
        self.assertEqual(vec_int_to_str(vec), '000111')

        vec = [1, 1, 1, 0, 0, 0]
        self.assertEqual(vec_int_to_str(vec, False), '111000')
    pass

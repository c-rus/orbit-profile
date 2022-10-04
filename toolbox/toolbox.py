from io import TextIOWrapper
import unittest
from math import ceil, log

# --- Classes and Functions ----------------------------------------------------

def to_bin(n: int, width: int=None, trunc: bool=True) -> str:
    bin_str = bin(n)
    is_negative = bin_str[0] == '-'
    # auto-define a width
    if width == None:
        width = 1 if n == 0 else ceil(log(abs(n) + 0.5, 2))
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


def from_bin(n: str, signed: bool=False) -> int:
    if signed == True and n[0] == '1':
        # flip all bits
        flipped = ''
        for bit in n: flipped += str(int(bit, base=2) ^ 1)
        return (int('0b'+flipped, base=2)+1) * -1
    else:
        return int('0b'+n, base=2)


def write_bits(file: TextIOWrapper, *args):
    for a in args:
        # auto-format as binary number
        if type(a) == int:
            file.write(to_bin(a)+'\n')
        # assume already formatted as binary number
        else:
            file.write(str(a)+'\n')
    pass


def get_generics(entity: str=None) -> dict:
    import subprocess, os, argparse
    gens = dict()
    BENCH = entity if entity != None else os.environ.get('ORBIT_BENCH')
    # verify a testbench is provided
    if BENCH == None:
        print('warning: No generics to extract because no entity is set')
        return gens
    # grab default values from testbench
    try:
        signals = subprocess.check_output(['orbit', 'get', BENCH, '--signals']).decode('utf-8').strip()
    except:
        print('warning: Failed to extract generics from entity \''+BENCH+'\'')
        return gens

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

    # override defaults with any values found on the command-line
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', '--generic', action='append', nargs='*', type=str)
    args = parser.parse_args()
    for arg in args.generic:
        value = None
        name = arg[0]
        if arg[0].count('=') > 0:
            name, value = arg[0].split('=', maxsplit=1)
        gens[name] = value

    return gens


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

class Test(unittest.TestCase):

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
    pass
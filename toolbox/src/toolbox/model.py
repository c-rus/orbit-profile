from abc import ABC as _ABC
from abc import abstractmethod as _abstractmethod
import random as _random
from . import to_bin, from_bin, write_bits

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


class Signal:

    def __init__(self, width: int=None, value: int=0):
        self._is_single = True if width == None else False
        self._width = width if width != None else 1
        self._value = value
        pass


    def max(self) -> int:
        '''
        Returns the maximum possible integer value stored in the allotted bits
        (inclusive).
        '''
        return pow2m1(self.width())
    

    def min(self) -> int:
        '''
        Returns the minimum possible integer value stored in the allotted bits 
        (inclusive).
        '''
        return 0
    

    def width(self) -> int:
        '''
        Accesses the number of bits set for this signal.
        '''
        return self._width
    

    def is_single_ended(self):
        '''
        Checks if the signal is not an array-type.
        '''
        return self._is_single
    

    def rand(self):
        '''
        Sets the data to a random value between 'min()' and 'max()', inclusively.
        '''
        self._value = _random.randint(self.min(), self.max())
        return self
    

    def as_int(self) -> int:
        '''
        Accesses the inner data value stored as an integer.
        '''
        return self._value
    

    def as_logic(self) -> str:
        '''
        Casts the data into a series of 1's and 0's in a string. The MSB
        is represented on the LHS (index 0).
        '''
        return to_bin(self.as_int(), self.width())
    

    def set(self, num, is_signed=False):
        '''
        Sets the data to the specified 'num' and according to its data type.  
        
        - If the type is `int`: This function ensures the data is within the 
        'max()' value by using the modulo operator.
        - If the type is `str`: This function will truncate the MSB (left-side) 
        bits from the vector if necessary to make the conversion fit within the 
        'max()' value.
        - Otherwise: the function will print a warning statement
        '''
        if type(num) == int:
            self._value = num % (self.max() + 1)
        elif type(num) == str:
            if self.width() < len(num):
                # use the rightmost bits (if applicable)
                num = num[len(num)-self.width():]
            self._value = from_bin(num, is_signed)
        else:
            print('WARNING: Invalid type attempting to set signal value')


    def __eq__(self, other):
        if isinstance(other, Signal):
            return self.__key() == other.__key()
        return NotImplemented
    

    def __key(self):
        return (self._width, self._value, self._is_single)


    def __hash__(self):
        return hash(self.__key())
    
    pass


class __BaseModel(_ABC):

    @_abstractmethod
    def __init__(self):
        '''
        Defines the available signals along with their widths and default values.

        The order the signals are specified is not necessarily the order they
        are written/read to/from the test vector files.
        '''
        pass


    def send(self, fd):
        '''
        Format the signals as logic values in the file `fd` to be read in during
        simulation.

        The format uses commas (`,`) to separate different signals and the order of signals
        written matches the order of instance variables in the declared class.
        '''
        result = []
        for _, port in self.get_ports():
            result += [port.as_logic()]
        write_bits(fd, *result)


    def get_ports(self):
        '''
        Collects the attributes defined in the subclass into a list storing
        the tuples.
        '''
        result = []
        for (key, val) in vars(self).items():
            # filter out items to be left with only the defined attributes
            if key.startswith('_') == True:
                continue
            if isinstance(val, Signal) == True:
                result += [(key, val)]
            else:
                exit('ERROR: Invalid type given to variable: '+key+' '+str(type(val)))
        return result
    

    @_abstractmethod
    def get_vhdl_proc(self) -> str:
        '''
        Generates valid VHDL code snippet for the reading procedure to parse the
        respective model and its signals in the correct order as they are going
        to be written to the corresponding test vector file.

        This procedure assumes the package `core.testkit.all` is already in scope.
        '''
        pass
    pass


class SuperBfm(__BaseModel, _ABC):


    def rand(self):
        '''
        Generates random input values for each attribute for the BFM. This is
        a convenience function for individually setting each signal randomly.
        '''
        for (id, port) in self.get_ports():
            self.__dict__[id] = Signal(port.width() if port.is_single_ended() == False else None).rand()
        return self


    def get_vhdl_proc(self):
        result = '''
-- This procedure is auto-generated by Python. DO NOT EDIT.
procedure drive_transaction(file fd: text) is 
    variable row : line;
begin
    if endfile(fd) = false then
        -- drive a transaction
        readline(fd, row);
'''
        for id, port in self.get_ports():
            fn_call = 'drive' if port.is_single_ended() == False else 'drive_single'
            result += '        '+fn_call+'(row, '+id+');\n'
        result += '''    end if;
end procedure;          
'''
        return result
    pass


class SuperScoreboard(__BaseModel, _ABC):

    @_abstractmethod
    def score(self, txn):
        '''
        Determine the correct outputs for the scoreboard based on the current
        transaction `txn`.

        This function should update the internal variables and return the
        updated `self` object.
        '''
        pass


    def get_vhdl_proc(self) -> str:
        result = '''
-- This procedure is auto-generated by Python. DO NOT EDIT.
procedure scoreboard(file fd: text) is 
    variable row : line;
'''
        for (id, port) in self.get_ports():
             if port.is_single_ended() == True:
                result += '    variable ideal_'+id+' : logics(0 downto 0);\n'
             else:
                result += '    variable ideal_'+id+' : logics('+id+'\'range);\n'
        result += '''begin
    if endfile(fd) = false then
        -- compare expected outputs and inputs
        readline(fd, row);
'''
        for id, port in self.get_ports():
            result += '        load_var(row, ideal_'+id+');\n'
            param = 'as_logics('+id+')' if port.is_single_ended() == True else id
            result += '        assert_eq('+param+', ideal_'+id+', \"'+id+'\");\n'
        result += '''    end if;
end procedure;
'''
        return result
    pass


class InputVecFile:
    def __init__(self, fname: str='inputs.dat', mode='w'):
        '''
        Creates an input test vector file in write mode.
        '''
        self._file = open(fname, mode)


    def write(self, txn: SuperBfm):
        '''
        Writes a bus functional model (BFM) to the input test vector file.
        '''
        if issubclass(type(txn), SuperBfm):
            txn.send(self._file)
        else:
            print('WARNING: Tried to write invalid type to input test vector file')
    pass


class OutputVecFile:
    def __init__(self, fname: str='outputs.dat', mode='w'):
        '''
        Creates an output test vector file in write mode.
        '''
        self._file = open(fname, mode)


    def write(self, sb: SuperScoreboard):
        '''
        Writes a score from a scoreboard to the input test vector file.
        '''
        if issubclass(type(sb), SuperScoreboard):
            sb.send(self._file)
        else:
            print('WARNING: Tried to write invalid type to output test vector file')
    pass
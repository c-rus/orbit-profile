from abc import ABC as _ABC
from abc import abstractmethod as _abstractmethod
import random as _random
from typing import Tuple as _Tuple
from enum import Enum as _Enum
from . import to_bin, from_bin, write_bits, pow2m1

class Mode(_Enum):
    INPUT  = 0
    OUTPUT = 1
    INOUT  = 2
    LOCAL  = 3
    pass


class Signal:

    def __init__(self, mode: Mode=Mode.LOCAL, width: int=None, value: int=0, downto: _Tuple[str, str]=None, to: _Tuple[str, str]=None):
        self._mode = mode
        self._is_single = True if width == None else False
        self._width = width if width != None else 1
        if self._width <= 0:
            print('WARNING: Signal cannot have width less than or equal to 0')
        self._value = value
        # store values for writing the VHDL record
        self._downto = downto
        self._to = to
        pass


    def mode(self) -> Mode:
        '''
        Returns the type of port the signal is.
        '''
        return self._mode


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


class SuperBfm(_ABC):        
    '''
    Returns the name for the entity being tested. 
    
    This name will appear in the generated VHDL code. By default it is `uut`.
    '''
    entity = None

    @_abstractmethod
    def __init__(self):
        '''
        Defines the available signals along with their widths and default values.

        The order the signals are specified is not necessarily the order they
        are written/read to/from the test vector files.
        '''
        pass


    def send(self, fd, mode: Mode):
        '''
        Format the signals as logic values in the file `fd` to be read in during
        simulation.

        The format uses commas (`,`) to separate different signals and the order of signals
        written matches the order of instance variables in the declared class.
        '''
        result = []
        port: Signal
        for key, port in self.get_ports(mode=mode):
            result += [port.as_logic()]
        write_bits(fd, *result)
        pass


    def get_ports(self, mode: Mode):
        '''
        Collects the attributes defined in the subclass into a list storing
        the tuples.

        Collects all signals tied to the Bfm if `mode` is set to `None`.
        '''
        result = []
        for (key, val) in vars(self).items():
            # filter out items to be left with only the defined attributes
            if key.startswith('_') == True or isinstance(val, Signal) == False:
                continue
            val: Signal
            # only add signals with the correct direction
            if val.mode() == mode or mode is None:
                result += [(key, val)]
        return result
    

    def _get_entity(self) -> str:
        return 'uut' if self.entity is None else str(self.entity)
    

    def _identify_port_types(self, top: str=None):
        '''
        Calls 'Orbit' to get the list of ports as signals to generate record.

        Returns a dictionary of the list of ports and their respective VHDL types.
        '''
        import subprocess, os
        sigs = dict()
        TOP = top if top != None else os.environ.get('ORBIT_TOP')
        # check if a testbench is provided
        if TOP == None:
            print('WARNING: No signals to extract because no entity is set')
        
        # grab default values from testbench
        command_success = True
        try:
            signals = subprocess.check_output(['orbit', 'get', TOP, '--signals']).decode('utf-8').strip()
        except:
            print('WARNING: Failed to extract signals from entity \''+TOP+'\'')
            command_success = False

        # act on the data returned from `Orbit` if successfully ran
        if command_success == True:
            # filter for signals
            sig_code = []
            line: str
            for line in signals.splitlines():
                i = line.find('signal ')
                if i > -1 :
                    sig_code += [line[i+len('signal '):line.find(';')]]

            # extract the constant name
            sig: str
            for sig in sig_code:
                # identify name
                name = sig[:sig.find(' ')]
                sigs[name] = None
                # identify the datatype
                d_type = sig.find(':')
                if d_type > -1:
                    sigs[name] = sig[d_type:sig.find(':=')+1 if sig.find(':=') > -1 else len(sig)]
            pass
        return sigs


    def rand(self):
        '''
        Generates random input values for each attribute for the BFM. This is
        a convenience function for individually setting each signal randomly.
        '''
        port: Signal
        for (id, port) in self.get_ports(mode=Mode.INPUT):
            self.__dict__[id] = Signal(port.mode(), port.width() if port.is_single_ended() == False else None).rand()
        return self


    def get_vhdl_process_inputs(self):
        '''
        Generates valid VHDL code snippet for the reading procedure to parse the
        respective model and its signals in the correct order as they are going
        to be written to the corresponding test vector file.

        This procedure assumes the package `core.testkit.all` is already in scope.
        '''
        PROC_NAME_BIT = 'drive_single'
        PROC_NAME_BUS = 'drive_vector'
        result = '''
-- This procedure is auto-generated by veracity. DO NOT EDIT.
procedure drive_transaction(file fd: text) is 
    variable row : line;
begin
    if endfile(fd) = false then
        -- drive a transaction
        readline(fd, row);
'''
        id: str
        port: Signal
        for id, port in self.get_ports(mode=Mode.INPUT):
            fn_call = PROC_NAME_BIT if port.is_single_ended() == True else PROC_NAME_BUS
            result += '        '+fn_call+'(row, bfm.'+id+');\n'
        result += '''    end if;
end procedure;          
'''
        return result
    

    def get_vhdl_process_outputs(self) -> str:
        '''
        Generates valid VHDL code snippet for the reading procedure to parse the
        respective model and its signals in the correct order as they are going
        to be written to the corresponding test vector file.

        This procedure assumes the package `core.testkit.all` is already in scope.
        '''
        PROC_NAME_BIT = 'load_single'
        PROC_NAME_BUS = 'load_vector'
        TAB = ' ' * 4
        result = '''
-- This procedure is auto-generated by veracity. DO NOT EDIT.
procedure scoreboard(file fd: text) is 
    variable row : line;
    variable ideal : '''+self._get_entity()+'''_bfm;
begin
    if endfile(fd) = false then
        -- compare expected outputs and inputs
        readline(fd, row);
''' 
        id: str
        port: Signal
        for id, port in self.get_ports(mode=Mode.OUTPUT):
            fn_call = PROC_NAME_BIT if port.is_single_ended() == True else PROC_NAME_BUS
            result += (TAB * 2) + fn_call + '(row, ideal.'+id+');\n'
            if port.is_single_ended() == True:
                result += (TAB * 2) + 'assert_eq(as_logics(bfm.'+id+'), as_logics(ideal.'+id+'), \"'+id+'\");\n'
            else:
                result += (TAB * 2) + 'assert_eq(bfm.'+id+', ideal.'+id+', \"'+id+'\");\n'
            pass
        result += TAB + '''end if;
end procedure;
'''
        return result
    

    def get_vhdl_record_bfm(self) -> str:
        TAB = ' ' * 4

        # collect the port types
        port_types = self._identify_port_types(self.entity)
        
        result = '''
-- This record is auto-generated by veracity. DO NOT EDIT.
type '''+self._get_entity()+'''_bfm is record
'''
        id: str
        port: Signal
        # determine spacing for neat alignment of signals
        longest_len = 0
        for (id, _) in self.get_ports(mode=None):
            if len(str(id)) > longest_len:
                longest_len = len(str(id))
            pass
        # write each signal to the bfm record
        for (id, port) in self.get_ports(mode=None):
            # try to auto-identify data type
            d_type = None
            if port._downto is None and port._to is None and id in port_types:
                d_type = port_types[id]
            # override or set the data type
            if d_type is None or port._downto is not None or port._to is not None:
                if port.is_single_ended() == True:
                    d_type = ': std_logic'
                else:
                    d_type = ': std_logic_vector('
                    # check the 'downto' and 'to' attributes
                    if port._downto is not None:
                        d_type += str(port._downto[0])+' downto '+str(port._downto[1])
                    elif port._to is not None:
                        d_type += str(port._to[0])+' to '+str(port._to[1])
                    else:
                        d_type += str(port.width()-1)+' downto '+'0'
                    d_type += ')'
                    pass
       
            result += TAB+id+' '+(' ' * (longest_len-len(str(id))))+d_type+';\n'

            pass
        result += '''end record;

signal bfm : '''+self._get_entity()+'''_bfm;
'''
        return result
    

    @_abstractmethod
    def model(self, *args):
        pass

    pass


class InputFile:
    def __init__(self, fname: str='inputs.dat', mode='w'):
        '''
        Creates an input test vector file in write mode.
        '''
        self._file = open(fname, mode)


    def write(self, bfm: SuperBfm):
        '''
        Writes the inputs of the bus functional model to the input test vector file.
        '''
        if issubclass(type(bfm), SuperBfm):
            bfm.send(self._file, mode=Mode.INPUT)
        else:
            print('WARNING: Tried to write invalid type to input test vector file')
    pass


class OutputFile:
    def __init__(self, fname: str='outputs.dat', mode='w'):
        '''
        Creates an output test vector file in write mode.
        '''
        self._file = open(fname, mode)


    def write(self, bfm: SuperBfm):
        '''
        Writes the outputs of the bus funcitonal model to the output test vector file.
        '''
        if issubclass(type(bfm), SuperBfm):
            bfm.send(self._file, mode=Mode.OUTPUT)
        else:
            print('WARNING: Tried to write invalid type to output test vector file')
    pass
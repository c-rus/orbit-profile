--------------------------------------------------------------------------------
--! Project   : {{ orbit.ip }}
--! Engineer  : {{ orbit.user }}
--! Created   : {{ orbit.date }}
--! Testbench : {{ orbit.filename }}
--! Details   :
--!     @todo: write general overview of component and its behavior
--!
--------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
library util;
use util.toolbox.all;

entity {{ orbit.filename }} is 
    -- @todo: define generic interface (if applicable)
end entity {{ orbit.filename }};


architecture sim of {{ orbit.filename }} is
    --! unit-under-test (UUT) interface wires
    -- @todo: define wires

    --! internal testbench signals
    signal clk: std_logic := '0';
    signal rst: std_logic := '0';
    -- the simulation will halt when `done` becomes '1'
    signal done: std_logic := '0';

    constant period: time := 10ns;
begin
    --! UUT instantiation
    -- @todo: instantiate entity

    --! generate clock with 50% duty cycle
    clk <= not clk after period/2 when done = '0';

    --! initial reset to start from known state
    boot: process
    begin
        rst <= '1';
        wait for period*4;
        rst <= '0';
        wait;
    end process;

    --! feed inputs into the UUT to begin processing
    input: process
        file inputs: text open read_mode is "inputs.dat";
    begin
        wait until rst = '0';

        while not endfile(inputs) loop
            -- example syntax
            -- toolbox.read_str_to_logic_vector(inputs, <signal>);
            -- @todo
        end loop;
        wait;
    end process;

    --! assert the received outputs match expected model values
    bench: process
        file outputs: text open read_mode is "outputs.dat";
    begin
        wait until rst = '0';

        while not endfile(outputs) loop
            --- example syntax
            -- toolbox.read_str_to_logic_vector(inputs, <signal-expected>);

            -- wait until a valid signal

            -- assert value matches
            -- assert <signal-expected> = <signal-receieved> report toolbox.report severity failure

            -- @todo

        end loop;
        done <= '1';
        wait;
    end process;

end architecture sim;
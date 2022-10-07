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
-- @note: uncomment the next 3 lines to use the toolbox package.
-- library util;
-- use util.toolbox_pkg.all;
-- use std.textio.all;

entity {{ orbit.filename }} is 
    -- @todo: define generic interface (if applicable)
end entity {{ orbit.filename }};


architecture sim of {{ orbit.filename }} is
    --! unit-under-test (UUT) interface wires
    -- @todo: define wires

    --! internal testbench signals
    signal clk : std_logic := '0';
    signal rst : std_logic := '0';
    -- the simulation will stop when `halt` becomes '1'
    signal halt : std_logic := '0';

    constant PERIOD : time := 10 ns;
begin
    --! UUT instantiation
    -- @todo: instantiate entity

    --! generate clock with 50% duty cycle
    clk <= not clk after PERIOD/2 when halt = '0';

    --! initial reset to start from known state
    boot: process
    begin
        rst <= '1';
        wait for period*4;
        rst <= '0';
        wait;
    end process;

    --! drive inputs into the UUT to begin processing
    drive: process
        file inputs : text open read_mode is "inputs.dat";
    begin
        wait until rst = '0';

        while not endfile(inputs) loop
            -- @note: example syntax for toolbox package
            -- <signal> <= read_str_to_slv(inputs, <width>);

            -- @todo: write timing control logic
        end loop;
        wait;
    end process;

    --! assert the received outputs match expected model values
    check: process
        file outputs : text open read_mode is "outputs.dat";
        --! @todo: define variables for checking output ports
    begin
        wait until rst = '0';

        while not endfile(outputs) loop
            -- @todo: write timing control logic

            -- @note: example syntax for toolbox package
            -- <variable> <= read_str_to_slv(outputs, <width>);

            -- @note: example syntax for toolbox package
            -- assert <expected> = <received> report error_slv("<message>", <expected>, <received>) severity failure;

        end loop;
        -- stop the simulation
        halt <= '1';
        report "Simulation complete.";
        wait;
    end process;

end architecture sim;
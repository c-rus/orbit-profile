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
    constant DELAY : time := 10 ns;
begin
    --! UUT instantiation
    -- @todo: instantiate entity

    --! assert the received outputs match expected model values
    bench: process
        file inputs  : text open read_mode is "inputs.dat";
        file outputs : text open read_mode is "outputs.dat";
    begin
        -- @todo: drive UUT and check circuit behavior
        while not endfile(inputs) loop
            --! read given inputs from file

            -- @note: example syntax for toolbox package
            -- <signal> <= read_str_to_slv(inputs, <width>);

            wait for DELAY;
            --! read expected outputs from file

            -- @note: example syntax for toolbox package
            -- <signal> <= read_str_to_slv(outputs, <width>);

            -- @note: example syntax for toolbox package
            -- assert <expected> = <received> report error_slv("<message>", <expected>, <received>) severity failure;
        end loop;

        -- halt the simulation
        report "Simulation complete.";
        wait;
    end process;

end architecture sim;
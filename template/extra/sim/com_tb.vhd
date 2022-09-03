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

entity {{ orbit.filename }} is 
    -- @todo: define generic interface (if applicable)
end entity {{ orbit.filename }};


architecture sim of {{ orbit.filename }} is
    --! unit-under-test (UUT) interface wires
    -- @todo: define wires

    --! internal testbench signals
    constant delay: time := 10ns;
begin
    --! UUT instantiation
    -- @todo: instantiate entity

    --! assert the received outputs match expected model values
    bench: process
    begin
        -- @todo: drive UUT and check circuit behavior
        wait;
    end process;

end architecture sim;
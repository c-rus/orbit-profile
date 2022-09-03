--------------------------------------------------------------------------------
--! Project  : {{ orbit.ip }}
--! Engineer : {{ orbit.user }}
--! Created  : {{ orbit.date }}
--! Entity   : {{ orbit.filename }}
--! Details  :
--!     @todo: write general overview of component and its behavior
--!
--------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

entity {{ orbit.filename }} is 
    port (
        clk : in std_logic;
        rst : in std_logic;
        -- @todo: define port interface
    );
end entity {{ orbit.filename }};


architecture rtl of {{ orbit.filename }} is

    -- @todo: define internal signals/components

begin

    -- @todo: describe the circuit
    
end architecture rtl;
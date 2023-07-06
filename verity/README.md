# `verity`

__Verity__ is a testing framework applying UVM concepts for verifying HDL designs using a combination of software languages and hardware description languages. The framework is targeted for Python and VHDL, but can be applied in general to any software and hardware description languages.

## Background

Verifying designs is a hard task, especially as designs become increasingly complex. The Universal Verification Methodology (UVM) was created as a way to generalize good testing procedures for verifying digital circuit designs. __Verity__ builds on UVM concepts and takes advantage of higher-level software languages to reduce the time required in verifying hardware.

The following diagram illustrates the basic UVM structure:

<!-- @todo: insert basic UVM diagram -->

The following diagram illustrates a __Verity__ testing structure:

<!-- @todo: insert basic UVM diagram -->

## Usage

__Verity__ is split into two languages: one at a software level and one at a hard description level. The software programming level is responsible for generating test inputs, tracking coverage, and generating test outputs. The hardware description level is responsible for the timing of the simulation: specifically determining when to drive inputs and monitoring when to check outputs. 

The rationale behind this separation of powers is that software langauges are very good at computing logic and algorithms, while hardware description languages are very good at implementing the concept of time. The fact that software is very easy at implementing algorithms along with the fact that numerous libraries already exist with algorithms you may be trying to implement in hardware, makes writing portions of a testbench in software suitable and natural.

## Operation 
The software level and hardware level co-exist. The software level is first executed to make sure the hardware level has everything it needs: namely the input and output test vector files. 

> __Note:__ The software level can also be responsible for making sure the hardware level properly parses a test vector by generating valid HDL code for implementing a procedure to read a line of the file.

When the software is generating tests, it can also keep track of what test cases are being covered by using _coverage nets_, which are either `Coverpoints` or `Covergroups`.

Once the test files are generated, the simulation can begin at the hardware level in the hardware description language. A library of common functions/procedures exist in the HDL for clock generation, system reseting, signal driving, signal montioring, and assertion checks.

## Current Implementations

### Software
- Python
### Hardware
- VHDL

## Dependencies
- Python (>= 3.7)
- Simulator supporting VHDL

## Examples

See the `examples/` directory.

## Tests

Performing unit tests for the Python implementation:

```
python -m unittest src/verity/*.py
```

## Installing

For the Python library, run the following command from this file's directory:

```
pip install .
```
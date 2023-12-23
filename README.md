# `orbit-profile`

A collection of configurations and plugins for integration with [Orbit](https://github.com/c-rus/orbit).

### Plugins

The following plugins are implemented in this profile:

- `gsim`: Run simulations using the GHDL simulator
- `msim`: Run simulations using the ModelSim simulator
- `quartz`: Run end-to-end FPGA toolflows using Intel Quartus Prime
  
### Installing

1. Download the profile:

```
git clone https://github.com/c-rus/orbit-profile.git "$(orbit env ORBIT_HOME)/profiles/crus"
```

2. Install the required python packages:
```
pip install -r "$(orbit env ORBIT_HOME)/profiles/crus/requirements.txt"
```

3. Link the profile's configuration file to your home configuration:

```
orbit config --append include="profiles/crus/config.toml"
```

4. (__Optional__) Install the Python implementation of `veriti` - a verification library for assisting in simulating HDL designs. Follow the instruction [here](https://github.com/c-rus/veriti.git#installing). This package is used in some plugin workflows.

### Updating

To receive the latest changes:

```
git -C "$(orbit env ORBIT_HOME)/profiles/crus" pull
```


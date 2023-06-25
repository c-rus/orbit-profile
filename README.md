# `orbit-profile`

### A collection of configurations, plugins, and templates for integration with [Orbit](https://github.com/c-rus/orbit).
  
## Installing

Download the profile:

```
git clone https://github.com/c-rus/orbit-profile.git "$(orbit env ORBIT_HOME)/profile/c-rus"
```

Link the profile's configuration file to your home configuration:

```
orbit config --append include="profile/c-rus/config.toml"
```

__Optional:__ Install the Python implementation of `veracity` - a verification library for assisting in simulating HDL designs:
```
pip install -e "$(orbit env ORBIT_HOME)/profile/c-rus/veracity"
```

## Updating

Receive the latest changes:

```
git -C "$(orbit env ORBIT_HOME)/profile/c-rus" pull
```

## Viewing

### Plugins

To view available plugins:

```
orbit plan --list
```

To view details about a plugin:

```
orbit plan --plugin <alias> --list
```

### Templates

To view available templates:

```
orbit new --list
```

To view available files for importing from a template:

```
orbit new --template <alias> --list
```
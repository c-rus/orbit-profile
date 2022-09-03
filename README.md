# `orbit-profile`

### A collection of configurations, plugins, and templates for integration with Orbit.
  
## Installing

Download the profile:

```
git clone https://github.com/c-rus/orbit-profile.git "$(orbit env ORBIT_HOME)/profile/c-rus"
```

Link the profile's configuration file to your home configuration:

```
orbit config --append include="profile/c-rus/config.toml"
```

## Updating

Receive the latest changes:

```
git -C "$(orbit env ORBIT_HOME)/profile/c-rus" pull
```

# Changelog
## Version 2.0.0 (2020-02-22)
- **Breaking Change:** Dropped support for **Python 3.5**.
- **Breaking Change:** Guild data is now read from `data` folder in the working directory.
- Now announces when a guild has a disbandment warning
- Now announces when guild's applications close or open.
- Added docker support


## Version 1.0.0 (2019-07-09)
- Now using YAML instead of json for configuration.
- Now announces guildhall changes.
- Interval between scans is now configurable.
- Removed some configurable values that made the config file more complex.

## Version 0.2.0 (2018-08-24)
- GuildWatcher can now detect invites
    - Announces when a new character is invited
    - Announces when an invite is rejected or revoked.

## Version 0.1.1 (2018-08-12)
- Fixed script entry point
- Renamed script to `guildwatcher` for consistency

## Version 0.1.0 (2018-08-11)
Initial release
- Announces when members join.
- Announces when members are kicked or leave.
- Announces when members are promoted.
- Announces when members are deleted.
- Announces when members get a name change.
- Announces when members get their title changed.
- Configurable via JSON file.
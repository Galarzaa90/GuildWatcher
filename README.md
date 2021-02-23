# GuildWatcher

A discord webhook that posts guild changes (member joins, members leaves, member promoted) in a Discord channel.

![GitHub Workflow Status](https://img.shields.io/github/workflow/status/Galarzaa90/GuildWatcher/Build/master)
[![GitHub release](https://img.shields.io/github/release/Galarzaa90/GuildWatcher/all.svg)](https://github.com/Galarzaa90/GuildWatcher/releases)
[![PyPI](https://img.shields.io/pypi/v/GuildWatcher.svg)](https://pypi.python.org/pypi/GuildWatcher/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/GuildWatcher.svg)
![PyPI - License](https://img.shields.io/pypi/l/GuildWatcher.svg)
[![codecov](https://codecov.io/gh/Galarzaa90/GuildWatcher/branch/master/graph/badge.svg?token=8MUNkVsCtO)](https://codecov.io/gh/Galarzaa90/GuildWatcher)

## Installing
### with pip
To install the latest version on PyPi:
```shell
pip install guildwatcher
```

or

Install the latest version from GitHub
```shell
pip install git+https://github.com/Galarzaa90/GuildWatcher.git
```

### with docker
```shell
docker pull galarzaa90/guild-watcher
```


### with git
You can download the files and run locally, but you will require to install dependencies yourself:
```shell
git clone https://github.com/Galarzaa90/GuildWatcher
pip install -r requirements.txt
```

## Configuring Webhooks
1. On the desired channel, go to its settings and click on the **Webhooks** section.
1. Click on **Create Webhook**.
1. Customize the avatar as needed.
1. Copy the webhook's URL.
1. Create a file named **config.yml** and edit it, basing it on **config-example.yml**.
    * The top level `webhook_url` will be used, but if you want another guild to use a different URL, you can specify one for that guild.
    
## Running
### The data directory
The script saves every guild's data to a `.data` file. On the next scan, the current state of the guild is compared with the previous guild's data in order to detect the changes.

The `.data` files allow the script to be able to keep track of changes between executions. Without a `.data` file, if the script was stopped and was executed an hour later, all changes that occurred in that time frame would not be detected.

### Installed via pip or locally
`config.yml` must be in the same directory you're running the script from.


If installed using pip, you can run the script in one of two ways:
```shell
guildwatcher
```

or

```shell
python -m guildwatcher
```

### From docker image
In order to run the script from a docker image, you need to mount the configuration file to `/app/config.yml`. 

While not required, it is highly recommended mounting a directory to store the guild data, to persist data files between executions. The data folder must be mounted to `/app/data/`.

```shell
docker run \
    -v "$(pwd)"/config.yml:/app/config.yml \
    -v "$(pwd)"/data/:/app/data/ \
    --rm -it galarzaa90/guild-watcher
```


## Current Features
- Announces when a member joins.
- Announces when a member leaves or is kicked.
- Announce when a member is promoted or demoted.
- Announce when a member changes name.
- Announce when a member's title is changed.
- Announce when a new character is invited.
- Announce when an invitation is revoked or rejected.
- Announce when the guildhall changes.
- Announce when a guild's application status is changed
- Announce when a guild is in risk of being disbanded.
- Multiple guilds support.
- Configurable scan times.
- Webhook URL configurable per guild.

## Known Issues
- Renaming a rank would trigger all rank members getting announced as leaving and joining back.

## Planned features

- Announce changes in guild attributes.
    - Application status
    - Disband warning
- Granular notification settings (e.g. disable rank changes, disable title changes, etc.)

## Example
![image](https://user-images.githubusercontent.com/12865379/29383497-7df48300-8285-11e7-83c3-f774ad3a43a8.png)


# GuildWatcher

A discord webhook that posts guild changes (member joins, members leaves, member promoted) in a Discord channel.

![Travis (.org)](https://img.shields.io/travis/Galarzaa90/GuildWatcher.svg)
[![GitHub (pre-)release](https://img.shields.io/github/release/Galarzaa90/GuildWatcher/all.svg)](https://github.com/Galarzaa90/GuildWatcher/releases)
[![PyPI](https://img.shields.io/pypi/v/GuildWatcher.svg)](https://pypi.python.org/pypi/GuildWatcher/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/GuildWatcher.svg)
![PyPI - License](https://img.shields.io/pypi/l/GuildWatcher.svg)

## Installing
### with pip
To install the latest version on PyPi:
```commandline
pip install guildwatcher
```

or

Install the latest version from GitHub
```commandline
pip install git+https://github.com/Galarzaa90/GuildWatcher.git
```

### with docker
```shell
docker pull galarzaa90/guild-watcher
```


### with git
You can download the files and run locally, but you will require to install dependencies yourself:
```commandline
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
    
## Running the script
- `config.yml` must be in the same directory you're running the script from.
- The script generates `.data` files, named after the guilds, these save the last state of the guild, to compare it with the current state.

If installed using pip, you can run the script in one of two ways:
```commandline
guildwatcher
```

or

```commandline
python -m guildwatcher
```

## Running from docker image
```shell
docker run \
    -v "$(pwd)"/config.yml:/app/config.yml \
    -v "$(pwd)"/data/:/app/data/ \
    -rm -it galarzaa90/guild-watcher
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
- Multiple guilds support.
- Configurable scan times.
- Webhook URL configurable per guild.

## Known Issues
- Renaming a rank would trigger all rank members getting announced as leaving and joining back.

## Planned features

- Announce changes in guild attributes.
    - Application status
    - Disband warning

## Example
![image](https://user-images.githubusercontent.com/12865379/29383497-7df48300-8285-11e7-83c3-f774ad3a43a8.png)


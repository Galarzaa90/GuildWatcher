# GuildWatcher

A discord webhook that posts guild changes (member joins, members leaves, member promoted) in a Discord channel.

![Travis (.org)](https://img.shields.io/travis/Galarzaa90/GuildWatcher.svg)
[![GitHub (pre-)release](https://img.shields.io/github/release/Galarzaa90/GuildWatcher/all.svg)](https://github.com/Galarzaa90/GuildWatcher/releases)
[![PyPI](https://img.shields.io/pypi/v/GuildWatcher.svg)](https://pypi.python.org/pypi/GuildWatcher/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/GuildWatcher.svg)
![PyPI - License](https://img.shields.io/pypi/l/GuildWatcher.svg)

## Installing
Install and update using pip:
```commandline
pip install guildwatcher -U
```

or

Install the latest version from GitHub
```commandline
pip install git+https://github.com/Galarzaa90/GuildWatcher.git -U
```

or

Download/Clone files, install requirements and run `guildwatcher.py`
```commandline
pip install -r requirements.txt
```

## Configuring Webhooks
1. On the desired channel, go to its settings and click on the **Webhooks** section.
1. Click on **Create Webhook**.
1. Customize the avatar as needed.
1. Copy the webhook's URL.
1. Create a file named **config.json** and edit it, basing it on **config-example.json**.
    * The top level `webhook_url` will be used, but if you want another guild to use a different URL, you can specify one for that guild.
    * If `override_image` is added to the guild, its logo will be used instead.
    
## Running the script
- `config.json` must be in the same directory you're running the script from.
- The script generates `.data` files, named after the guilds, these save the last state of the guild, to compare it with the current state.

If installed using pip, you can run the script in one of two ways:
```commandline
guildwatcher
```

or

```commandline
python -m guildwatcher
```

## Current Features
* Announces when a member joins
* Announces when a member leaves or is kicked
* Announce when a member is promoted or demoted
* Announce when a member changes name
* Announce when a member's title is changed
* Multiple guilds support
* Webhook URL configurable per guild

## Known Issues
* Renaming a rank would trigger all rank members getting announced as leaving and joining back.

## Planned features
* Configurable scan times
* Check invites

## Example
![image](https://user-images.githubusercontent.com/12865379/29383497-7df48300-8285-11e7-83c3-f774ad3a43a8.png)


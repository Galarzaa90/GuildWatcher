# GuildWatcher [![Build Status](https://travis-ci.org/Galarzaa90/GuildWatcher.svg?branch=master)](https://travis-ci.org/Galarzaa90/GuildWatcher)

A discord webhook that posts guild changes (member joins, members leaves, member promoted) in a Discord channel.


## Requirements:
* Python 3.2 or higher with the following module:
    * Requests

## Configuring Webhooks
1. On the desired channel, go to its settings and click on the **Webhooks** section.
1. Click on **Create Webhook**.
1. Change the bot's name and avatar to whatever you prefer.
    * You can also edit config.json to override the bot's username and avatar
1. Rename **config-example.json** to **config.json** and edit it.
    * "*name*" and "*avatar_url*" are optional parameters, they can be left blank or removed. 
    If used, those values will be used instead of the ones set in the webhook configuration screen in discord.
    * Add as many guilds as you like. If "*override_name*" or "*override_image*" is used, the message will show the 
    guild's name and/or picture instead.
1. Run the script.

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


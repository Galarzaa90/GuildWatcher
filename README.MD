*Script is still under development*

A discord webhook that posts guild changes (member joins, members leaves, member promoted) in a Discord channel.


## Requirements:
* Python 3.4.2 or higher with the following modules:
    * Requests
    * Pickle

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
* Multiple guilds support

## Known Issues
* Renaming a rank would trigger all rank members getting announced as leaving and joinning back.
* A name change would be detected as leaving, and joining.

## Planned features
* Announce when a member's rank changes
* Announce when a member's title changes
* Webhook URL configurable per guild
* Configurable scan times

## Example
![image](https://cloud.githubusercontent.com/assets/12865379/23975881/f59df368-09a0-11e7-86f4-2f1f23351f3f.png)

*Script is still under development*

A discord webhook that posts guild changes (member joins, members leaves, member promoted) in a Discord channel.


## Requirements:
* Python 3.4.2 or higher
* Requests
* Pickle

## Configuring Webhooks
1. On the desired channel, go to its settings and click on the **Webhooks** section.
2. Click on **Create Webhook**.
3. Change the bot's name and avatar to whatever you prefer.
4. Copy the **Webhook URL** into the script's settings.

## Current Features
* Announces when a member joins
* Announces when a member leaves or is kicked

## Known Issues
* Renaming a rank would trigger all rank members getting announced as leaving and joinning back.
* A name change would be detected as leaving, and joining.

## Planned features
* Announce when a member's rank changes
* Announce when a member's title changes
* Multiple guilds support

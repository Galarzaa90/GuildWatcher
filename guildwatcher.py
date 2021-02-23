"""
The MIT License (MIT)
Copyright (c) 2019 Allan Galarza

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
import json
import logging
import pickle
import time
from enum import Enum
import os.path

import requests
import tibiapy
import yaml

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s: %(message)s'))
consoleHandler.setLevel(logging.DEBUG)
log.addHandler(consoleHandler)

# Embed colors
CLR_NEW_MEMBER = 0x05825B  # Dark green
CLR_REMOVED_MEMBER = 0xFF0000  # Red
CLR_PROMOTED = 0xFFFF00  # Yellow
CLR_DEMOTED = 0xFFA500  # Orange
CLR_DELETED = 0x000000  # Black
CLR_NAME_CHANGE = 0x00FFFF  # Cyan
CLR_TITLE_CHANGE = 0xC512ED  # Magenta
CLR_INVITE_REMOVED = 0xFF6966  # Light red
CLR_NEW_INVITE = 0x7DF589  # Lime green
CLR_GUILDHALL_REMOVE = 0xA9A9A9  # Grey
CLR_GUILDHALL_CHANGED = 0xFFFFFF  # White
CLR_DISBAND_NEW = 0xE59400  # Darker orange
CLR_DISBAND_REMOVE = 0x08CC8F  # Strong cyan/Lime green
CLR_APPLICATIONS = 0xF5F5DC  # Beige

# Change strings
# m -> Member related to the change
# e -> Emoji representing the character's vocation
# v -> Abbreviated vocation
# extra -> Extra argument, related to the change.
FMT_CHANGE = "[{m.name}]({m.url}) - **{m.level}** **{v}** {e} - Rank: **{m.rank}** - Joined **{m.joined}**\n"
FMT_NEW_MEMBER = "[{m.name}]({m.url}) - **{m.level}** **{v}** {e}\n"
FMT_NAME_CHANGE = "{extra} → [{m.name}]({m.url}) - **{m.level}** **{v}** {e}\n"
FMT_TITLE_CHANGE = "[{m.name}]({m.url}) - {extra} → {m.title} - **{m.level}** **{v}** {e}\n"
FMT_INVITE_CHANGE = "[{m.name}]({m.url}) - Invited: **{m.date}**\n"
FMT_GUILDHALL_CHANGED = "Guild moved to guildhall **{extra}**"
FMT_GUILDHALL_REMOVE = "Guild no longer owns guildhall **{extra}**"
FMT_DISBAND_REMOVE = "Guild no longer in risk of being disbanded."
FMT_DISBAND_NEW = "Guild will be disbanded on **{extra[1]}** {extra[0]}."


class Change:
    """
    Represents a change found in the guild.

    :ivar member: The member involved
    :ivar type: The change type.
    :ivar extra: Extra information related to the change.
    :type member: abc.Character
    :type type: ChangeType
    :type extra: Optional[Any]
    """
    def __init__(self, _type, member=None, extra=None):
        self.member = member
        self.type = _type
        self.extra = extra

    def __repr__(self):
        return "<%s type=%s member=%r>" % (self.__class__.__name__, self.type.name, self.member)


class ChangeType(Enum):
    """Contains all the possible changes that can be found."""
    NEW_MEMBER = 1  #: New member joined the guild.
    DELETED = 2  #: Member was deleted from the game.
    REMOVED = 3  #: Member was kicked or left the guild.
    NAME_CHANGE = 4  #: Member changed their name.
    TITLE_CHANGE = 5  #: Member title was changed.
    DEMOTED = 6  #: Member was demoted.
    PROMOTED = 7  #: Member was promoted.
    INVITE_REMOVED = 8  #: Invitation was removed or rejected.
    NEW_INVITE = 9  #: New invited
    GUILDHALL_CHANGED = 10  #: Guild moved to a new guildhall.
    GUILDHALL_REMOVED = 11  #: Guild no longer has a guildhall.
    NEW_DISBAND_WARNING = 12  #: Guild is going to be disbanded
    REMOVED_DISBAND_WARNING = 13  #: Guild no longer in danger of being disbanded
    APPLICATIONS_CHANGE = 14  #: The application status changed


class ConfigGuild:
    def __init__(self, name, webhook_url):
        self.name = name
        self.webhook_url = webhook_url

    def __repr__(self):
        return "<%s name=%r webhook_url=%r>" % (self.__class__.__name__, self.name, self.webhook_url)


class Config:
    def __init__(self, **kwargs):
        guilds = kwargs.get("guilds", [])
        self.webhook_url = kwargs.get("webhook_url")
        self.interval = int(kwargs.get("interval", 300))
        self.guilds = []
        for guild in guilds:
            if isinstance(guild, str):
                self.guilds.append(ConfigGuild(guild, self.webhook_url))
            if isinstance(guild, dict):
                self.guilds.append(ConfigGuild(guild["name"], guild["webhook_url"]))

    def __repr__(self):
        return "<%s webhook_url=%r guilds=%r>" % (self.__class__.__name__, self.webhook_url, self.guilds)


def load_config():
    """Loads and validates the configuration file."""
    try:
        with open('config.yml') as yml_file:
            cgf_yml = yaml.safe_load(yml_file)
            return Config(**cgf_yml)
    except FileNotFoundError:
        log.error("Missing config.yml file. Check the example file.")
    except (ValueError, KeyError, TypeError) as e:
        log.error("Malformed config.yml file.\nError: %s" % e)
    exit()


def save_data(file, data):
    """
    Saves a guild's data to a file.
    :param file: The file's path to save to
    :param data: The guild's data.
    """
    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", file), "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_data(file):
    """
    Loads guild data from a file.
    :param file: The file path to look for.
    :return: The guild's data, if available.
    :rtype: tibiapy.Guild
    """
    try:
        with open(os.path.join("data", file), "rb") as f:
            return pickle.load(f)
    except ValueError:
        return None
    except FileNotFoundError:
        return None


def get_character(name, tries=5):  # pragma: no cover
    """
    Gets information about a character from Tibia.com
    :param name: The name of the character.
    :param tries: The maximum amount of retries before giving up.
    :return: The character's information
    :type name: str
    :type tries: int
    :rtype: tibiapy.Character
    """
    try:
        url = tibiapy.Character.get_url(name)
    except UnicodeEncodeError:
        return None

    # Fetch website
    try:
        r = requests.get(url=url)
        content = r.text
    except requests.RequestException:
        if tries == 0:
            return None
        else:
            tries -= 1
            return get_character(name, tries)
    char = tibiapy.Character.from_content(content)
    return char


def get_guild(name, tries=5):  # pragma: no cover
    """
    Gets information about a guild from Tibia.com
    :param name: The name of the guild. Case sensitive.
    :param tries: The maximum amount of retries before giving up.
    :return: The guild's information
    :type name: str
    :type tries: int
    :rtype: tibiapy.Guild
    """
    try:
        r = requests.get(tibiapy.Guild.get_url(name))
        content = r.text
    except requests.RequestException:
        if tries == 0:
            return None
        else:
            tries -= 1
            return get_guild(name, tries)

    guild = tibiapy.Guild.from_content(content)

    return guild


def split_message(message):  # pragma: no cover
    """Splits a message into smaller messages if it exceeds the limit

    :param message: The message to split
    :type message: str
    :return: The split message
    :rtype: list of str"""
    if len(message) <= 1900:
        return [message]
    else:
        lines = message.splitlines()
        new_message = ""
        message_list = []
        for line in lines:
            if len(new_message+line+"\n") <= 1900:
                new_message += line+"\n"
            else:
                message_list.append(new_message)
                new_message = ""
        if new_message:
            message_list.append(new_message)
        return message_list


def compare_guild(before, after):
    """
    Compares the same guild at different points in time, to obtain the changes made.

    It returns all the changes found.

    :param before: The state of the guild in the previous saved state.
    :type before: tibiapy.Guild
    :param after:  The current state of the guild.
    :type after: tibiapy.Guild
    :return: A list of all the changes found.
    :rtype: list of Change
    """
    changes = []
    # Members no longer in guild. Some may have changed name.
    removed_members = [m for m in before.members if m not in after.members]
    joined = [m for m in after.members if m not in before.members]

    if before.guildhall != after.guildhall:
        if before.guildhall is None:
            changes.append(Change(ChangeType.GUILDHALL_CHANGED, None, after.guildhall.name))
            log.info("New guildhall: %s" % after.guildhall.name)
        elif after.guildhall is None:
            log.info("Guildhall removed: %s" % before.guildhall.name)
            changes.append(Change(ChangeType.GUILDHALL_REMOVED, None, before.guildhall.name))
    if before.disband_condition != after.disband_condition:
        if after.disband_condition is None:
            log.info("Guild no longer in danger of disbanding")
            changes.append(Change(ChangeType.REMOVED_DISBAND_WARNING))
        else:
            log.info("Guild in danger of being disbanded: %s", after.disband_condition)
            changes.append(Change(ChangeType.NEW_DISBAND_WARNING, extra=(after.disband_condition, after.disband_date)))
    if before.open_applications != after.open_applications:
        changes.append(Change(ChangeType.APPLICATIONS_CHANGE, extra=after.open_applications))
        log.info("Guild application status changed: %s", "open" if after.open_applications else "closed")

    compare_members(after, before, changes)
    check_removed_members(changes, joined, removed_members)

    changes += [Change(ChangeType.NEW_MEMBER, m) for m in joined]
    if len(joined) > 0:
        log.info("New members found: " + ",".join(m.name for m in joined))

    compare_guild_invites(after, before, changes, joined)
    return changes


def compare_members(after, before, changes):
    """Compares the members still in the guild to see what changed.

    It compares the member's current state, with the previous member's state."""
    # ranks is property, so we save a copy to avoid recalculating it every time.
    ranks = after.ranks[:]
    for member in before.members:
        for member_after in after.members:
            if member != member_after:
                continue
            # Rank changed
            if member.rank != member_after.rank:
                try:
                    # Check if new rank position's is higher or lower
                    if ranks.index(member.rank) < ranks.index(member_after.rank):
                        changes.append(Change(ChangeType.DEMOTED, member_after))
                        log.info("Member demoted: %s" % member_after.name)
                    else:
                        log.info("Member promoted: %s" % member_after.name)
                        changes.append(Change(ChangeType.PROMOTED, member_after))
                except ValueError:
                    # The member used to have a rank that no longer exists:
                    # This can be due to the rank being renamed or the rank being no longer visible as it has no members
                    pass
            # Title changed
            if member.title != member_after.title:
                log.info("Member title changed from '%s' to '%s'" % (member.title, member_after.title))
                changes.append(Change(ChangeType.TITLE_CHANGE, member_after, member.title))
            break


def check_removed_members(changes, joined, removed_members):
    """Checks every removed member to see if they left, changed name or were deleted."""
    for member in removed_members:
        # We check if it was a namechange or character deleted
        log.info("Checking character {0.name}".format(member))
        char = get_character(member.name)
        # Character was deleted (or maybe namelocked)
        if char is None:
            log.info("Member deleted: %s" % member.name)
            changes.append(Change(ChangeType.DELETED, member))
            continue
        # Character has a new name and matches someone in guild, meaning it got a name change
        found = False
        for _member in joined:
            if char.name == _member.name:
                joined.remove(_member)
                changes.append(Change(ChangeType.NAME_CHANGE, _member, member.name))
                log.info("%s changed name to %s" % (member.name, _member.name))
                found = True
                break
        if not found:
            log.info("Member no longer in guild: " + member.name)
            changes.append(Change(ChangeType.REMOVED, member))


def compare_guild_invites(after, before, changes, joined):
    """Compares invites, to see if they were accepted or rejected."""
    new_invites = [i for i in after.invites if i not in before.invites]
    removed_invites = [i for i in before.invites if i not in after.invites]
    # Check if invitation got removed or member joined
    for removed_invite in removed_invites:
        accepted = False
        for new_member in joined:
            if new_member.name == removed_invite.name:
                accepted = True
                break
        if not accepted:
            log.info("Invite rejected or removed: " + removed_invite.name)
            changes.append(Change(ChangeType.INVITE_REMOVED, removed_invite))
    changes += [Change(ChangeType.NEW_INVITE, i) for i in new_invites]
    if len(new_invites) > 0:
        log.info("New invites found: " + ",".join(m.name for m in new_invites))


def get_vocation_emoji(vocation):
    """Returns an emoji to represent a character's vocation.

    :param vocation: The vocation's name.
    :type vocation: tibiapy.Vocation
    :return: The emoji that represents the vocation.
    :rtype: str
    """
    return {
        tibiapy.Vocation.DRUID: "❄️",
        tibiapy.Vocation.ELDER_DRUID: "❄️",
        tibiapy.Vocation.KNIGHT: "🛡",
        tibiapy.Vocation.ELITE_KNIGHT: "🛡",
        tibiapy.Vocation.SORCERER: "🔥",
        tibiapy.Vocation.MASTER_SORCERER: "🔥",
        tibiapy.Vocation.PALADIN: "🏹",
        tibiapy.Vocation.ROYAL_PALADIN: "🏹",
    }.get(vocation, "")


def get_vocation_abbreviation(vocation):
    """Gets an abbreviated string of the vocation.

    :param vocation: The vocation's name
    :type vocation: tibiapy.Vocation
    :return: The emoji that represents the vocation.
    :rtype: str"""
    return {
        tibiapy.Vocation.DRUID: "D",
        tibiapy.Vocation.ELDER_DRUID: "ED",
        tibiapy.Vocation.KNIGHT: "K",
        tibiapy.Vocation.ELITE_KNIGHT: "EK",
        tibiapy.Vocation.SORCERER: "S",
        tibiapy.Vocation.MASTER_SORCERER: "MS",
        tibiapy.Vocation.PALADIN: "P",
        tibiapy.Vocation.ROYAL_PALADIN: "RP",
        tibiapy.Vocation.NONE: "N",
    }.get(vocation, "")


def build_embeds(changes):
    """
    Builds a list of discord embed.

    Embeds consist of dictionaries, representing the JSON values.

    :param changes: The changes to build the embed from
    :type changes: list of Change
    :return: A list of dictionaries representing embeds.
    :rtype: list of dict
    """
    embeds = []
    new_members = ""
    removed = ""
    promoted = ""
    demoted = ""
    title_changes = ""
    name_changes = ""
    deleted = ""
    new_invites = ""
    removed_invites = ""
    for change in changes:
        try:
            vocation = get_vocation_abbreviation(change.member.vocation)
            emoji = get_vocation_emoji(change.member.vocation)
        except AttributeError:
            vocation, emoji = None, None
        if change.type == ChangeType.NEW_MEMBER:
            new_members += FMT_NEW_MEMBER.format(m=change.member, v=vocation, e=emoji)
        elif change.type == ChangeType.REMOVED:
            removed += FMT_CHANGE.format(m=change.member, v=vocation, e=emoji)
        elif change.type == ChangeType.DEMOTED:
            demoted += FMT_CHANGE.format(m=change.member, v=vocation, e=emoji)
        elif change.type == ChangeType.PROMOTED:
            promoted += FMT_CHANGE.format(m=change.member, v=vocation, e=emoji)
        elif change.type == ChangeType.DELETED:
            deleted += FMT_CHANGE.format(m=change.member, v=vocation, e=emoji)
        elif change.type == ChangeType.NAME_CHANGE:
            name_changes += FMT_NAME_CHANGE.format(m=change.member, v=vocation, e=emoji, extra=change.extra)
        elif change.type == ChangeType.TITLE_CHANGE:
            title_changes += FMT_TITLE_CHANGE.format(m=change.member, v=vocation, e=emoji, extra=change.extra)
        elif change.type == ChangeType.NEW_INVITE:
            new_invites += FMT_INVITE_CHANGE.format(m=change.member)
        elif change.type == ChangeType.INVITE_REMOVED:
            removed_invites += FMT_INVITE_CHANGE.format(m=change.member)
        elif change.type == ChangeType.GUILDHALL_REMOVED:
            embeds.append({"color": CLR_GUILDHALL_REMOVE, "title": "Guildhall removed",
                           "description": FMT_GUILDHALL_REMOVE.format(extra=change.extra)})
        elif change.type == ChangeType.GUILDHALL_CHANGED:
            embeds.append({"color": CLR_GUILDHALL_CHANGED, "title": "Guildhall changed",
                           "description": FMT_GUILDHALL_CHANGED.format(extra=change.extra)})
        elif change.type == ChangeType.NEW_DISBAND_WARNING:
            embeds.append({"color": CLR_DISBAND_NEW, "title": "Guild in risk of being disbanded",
                           "description": FMT_DISBAND_NEW.format(extra=change.extra)})
        elif change.type == ChangeType.REMOVED_DISBAND_WARNING:
            embeds.append({"color": CLR_DISBAND_REMOVE, "title": "Guild no longer in disband risk",
                           "description": FMT_DISBAND_REMOVE})
        elif change.type == ChangeType.APPLICATIONS_CHANGE:
            embeds.append({"color": CLR_APPLICATIONS, "title": "Guild application status changed",
                          "description": f"Applications are now {'open' if change.extra else 'closed'}."})

    if new_members:
        messages = split_message(new_members)
        for message in messages:
            embeds.append({"color": CLR_NEW_MEMBER, "title": "New member", "description": message})
    if removed:
        messages = split_message(removed)
        for message in messages:
            embeds.append({"color": CLR_REMOVED_MEMBER, "title": "Member left or kicked", "description": message})
    if promoted:
        messages = split_message(promoted)
        for message in messages:
            embeds.append({"color": CLR_PROMOTED, "title": "Member promoted", "description": message})
    if demoted:
        messages = split_message(demoted)
        for message in messages:
            embeds.append({"color": CLR_DEMOTED, "title": "Member demoted", "description": message})
    if deleted:
        messages = split_message(deleted)
        for message in messages:
            embeds.append({"color": CLR_DELETED, "title": "Members deleted", "description": message})
    if name_changes:
        messages = split_message(name_changes)
        for message in messages:
            embeds.append({"color": CLR_NAME_CHANGE, "title": "Member changed name", "description": message})
    if title_changes:
        messages = split_message(title_changes)
        for message in messages:
            embeds.append({"color": CLR_TITLE_CHANGE, "title": "Title changed", "description": message})
    if removed_invites:
        messages = split_message(removed_invites)
        for message in messages:
            embeds.append({"color": CLR_NEW_INVITE, "title": "Invites rejected or cancelled", "description": message})
    if new_invites:
        messages = split_message(new_invites)
        for message in messages:
            embeds.append({"color": CLR_NEW_INVITE, "title": "New invites", "description": message})
    return embeds


def publish_changes(url, embeds, name=None, avatar=None, new_count=0):
    """
    Publish changes to discord through a webhook

    :param url: The webhook's URL
    :param embeds: List of dictionaries, containing the embeds with changes.
    :param name: The poster's name, if None, the name assigned when creating the webhook will be used.
    :param avatar: The URL to the avatar to use, if None, the avatar assigned at creation will be used.
    :param new_count: The new guild member count. If 0, no mention will be made.
    :type url: str
    :type embeds: list of dict
    :type name: str
    :type avatar: str
    :type new_count: int
    """
    # Webhook messages have a limit of 6000 characters
    # Can't display more than 10 embeds in one message
    batches = []
    current_batch = []
    current_length = 0
    for embed in embeds:
        length = len(embed["description"]) + len(embed["title"])
        if current_length+length > 6000 or len(current_batch) == 10:
            batches.append(current_batch)
            current_length = 0
            current_batch = []
            continue
        current_batch.append(embed)
        current_length += length

    batches.append(current_batch)

    for i, batch in enumerate(batches):
        body = {
            "username": name,
            "avatar_url": avatar,
            "embeds": batch
        }
        if i == 0 and new_count > 0:
            body["content"] = "The guild now has **%d** members." % new_count
        try:
            requests.post(url, data=json.dumps(body), headers={"Content-Type": "application/json"})
        except requests.RequestException:
            log.error("Couldn't publish changes.")


def scan_guilds():
    cfg = load_config()
    if not cfg.webhook_url:
        log.error("Missing Webhook URL in config.yml")
        exit()
    while True:
        # Iterate through each guild in the configuration file
        for cfg_guild in cfg.guilds:
            name = cfg_guild.name
            if name is None:
                log.error("Guild is missing name.")
                time.sleep(5)
                continue
            guild_file = name+".data"
            guild_data = load_data(guild_file)
            if guild_data is None:
                log.info(name + " - No previous data found. Saving current data.")
                guild_data = get_guild(name)
                if guild_data is None:
                    log.error(name + " - Error: Guild doesn't exist")
                    continue
                save_data(guild_file, guild_data)
                time.sleep(5)
                continue

            log.info(name + " - Scanning guild...")
            new_guild_data = get_guild(name)
            if new_guild_data is None:
                log.error(name + " - Error: Guild doesn't exist")
                continue
            save_data(guild_file, new_guild_data)
            # Looping through members
            member_count_before = guild_data.member_count
            member_count = new_guild_data.member_count
            # Only publish count if it changed
            if member_count == member_count_before:
                member_count = 0
            changes = compare_guild(guild_data, new_guild_data)
            embeds = build_embeds(changes)
            publish_changes(cfg_guild.webhook_url, embeds, guild_data.name, new_guild_data.logo_url, member_count)
            log.info(name + " - Scanning done")
            time.sleep(2)
        time.sleep(cfg.interval)


if __name__ == "__main__":
    scan_guilds()

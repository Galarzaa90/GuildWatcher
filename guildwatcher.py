import json
import logging
import pickle
import time
from enum import Enum

import requests
import tibiapy

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s: %(message)s'))
consoleHandler.setLevel(logging.DEBUG)
log.addHandler(consoleHandler)


# Change strings
FMT_CHANGE = "[{m.name}]({m.url}) - **{m.level}** **{v}** {e} - Rank: **{m.rank}** - Joined **{m.joined}**\n"
FMT_NEW_MEMBER = "[{m.name}]({m.url}) - **{m.level}** **{v}** {e}\n"
FMT_NAME_CHANGE = "{extra} → [{m.name}]({m.url}) - **{m.level}** **{v}** {e}\n"
FMT_TITLE_CHANGE = "[{m.name}]({m.url}) - {extra} → {m.title} - **{m.level}** **{v}** {e}\n"


class Change:
    """
    Represents a change found in the guild.

    :ivar member: The member involved
    :ivar type: The change type.
    :ivar extra: Extra information related to the change.
    :type member: GuildMember
    :type type: str
    :type extra: Optional[Any]
    """
    def __init__(self, _type, member, extra=None):
        self.member = member
        self.type = _type
        self.extra = extra


class ChangeType(Enum):
    """Contains all the possible changes that can be found."""
    NEW_MEMBER = 1  #: New member joined the guild.
    DELETED = 2  #: Member was deleted from the game.
    REMOVED = 3  #: Member was kicked or left the guild.
    NAME_CHANGE = 4  #: Member changed their name.
    TITLE_CHANGE = 5  #: Member title was changed.
    DEMOTED = 6  #: Member was demoted.
    PROMOTED = 7  #: Member was promoted.


cfg = {}


def load_config():
    """Loads and validates the configuration file."""
    global cfg
    try:
        with open('config.json') as json_data:
            cfg = json.load(json_data)
    except FileNotFoundError:
        log.error("Missing config.json file. Check the example file.")
        exit()
    except ValueError:
        log.error("Malformed config.json file.")
        exit()


def save_data(file, data):
    """
    Saves a guild's data to a file.
    :param file: The file's path to save to
    :param data: The guild's data.
    """
    with open(file, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_data(file):
    """
    Loads guild data from a file.
    :param file: The file path to look for.
    :return: The guild's data, if available.
    :rtype: tibiapy.Guild
    """
    try:
        with open(file, "rb") as f:
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


def compare_guilds(before, after):
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
    ranks = after.ranks[:]
    before_members = before.members[:]
    after_members = after.members[:]
    # Members no longer in guild. Some may have changed name.
    removed_members = [m for m in before_members if m not in after_members]
    joined = [m for m in after_members if m not in before_members]
    for member in before_members:
        for member_new in after_members:
            if member != member_new:
                continue
            # Remove member from list to reduce iterating
            after_members.remove(member_new)
            # Rank changed
            if member.rank != member_new.rank:
                try:
                    # Check if new rank position's is higher or lower
                    if ranks.index(member.rank) < ranks.index(member_new.rank):
                        changes.append(Change(ChangeType.DEMOTED, member_new))
                        log.info("Member demoted: %s" % member_new.name)
                    else:
                        log.info("Member promoted: %s" % member_new.name)
                        changes.append(Change(ChangeType.PROMOTED, member_new))
                except ValueError:
                    # This should be impossible
                    log.error("Unexpected error: Member has a rank not present in list")
            # Title changed
            if member.title != member_new.title:
                log.info("Member title changed from '%s' to '%s'" % (member.title, member_new.title))
                changes.append(Change(ChangeType.TITLE_CHANGE, member_new, member.title))
            break
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
        _found = False
        for _member in after_members:
            if char.name == _member.name:
                after_members.remove(_member)
                changes.append(Change(ChangeType.NAME_CHANGE, _member, member.name))
                log.info("%s changed name to %s" % (member.name, _member.name))
                _found = True
                break
        if _found:
            continue
        log.info("Member no longer in guild: " + member.name)
        changes.append(Change(ChangeType.REMOVED, member))
    changes += [Change(ChangeType.NEW_MEMBER, m) for m in joined]
    if len(joined) > 0:
        log.info("New members found: " + ",".join(m.name for m in joined))
    return changes


def get_vocation_emoji(vocation):
    """Returns an emoji to represent a character's vocation.

    :param vocation: The vocation's name.
    :type vocation: str
    :return: The emoji that represents the vocation.
    :rtype: str
    """
    return {
        "Druid": "\U00002744",
        "Elder Druid": "\U00002744",
        "Knight": "\U0001F6E1",
        "Elite Knight": "\U0001F6E1",
        "Sorcerer": "\U0001F525",
        "Master Sorcerer": "\U0001F525",
        "Paladin": "\U0001F3F9",
        "Royal Paladin": "\U0001F3F9",
    }.get(vocation, "")


def get_vocation_abbreviation(vocation):
    """Gets an abbreviated string of the vocation.

    :param vocation: The vocation's name
    :type vocation: str
    :return: The emoji that represents the vocation.
    :rtype: str"""
    return {
        "Druid": "D",
        "Elder Druid": "ED",
        "Knight": "K",
        "Elite Knight": "EK",
        "Sorcerer": "S",
        "Master Sorcerer": "MS",
        "Paladin": "P",
        "Royal Paladin": "RP",
        "None": "N",
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
    for change in changes:
        vocation = get_vocation_abbreviation(change.member.vocation)
        emoji = get_vocation_emoji(change.member.vocation)
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

    if new_members:
        messages = split_message(new_members)
        for message in messages:
            embeds.append({"color": 361051, "title": "New member", "description": message})
    if removed:
        messages = split_message(removed)
        for message in messages:
            embeds.append({"color": 16711680, "title": "Member left or kicked", "description": message})
    if promoted:
        messages = split_message(promoted)
        for message in messages:
            embeds.append({"color": 16776960, "title": "Member promoted", "description": message})
    if demoted:
        messages = split_message(demoted)
        for message in messages:
            embeds.append({"color": 16753920, "title": "Member demoted", "description": message})
    if deleted:
        messages = split_message(deleted)
        for message in messages:
            embeds.append({"color": 0, "title": "Members deleted", "description": message})
    if name_changes:
        messages = split_message(name_changes)
        for message in messages:
            embeds.append({"color": 65535, "title": "Member changed name", "description": message})
    if title_changes:
        messages = split_message(title_changes)
        for message in messages:
            embeds.append({"color": 12915437, "title": "Title changed", "description": message})
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
        if current_length+len(embed["description"]) > 6000 or len(batches) == 10:
            batches.append(current_batch)
            current_length = 0
            current_batch = []
            continue
        current_batch.append(embed)
        current_length += len(embed["description"])

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
    load_config()
    while True:
        # Iterate through each guild in the configuration file
        for cfg_guild in cfg["guilds"]:
            if cfg_guild.get("webhook_url", cfg.get("webhook_url")) is None:
                log.error("Missing Webhook URL in config.json")
                exit()
            name = cfg_guild.get("name")
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
            changes = compare_guilds(guild_data, new_guild_data)
            if cfg_guild["override_image"]:
                cfg_guild["avatar_url"] = new_guild_data.logo_url
            embeds = build_embeds(changes)
            publish_changes(cfg_guild.get("webhook_url", cfg.get("webhook_url")), embeds, guild_data.name,
                            cfg_guild["avatar_url"], member_count)
            log.info(name + " - Scanning done")
            time.sleep(2)
        time.sleep(5 * 60)


if __name__ == "__main__":
    scan_guilds()
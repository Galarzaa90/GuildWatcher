import json
import logging
import pickle
import time
from enum import Enum, auto

import requests
from tibiapy import Character, Guild, GuildMember

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s: %(message)s'))
consoleHandler.setLevel(logging.DEBUG)
log.addHandler(consoleHandler)


# Change strings
FMT_CHANGE = "[{m.name}]({m.url}) - **{m.level}** **{v}** {e} - Rank: **{m.rank}** - Joined **{m.joined}**\n"
FMT_NEW_MEMBER = "[{m.name}]({m.url}) - **{m.level}** **{v}** {e}\n"
FMT_NAME_CHANGE = "{extra} -> [{m.name}]({m.url}) - **{m.level}** **{v}** {e}\n"
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
        self.member = member  # type: GuildMember
        self.type = _type  # type: ChangeType
        self.extra = extra


class ChangeType(Enum):
    """Contains all the possible changes that can be found."""
    NEW_MEMBER = auto()  #: New member joined the guild.
    DELETED = auto()  #: Member was deleted from the game.
    REMOVED = auto()  #: Member was kicked or left the guild.
    NAME_CHANGE = auto()  #: Member changed their name.
    TITLE_CHANGE = auto()  #: Member title was changed.
    DEMOTED = auto()  #: Member was demoted.
    PROMOTED = auto()  #: Member was promoted.


cfg = {}


def load_config():
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
    with open(file, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_data(file):
    try:
        with open(file, "rb") as f:
            return pickle.load(f)
    except ValueError:
        return None
    except FileNotFoundError:
        return None


def get_character(name, tries=5):  # pragma: no cover
    try:
        url = Character.get_url(name)
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
    char = Character.from_content(content)
    return char


def get_guild(name, tries=5):  # pragma: no cover
    try:
        r = requests.get(Guild.get_url(name))
        content = r.text
    except requests.RequestException:
        if tries == 0:
            return None
        else:
            tries -= 1
            return get_guild(name, tries)

    guild = Guild.from_content(content)

    return guild


def compare_guilds(before, after):
    """
    Compares the same guild at different points in time, to obtain the changes made.

    It returns all the changes found.

    :param before: The state of the guild in the previous saved state.
    :type before: Guild
    :param after:  The current state of the guild.
    :type after: Guild
    :return: A list of all the changes found.
    :rtype: list of Change
    """
    changes = []
    ranks = after.ranks[:]
    before_members = before.members[:]
    after_members = after.members[:]
    for member in before_members:  # type: GuildMember
        found = False
        for member_new in after_members:  # type: GuildMember
            if member != member_new:
                continue
            # Member still in guild, remove it from list
            after_members.remove(member_new)
            found = True
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
        if not found:
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
    joined = after_members[:]
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
        embeds.append({"color": 361051, "title": "New member", "description": new_members})
    if removed:
        embeds.append({"color": 16711680, "title": "Member left or kicked", "description": removed})
    if promoted:
        embeds.append({{"color": 16776960, "title": "Member promoted", "description": promoted}})
    if demoted:
        embeds.append({"color": 16753920, "title": "Member demoted", "description": demoted})
    if deleted:
        embeds.append({"color": 0, "title": "Members deleted", "description": deleted})
    if name_changes:
        embeds.append({"color": 65535, "title": "Member changed name", "description": name_changes})
    if title_changes:
        embeds.append({"color": 12915437, "title": "Title changed", "description": title_changes})
    return embeds


def announce_changes(guild_config, name, changes, joined, total):
    new_member_format = "[{m.name}]({m.url}) - Level **{m.level}** **{m.vocation}** {emoji}"
    member_format = "[{m.name}]({m.url}) - Level **{m.level}** **{m.vocation}** {emoji} - Rank: **{m.rank}** - " \
                    "Joined: **{m.joined}**"
    name_changed_format = "{former_name} → [{m.name}]({m.url}) - Level **{m.level}** **{m.vocation}** {emoji} - " \
                          "Rank: **{m.rank}**"
    title_changed_format = "[{m.name}]({m.url}) - {old_title} → {m.title} " \
                           "- Level **{m.level}** **{m.vocation}** {emoji} - Rank: **{m.rank}**"
    body = {
        "username": name if guild_config.get("override_name", False) else cfg.get("name"),
        "avatar_url": guild_config.get("avatar_url", cfg.get("avatar_url")),
        "embeds": [],
    }
    joined_str = ""
    removed = ""
    name_changed = ""
    deleted = ""
    promoted = ""
    demoted = ""
    title_changed = ""

    for change in changes:
        emoji = vocation_emojis.get(change["member"].vocation, "")
        change["member"].vocation = vocation_abbreviations.get(change["member"].vocation, "")
        if change["type"] == "promotion":
            promoted += member_format.format(m=change["member"], emoji=emoji) + "\n"
        if change["type"] == "removed":
            removed += member_format.format(m=change["member"], emoji=emoji) + "\n"
        if change["type"] == "demotion":
            demoted += member_format.format(m=change["member"], emoji=emoji) + "\n"
        if change["type"] == "name_change":
            name_changed += name_changed_format.format(m=change["member"], emoji=emoji,
                                                       former_name=change["former_name"]) + "\n"
        if change["type"] == "title":
            title_changed += title_changed_format.format(m=change["member"], emoji=emoji,
                                                         old_title=change["old_title"]) + "\n"

    for join in joined:
        emoji = vocation_emojis.get(join.vocation, "")
        join.vocation = vocation_abbreviations.get(join.vocation, "")
        joined_str += new_member_format.format(m=join, emoji=emoji) + "\n"

    if joined_str or deleted or removed:
        body["content"] = "The guild now has **{0:,}** members.".format(total)

    if joined_str:
        title = "New member"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        new = {"color": 361051, "title": title, "description": joined_str}
        body["embeds"].append(new)

    if removed:
        title = "Member left or kicked"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        new = {"color": 16711680, "title": title, "description": removed}
        body["embeds"].append(new)

    if promoted:
        title = "Member promoted"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        new = {"color": 16776960, "title": title, "description": promoted}
        body["embeds"].append(new)

    if demoted:
        title = "Member demoted"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        new = {"color": 16753920, "title": title, "description": demoted}
        body["embeds"].append(new)

    if deleted:
        title = "Member deleted"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        new = {"color": 0, "title": title, "description": deleted}
        body["embeds"].append(new)

    if name_changed:
        title = "Member changed name"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        new = {"color": 65535, "title": title, "description": name_changed}
        body["embeds"].append(new)

    if title_changed:
        title = "Title changed"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        new = {"color": 12915437, "title": title, "description": title_changed}
        body["embeds"].append(new)

    requests.post(guild_config.get("webhook_url", cfg.get("webhook_url")),
                  data=json.dumps(body), headers={"Content-Type": "application/json"})


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

            log.info(name + "- Scanning guild...")
            new_guild_data = get_guild(name)
            if new_guild_data is None:
                log.error(name + " - Error: Guild doesn't exist")
                continue
            save_data(guild_file, new_guild_data)
            # Looping through members
            total_members = new_guild_data.member_count
            changes = compare_guilds(guild_data, new_guild_data)
            if cfg_guild["override_image"]:
                cfg_guild["avatar_url"] = new_guild_data.logo_url
            announce_changes(cfg_guild, name, changes, total_members)
            log.info(name + " - Scanning done")
            time.sleep(2)
        time.sleep(5 * 60)


if __name__ == "__main__":
    scan_guilds()
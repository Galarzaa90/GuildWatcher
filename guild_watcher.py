import json
import logging
import pickle
import re
import time
import urllib.parse

import requests

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s: %(message)s'))
consoleHandler.setLevel(logging.DEBUG)
log.addHandler(consoleHandler)

cfg = {}
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


def get_character(name, tries=5):
    """Returns a dictionary with a player's info
    The dictionary contains the following keys: name, deleted, level, vocation, world, residence,
    married, gender, guild, last,login, chars*.
        *chars is list that contains other characters in the same account (if not hidden).
        Each list element is dictionary with the keys: name, world.
    May return ERROR_DOESNTEXIST or ERROR_NETWORK accordingly."""
    url_character = "https://secure.tibia.com/community/?subtopic=characters&name="
    try:
        url = url_character + urllib.parse.quote(name.encode('iso-8859-1'))
    except UnicodeEncodeError:
        return None
    char = dict()

    # Fetch website
    try:
        r = requests.get(url=url)
        content = r.text
    except requests.RequestException:
        if tries == 0:
            return {"error": "Network"}
        else:
            tries -= 1
            return get_character(name, tries)

    # Trimming content to reduce load
    try:
        startIndex = content.index('<div class="BoxContent"')
        endIndex = content.index("<B>Search Character</B>")
        content = content[startIndex:endIndex]
    except ValueError:
        # Website fetch was incomplete, due to a network error
        if tries == 0:
            return None
        else:
            tries -= 1
            time.sleep(2)
            return get_character(name, tries)
    # Check if player exists
    if "Name:</td><td>" not in content:
        return None

    # Name
    m = re.search(r'Name:</td><td>([^<,]+)', content)
    if m:
        char['name'] = m.group(1).strip()

    # Vocation
    m = re.search(r'Vocation:</td><td>([^<]+)', content)
    if m:
        char['vocation'] = m.group(1)

    # World
    m = re.search(r'World:</td><td>([^<]+)', content)
    if m:
        char['world'] = m.group(1)

    return char


def get_guild_info(name, tries=5):
    try:
        r = requests.get("https://secure.tibia.com/community/", params={"subtopic":"guilds","page":"view","GuildName":name})
        content = r.text
    except requests.RequestException:
        if tries == 0:
            return {"error": "Network"}
        else:
            tries -= 1
            return get_guild_info(name, tries)

    try:
        start_index = content.index('<div class="BoxContent"')
        end_index = content.index('<div id="ThemeboxesColumn" >')
        content = content[start_index:end_index]
    except ValueError:
        # Website fetch was incomplete, due to a network error
        return {"error": "Network"}

    if '<div class="Text" >Error</div>' in content:
        return {"error": "NotFound"}

    guild = {}
    # Logo URL
    m = re.search(r'<IMG SRC=\"([^\"]+)\" W', content)
    if m:
        guild['logo_url'] = m.group(1)

        # Regex pattern to fetch members
        regex_members = r'<TR BGCOLOR=#[\dABCDEF]+><TD>(.+?)</TD>\s</td><TD><A HREF="https://secure.tibia.com/community/\?subtopic=characters&name=(.+?)">.+?</A> *\(*(.*?)\)*</TD>\s<TD>(.+?)</TD>\s<TD>(.+?)</TD>\s<TD>(.+?)</TD>'
        pattern = re.compile(regex_members, re.MULTILINE + re.S)

        m = re.findall(pattern, content)
        guild['members'] = []
        # Check if list is empty
        if m:
            # Building dictionary list from members
            last_rank = ""
            guild["ranks"] = []
            for (rank, name, title, vocation, level, joined) in m:
                rank = last_rank if (rank == '&#160;') else rank
                if rank not in guild["ranks"]:
                    guild["ranks"].append(rank)
                last_rank = rank
                name = requests.utils.unquote(name).replace("+", " ")
                joined = joined.replace('&#160;', '-')
                guild['members'].append({'rank': rank, 'name': name, 'title': title, 'vocation': vocation,
                                         'level': level, 'joined': joined})

    return guild


vocation_emojis = {
    "Druid": "\U00002744",
    "Elder Druid": "\U00002744",
    "Knight": "\U0001F6E1",
    "Elite Knight": "\U0001F6E1",
    "Sorcerer": "\U0001F525",
    "Master Sorcerer": "\U0001F525",
    "Paladin": "\U0001F3F9",
    "Royal Paladin": "\U0001F3F9",
}

vocation_abbreviations = {
    "Druid": "D",
    "Elder Druid": "ED",
    "Knight": "K",
    "Elite Knight": "EK",
    "Sorcerer": "S",
    "Master Sorcerer": "MS",
    "Paladin": "P",
    "Royal Paladin": "RP",
    "None": "N",
}


def announce_changes(guild_config, name, changes, joined, total):
    new_member_format = "[{name}]({url}) - Level **{level}** **{vocation}** {emoji}"
    member_format = "[{name}]({url}) - Level **{level}** **{vocation}** {emoji} - Rank: **{rank}** - " \
                    "Joined: **{joined}**"
    name_changed_format = "{former_name} \U00002192 [{name}]({url}) - Level **{level}** **{vocation}** {emoji} - " \
                          "Rank: **{rank}**"
    title_changed_format = "[{name}]({url}) - {old_title} \U00002192 {title} - Level **{level}** **{vocation}** {emoji} - " \
                          "Rank: **{rank}**"
    body = {
        "username": guild["name"] if guild_config.get("override_name", False) else cfg.get("name"),
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

    for m in (changes+joined):
        m["url"] = "https://secure.tibia.com/community/?subtopic=characters&name=" + requests.utils.quote(m["name"])
        m["emoji"] = vocation_emojis.get(m["vocation"], "")
        m["vocation"] = vocation_abbreviations.get(m["vocation"], "")
        change_type = m.get("type", "")
        if change_type == "removed":
            removed += member_format.format(**m) + "\n"
        elif change_type == "promotion":
            promoted += member_format.format(**m) + "\n"
        elif change_type == "demotion":
            demoted += member_format.format(**m) + "\n"
        elif change_type == "namechange":
            name_changed += name_changed_format.format(**m) + "\n"
        elif change_type == "titlechange":
            if m["old_title"] == "":
                m["old_title"] = "None"
            if m["title"] == "":
                m["title"] = "None"
            title_changed += title_changed_format.format(**m) + "\n"
        elif change_type == "deleted":
            deleted += member_format.format(**m) + "\n"
        else:
            joined_str += new_member_format.format(**m) + "\n"

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

    requests.post(guild.get("webhook_url", guild_config.get("webhook_url", cfg.get("webhook_url"))),
                  data=json.dumps(body), headers={"Content-Type": "application/json"})


def main():
    while True:
        # Iterate each guild
        for guild in cfg["guilds"]:
            if guild.get("webhook_url", cfg.get("webhook_url")) is None:
                log.error("Missing Webhook URL in config.json")
                exit()
            name = guild.get("name", None)
            if name is None:
                log.error("Guild missing name.")
                time.sleep(5)
                continue
            guild_file = name+".data"
            guild_data = load_data(guild_file)
            if guild_data is None:
                log.info(name + " - No previous data found. Saving current data.")
                guild_data = get_guild_info(name)
                error = guild_data.get("error")
                if error is not None:
                    log.error(name +" - Error: " + error)
                    continue
                save_data(guild_file, guild_data)
                time.sleep(5)
                continue

            log.info(name + " - Scanning guild...")
            new_guild_data = get_guild_info(name)
            error = new_guild_data.get("error")
            if error is not None:
                log.error(name + " - Error: "+error)
                continue
            save_data(guild_file, new_guild_data)
            changes = []
            # Looping previously saved members
            total_members = len(new_guild_data["members"])
            for member in guild_data["members"]:
                found = False
                # Looping current members
                for _member in new_guild_data["members"]:
                    if member["name"] == _member["name"]:
                        # Member still in guild, we remove it from list for faster iterating
                        new_guild_data["members"].remove(_member)
                        found = True
                        # Rank changed
                        if member["rank"] != _member["rank"]:
                            try:
                                if new_guild_data["ranks"].index(member["rank"]) < \
                                        new_guild_data["ranks"].index(_member["rank"]):
                                    # Demoted
                                    log.info("Member demoted: " + _member["name"])
                                    _member["type"] = "demotion"
                                    changes.append(_member)
                                else:
                                    # Promoted
                                    log.info("Member promoted: " + _member["name"])
                                    _member["type"] = "promotion"
                                    changes.append(_member)
                            except ValueError:
                                # Todo: Handle this
                                pass
                        # Title changed
                        if member["title"] != _member["title"]:
                            _member["type"] = "titlechange"
                            _member["old_title"] = member["title"]
                            log.info("Member title changed: {name} - {title}".format(**member))
                            changes.append(_member)
                        break
                if not found:
                    # We check if it was a namechange or character deleted
                    log.info("Checking character {name}".format(**member))
                    char = get_character(member["name"])
                    # Character was deleted (or maybe namelocked)
                    if char is None:
                        member["type"] = "deleted"
                        changes.append(member)
                        continue
                    # Character has a new name and matches someone in guild, meaning it got a name change
                    _found = False
                    for _member in new_guild_data["members"]:
                        if char["name"] == _member["name"]:
                            _member["former_name"] = member["name"]
                            _member["type"] = "namechange"
                            changes.append(_member)
                            new_guild_data["members"].remove(_member)
                            log.info("{former_name} changed name to {name}".format(**_member))
                            _found = True
                            break
                    if _found:
                        continue
                    log.info("Member no longer in guild: " + member["name"])
                    member["type"] = "removed"
                    changes.append(member)
            joined = new_guild_data["members"][:]
            if len(joined) > 0:
                log.info("New members found: " + ",".join(m["name"] for m in joined))
            if guild["override_image"]:
                guild["avatar_url"] = new_guild_data["logo_url"]
            announce_changes(guild, name, changes, joined, total_members)
            log.info(name + " - Scanning done")
            time.sleep(2)
        time.sleep(5*60)


if __name__ == "__main__":
    main()
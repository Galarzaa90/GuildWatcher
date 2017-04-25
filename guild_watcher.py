import re
import urllib.parse

import requests
import pickle
import json
import time

cfg = {}
try:
    with open('config.json') as json_data:
        cfg = json.load(json_data)
except FileNotFoundError:
    print("Missing config.json file. Check the example file.")
    exit()
except ValueError:
    print("Malformed config.json file.")
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


def announce_changes(guild_config, name, joined, removed, promoted, demoted, deleted, name_changed):
    new_member_format = "[{name}]({url}) - Level **{level}** **{vocation}** {emoji}"
    member_format = "[{name}]({url}) - Level **{level}** **{vocation}** {emoji} - Rank: **{rank}** - " \
                    "Joined: **{joined}**"
    name_changed_format = "{former_name} \U00002192 [{name}]({url}) - Level **{level}** **{vocation}** {emoji} - " \
                          "Rank: **{rank}**"
    body = {
        "username": guild["name"] if guild_config.get("override_name", False) else cfg.get("name"),
        "avatar_url": guild_config.get("avatar_url", cfg.get("avatar_url")),
        "embeds": [],
    }
    if joined:
        title = "New member" if len(joined) == 1 else "New members"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        description = ""
        for m in joined:
            m["url"] = "https://secure.tibia.com/community/?subtopic=characters&name=" + requests.utils.quote(m["name"])
            m["emoji"] = vocation_emojis.get(m["vocation"], "")
            m["vocation"] = vocation_abbreviations.get(m["vocation"], "")
            description += new_member_format.format(**m)+"\n"
        new = {"color": 361051, "title": title, "description": description}
        body["embeds"].append(new)

    if removed:
        title = "Member left or kicked" if len(removed) == 1 else "Members left or kicked"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        description = ""
        for m in removed:
            m["url"] = "https://secure.tibia.com/community/?subtopic=characters&name=" + requests.utils.quote(m["name"])
            m["emoji"] = vocation_emojis.get(m["vocation"], "")
            m["vocation"] = vocation_abbreviations.get(m["vocation"], "")
            description += member_format.format(**m) + "\n"
        new = {"color": 16711680, "title": title, "description": description}
        body["embeds"].append(new)

    if promoted:
        title = "Member promoted" if len(promoted) == 1 else "Members promoted"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        description = ""
        for m in promoted:
            m["url"] = "https://secure.tibia.com/community/?subtopic=characters&name=" + requests.utils.quote(m["name"])
            m["emoji"] = vocation_emojis.get(m["vocation"], "")
            m["vocation"] = vocation_abbreviations.get(m["vocation"], "")
            description += member_format.format(**m) + "\n"
        new = {"color": 16776960, "title": title, "description": description}
        body["embeds"].append(new)

    if demoted:
        title = "Member demoted" if len(demoted) == 1 else "Members demoted"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        description = ""
        for m in demoted:
            m["url"] = "https://secure.tibia.com/community/?subtopic=characters&name=" + requests.utils.quote(m["name"])
            m["emoji"] = vocation_emojis.get(m["vocation"], "")
            m["vocation"] = vocation_abbreviations.get(m["vocation"], "")
            description += member_format.format(**m) + "\n"
        new = {"color": 16753920, "title": title, "description": description}
        body["embeds"].append(new)

    if deleted:
        title = "Member deleted" if len(deleted) == 1 else "Members deleted"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        description = ""
        for m in deleted:
            m["url"] = "https://secure.tibia.com/community/?subtopic=characters&name=" + requests.utils.quote(m["name"])
            m["emoji"] = vocation_emojis.get(m["vocation"], "")
            m["vocation"] = vocation_abbreviations.get(m["vocation"], "")
            description += member_format.format(**m) + "\n"
        new = {"color": 0, "title": title, "description": description}
        body["embeds"].append(new)

    if name_changed:
        title = "Member changed name" if len(name_changed) == 1 else "Members changed name"
        if not guild_config.get("override_name", False):
            title += " in {0}".format(name) if len(cfg["guilds"]) > 1 else ""
        description = ""
        for m in name_changed:
            m["url"] = "https://secure.tibia.com/community/?subtopic=characters&name=" + requests.utils.quote(m["name"])
            m["emoji"] = vocation_emojis.get(m["vocation"], "")
            m["vocation"] = vocation_abbreviations.get(m["vocation"], "")
            description += name_changed_format.format(**m) + "\n"
        new = {"color": 65535, "title": title, "description": description}
        body["embeds"].append(new)

    requests.post(guild.get("webhook_url", guild_config.get("webhook_url", cfg.get("webhook_url"))),
                  data=json.dumps(body), headers={"Content-Type": "application/json"})

if __name__ == "__main__":
    while True:
        # Iterate each guild
        for guild in cfg["guilds"]:
            if guild.get("webhook_url", cfg.get("webhook_url")) is None:
                print("Missing Webhook URL in config.json")
                exit()
            name = guild.get("name", None)
            if name is None:
                print("Guild missing name.")
                time.sleep(5)
                continue
            guild_file = name+".data"
            guild_data = load_data(guild_file)
            if guild_data is None:
                print(name, "- No previous data found. Saving current data.")
                guild_data = get_guild_info(name)
                error = guild_data.get("error")
                if error is not None:
                    print(name, "- Error:", error)
                    continue
                save_data(guild_file, guild_data)
                time.sleep(5)
                continue

            print(name, "- Scanning guild")
            new_guild_data = get_guild_info(name)
            error = new_guild_data.get("error")
            if error is not None:
                print(name, "- Error:", error)
                continue
            save_data(guild_file, new_guild_data)
            removed = []
            joined = []
            promoted = []
            demoted = []
            deleted = []
            name_changed = []
            # Looping previously saved members
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
                                    print("Member demoted:", _member["name"])
                                    demoted.append(_member)
                                else:
                                    # Promoted
                                    print("Member promoted:", _member["name"])
                                    promoted.append(_member)
                            except ValueError:
                                # Todo: Handle this
                                pass
                        break
                if not found:
                    # We check if it was a namechange or character deleted
                    print("Checking character {name}".format(**member))
                    char = get_character(member["name"])
                    # Character was deleted (or maybe namelocked)
                    if char is None:
                        deleted.append(member)
                        continue
                    # Character has a new name and matches someone in guild, meaning it got a name change
                    _found = False
                    for _member in new_guild_data["members"]:
                        if char["name"] == _member["name"]:
                            _member["former_name"] = member["name"]
                            name_changed.append(_member)
                            new_guild_data["members"].remove(_member)
                            print("{former_name} changed name to {name}".format(**_member))
                            _found = True
                            break
                    if _found:
                        continue
                    print("Member no longer in guild: ", member["name"])
                    removed.append(member)
            joined = new_guild_data["members"][:]
            if len(joined) > 0:
                print("New members found: " +",".join(m["name"] for m in joined))
            if guild["override_image"]:
                guild["avatar_url"] = new_guild_data["logo_url"]
            announce_changes(guild, name, joined, removed, promoted, demoted, deleted, name_changed)
            time.sleep(2)
        time.sleep(5*60)



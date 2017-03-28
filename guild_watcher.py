import re
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


def announce_changes(guild_config, name, joined, removed, promoted, demoted):
    new_member_format = "[{name}]({url}) - Level **{level}** **{vocation}** {emoji}"
    removed_member_format = "[{name}]({url}) - Level **{level}** **{vocation}** {emoji} - " \
                            "Rank: **{rank}** - Joined: **{joined}**"
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
            description += removed_member_format.format(**m) + "\n"
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
            description += removed_member_format.format(**m) + "\n"
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
            description += removed_member_format.format(**m) + "\n"
        new = {"color": 16753920, "title": title, "description": description}
        body["embeds"].append(new)

    requests.post(guild.get("webhook_url", cfg.get("webhook_url")), data=json.dumps(body),
                  headers={"Content-Type": "application/json"})

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
            removed_members = []
            new_members = []
            promoted = []
            demoted = []
            for member in guild_data["members"]:
                found = False
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
                    print("Member no longer in guild: ", member["name"])
                    removed_members.append(member)
            new_members = new_guild_data["members"][:]
            if len(new_members) > 0:
                print("New members found: "+",".join(m["name"] for m in new_members))
            if guild["override_image"]:
                guild["avatar_url"] = new_guild_data["logo_url"]
            announce_changes(guild, name, new_members, removed_members, promoted, demoted)
            time.sleep(10)
        time.sleep(5*60)



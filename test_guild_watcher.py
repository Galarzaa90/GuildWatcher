import copy
import datetime
import unittest
from datetime import date
from unittest.mock import MagicMock

import requests
from tibiapy import Guild, GuildMember, Character

import guild_watcher
from guild_watcher import Change, ChangeType


class TestGuildWatcher(unittest.TestCase):
    def setUp(self):
        self.guild = Guild("Test Guild", "Antica")
        today = datetime.date.today()
        self.guild.members = [
            GuildMember("Galarzaa", "Leader", level=285, vocation="Royal Paladin", joined=today),
            GuildMember("Nezune", "Vice", level=412, vocation="Elite Knight", title="Nab", joined=today),
            GuildMember("Ondskan", "Vice", level=437, vocation="Royal Paladin", joined=today),
            GuildMember("Faenryz", "Vice", level=207, vocation="Royal Paladin", joined=today),
            GuildMember("Tschis", "Elite", level=205, vocation="Druid", joined=today),
            GuildMember("John Doe", "Elite", level=34, vocation="Master Sorcerer", joined=today),
            GuildMember("Jane Doe", "Recruit", level=55, vocation="Sorcerer", joined=today),
            GuildMember("Fahgnoli", "Recruit", level=404, vocation="Master Sorcerer", joined=today)
        ]
        self.guild_after = copy.deepcopy(self.guild)

    def testPromotedMember(self):
        new_rank = "Elite"
        promoted_member = self.guild_after.members[6]
        promoted_member.rank = new_rank

        changes = guild_watcher.compare_guilds(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.PROMOTED)
        self.assertEqual(changes[0].member.name, promoted_member.name)
        self.assertEqual(changes[0].member.rank, promoted_member.rank)

    def testDemotedMember(self):
        new_rank = "Recruit"
        demoted_member = self.guild_after.members[5]
        demoted_member.rank = new_rank

        changes = guild_watcher.compare_guilds(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.DEMOTED)
        self.assertEqual(changes[0].member.name, demoted_member.name)
        self.assertEqual(changes[0].member.rank, demoted_member.rank)

    def testNewMember(self):
        new_member = GuildMember("Noob", "Recruit", level=12, vocation="Knight")
        self.guild_after.members.append(new_member)

        changes = guild_watcher.compare_guilds(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.NEW_MEMBER)
        self.assertEqual(changes[0].member.name, new_member.name)

    def testTitleChange(self):
        new_title = "Even Nabber"
        affected_member = self.guild_after.members[1]
        old_title = affected_member.title
        affected_member.title = new_title
        changes = guild_watcher.compare_guilds(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.TITLE_CHANGE)
        self.assertEqual(changes[0].member.name, affected_member.name)
        self.assertEqual(changes[0].member.title, new_title)
        self.assertEqual(changes[0].extra, old_title)

    def testMemberDeleted(self):
        # Kick member at position 6
        kicked = self.guild_after.members.pop(6)

        # Mock get_character to imitate non existing character
        guild_watcher.get_character = MagicMock(return_value=None)

        changes = guild_watcher.compare_guilds(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.DELETED)
        self.assertEqual(changes[0].member.name, kicked.name)
        guild_watcher.get_character.assert_called_with(kicked.name)

    def testMemberKicked(self):
        # Kick member at position 1
        kicked = self.guild_after.members.pop(1)

        # Mock get_character to imitate existing character
        guild_watcher.get_character = MagicMock(return_value=Character(name=kicked.name))

        changes = guild_watcher.compare_guilds(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.REMOVED)
        self.assertEqual(changes[0].member.name, kicked.name)
        guild_watcher.get_character.assert_called_with(kicked.name)

    def testMemberNameChanged(self):
        # Change name of first member
        new_name = "Galarzaa Fidera"
        affected_member = self.guild_after.members[0]
        old_name = affected_member.name
        affected_member.name = new_name

        # Checking the missing character should return the new name
        guild_watcher.get_character = MagicMock(return_value=Character(name=new_name))

        changes = guild_watcher.compare_guilds(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.NAME_CHANGE)
        self.assertEqual(changes[0].member.name, new_name)
        self.assertEqual(changes[0].extra, old_name)
        guild_watcher.get_character.assert_called_with(old_name)

    def testDataIntegrity(self):
        guild_watcher.save_data(".tmp.data", self.guild)
        saved_guild = guild_watcher.load_data(".tmp.data")

        changes = guild_watcher.compare_guilds(self.guild, saved_guild)

        self.assertFalse(changes)

    def testEmbeds(self):
        changes = [
            Change(ChangeType.NEW_MEMBER, GuildMember("Noob", "Recruit", level=19, vocation="Druid")),
            Change(ChangeType.REMOVED, GuildMember("John", "Member", level=56, vocation="Druid", joined=date.today())),
            Change(ChangeType.NAME_CHANGE, GuildMember("Tschis", "Vice", level=205, vocation="Druid"), "Tschas"),
            Change(ChangeType.DELETED, GuildMember("Botter", "Vice", level=444, vocation="Elite Knight",
                                                   joined=date.today())),
            Change(ChangeType.TITLE_CHANGE, GuildMember("Nezune", level=404, rank="Vice", vocation="Elite Knight",
                                                        title="Nab"), "Challenge Pls"),
            Change(ChangeType.PROMOTED, GuildMember("Old", "Rank", level=142, vocation="Royal Paladin",
                                                    joined=date.today())),
            Change(ChangeType.DEMOTED, GuildMember("Jane", "Rank", level=89, vocation="Master Sorcerer",
                                                   joined=date.today()))
        ]
        embeds = guild_watcher.build_embeds(changes)
        self.assertTrue(embeds)
        requests.post = MagicMock()
        guild_watcher.publish_changes("https://canary.discordapp.com/api/webhooks/webhook", embeds)
        self.assertTrue(requests.post.call_count)

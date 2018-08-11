import unittest
from unittest.mock import MagicMock

from tibiapy import Guild, GuildMember, Character
from datetime import date

import guild_watcher
from guild_watcher import Change, ChangeType


class TestGuildWatcher(unittest.TestCase):

    def testPromotedMember(self):
        guild_before = Guild(name="Test Guild", world="Antica")
        guild_after = Guild(name="Test Guild", world="Antica")

        guild_before.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
            GuildMember(name="Jane Doe", rank="Vice Leader"),
            GuildMember(name="Tschas", rank="Member"),
            GuildMember(name="John Doe", rank="Member"),
        ]

        guild_after.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
            GuildMember(name="Jane Doe", rank="Vice Leader"),
            GuildMember(name="Tschas", rank="Vice Leader"),
            GuildMember(name="John Doe", rank="Member"),
        ]
        changes = guild_watcher.compare_guilds(guild_before, guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.PROMOTED)
        self.assertEqual(changes[0].member.name, "Tschas")

    def testDemotedMember(self):
        guild_before = Guild(name="Test Guild", world="Antica")
        guild_after = Guild(name="Test Guild", world="Antica")

        guild_before.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
            GuildMember(name="Tschas", rank="Vice Leader"),
            GuildMember(name="Jane Doe", rank="Vice Leader"),
            GuildMember(name="John Doe", rank="Member"),
        ]

        guild_after.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
            GuildMember(name="Tschas", rank="Vice Leader"),
            GuildMember(name="Jane Doe", rank="Member"),
            GuildMember(name="John Doe", rank="Member"),
        ]
        changes = guild_watcher.compare_guilds(guild_before, guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.DEMOTED)
        self.assertEqual(changes[0].member.name, "Jane Doe")

    def testNewMember(self):
        guild_before = Guild(name="Test Guild", world="Antica")
        guild_after = Guild(name="Test Guild", world="Antica")

        guild_before.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
        ]

        guild_after.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
            GuildMember(name="Tschas", rank="Vice Leader"),
        ]
        changes = guild_watcher.compare_guilds(guild_before, guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.NEW_MEMBER)
        self.assertEqual(changes[0].member.name, "Tschas")

    def testTitleChange(self):
        guild_before = Guild(name="Test Guild", world="Antica")
        guild_after = Guild(name="Test Guild", world="Antica")

        guild_before.members = [
            GuildMember(name="Galarzaa", rank="Leader", title="Dictator"),
        ]

        guild_after.members = [
            GuildMember(name="Galarzaa", rank="Leader", title="Gallan"),
        ]
        changes = guild_watcher.compare_guilds(guild_before, guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.TITLE_CHANGE)
        self.assertEqual(changes[0].member.name, "Galarzaa")
        self.assertEqual(changes[0].extra, "Dictator")

    def testMemberDeleted(self):
        guild_watcher.get_character = MagicMock(return_value=None)

        guild_before = Guild(name="Test Guild", world="Antica")
        guild_after = Guild(name="Test Guild", world="Antica")

        guild_before.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
            GuildMember(name="Tschas", rank="Vice Leader"),
        ]

        guild_after.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
        ]
        changes = guild_watcher.compare_guilds(guild_before, guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.DELETED)
        self.assertEqual(changes[0].member.name, "Tschas")
        guild_watcher.get_character.assert_called()

    def testMemberKicked(self):
        char = Character()
        char.name = "Tschas"
        guild_watcher.get_character = MagicMock(return_value=Character())

        guild_before = Guild(name="Test Guild", world="Antica")
        guild_after = Guild(name="Test Guild", world="Antica")

        guild_before.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
            GuildMember(name="Tschas", rank="Vice Leader"),
        ]

        guild_after.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
        ]
        changes = guild_watcher.compare_guilds(guild_before, guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.REMOVED)
        self.assertEqual(changes[0].member.name, "Tschas")
        guild_watcher.get_character.assert_called()

    def testMemberNameChanged(self):
        guild_before = Guild(name="Test Guild", world="Antica")
        guild_after = Guild(name="Test Guild", world="Antica")

        guild_before.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
            GuildMember(name="Tschas", rank="Vice Leader"),
        ]

        guild_after.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
            GuildMember(name="Tschis", rank="Leader"),
        ]

        char = Character()
        char.name = "Tschis"
        guild_watcher.get_character = MagicMock(return_value=char)
        changes = guild_watcher.compare_guilds(guild_before, guild_after)
        self.assertEqual(changes[0].type, guild_watcher.ChangeType.NAME_CHANGE)
        self.assertEqual(changes[0].member.name, "Tschis")
        self.assertEqual(changes[0].extra, "Tschas")
        guild_watcher.get_character.assert_called()

    def testDataIntegrity(self):
        guild = Guild(name="Test Guild", world="Antica")
        guild.members = [
            GuildMember(name="Galarzaa", rank="Leader"),
            GuildMember(name="Tschas", rank="Vice Leader"),
        ]
        guild_watcher.save_data(".tmp.data", guild)
        saved_guild = guild_watcher.load_data(".tmp.data")

        changes = guild_watcher.compare_guilds(guild, saved_guild)

        self.assertFalse(changes)

    def testEmbeds(self):
        changes = [
            Change(ChangeType.NEW_MEMBER, GuildMember("Noob", "Recruit", level=19, vocation="Druid")),
            Change(ChangeType.REMOVED, GuildMember("Noob", "Recruit", level=19, vocation="Druid", joined=date.today()))
        ]
        embeds = guild_watcher.build_embeds(changes)
        print(embeds)
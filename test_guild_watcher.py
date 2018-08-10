import unittest
from unittest.mock import MagicMock

from tibiapy import Guild, GuildMember, Character

import guild_watcher


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
        self.assertEqual(changes[0]["type"], "promotion")
        self.assertEqual(changes[0]["member"].name, "Tschas")

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
        self.assertEqual(changes[0]["type"], "demotion")
        self.assertEqual(changes[0]["member"].name, "Jane Doe")

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
        self.assertEqual(changes[0]["type"], "joined")
        self.assertEqual(changes[0]["member"].name, "Tschas")

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
        self.assertEqual(changes[0]["type"], "title")
        self.assertEqual(changes[0]["member"].name, "Galarzaa")
        self.assertEqual(changes[0]["old_title"], "Dictator")

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
        self.assertEqual(changes[0]["type"], "deleted")
        self.assertEqual(changes[0]["member"].name, "Tschas")
        guild_watcher.get_character.assert_called()

    def testMemberKicked(self):
        char = Character()
        char.name = "Tschass"
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
        self.assertEqual(changes[0]["type"], "removed")
        self.assertEqual(changes[0]["member"].name, "Tschas")
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
        self.assertEqual(changes[0]["type"], "name_change")
        self.assertEqual(changes[0]["member"].name, "Tschis")
        guild_watcher.get_character.assert_called()
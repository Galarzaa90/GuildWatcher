import unittest

from tibiapy import Guild, GuildMember

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


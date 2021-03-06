import copy
import datetime
import logging
import unittest
from datetime import date
from unittest.mock import MagicMock, patch, mock_open

import requests
from tibiapy import Guild, GuildMember, Character, GuildInvite, Vocation, GuildHouse

import guildwatcher
from guildwatcher import Change, ChangeType

logger = logging.getLogger(guildwatcher.__name__)


class TestGuildWatcher(unittest.TestCase):
    def setUp(self):
        self.guild = Guild("Test Guild", "Antica")
        self.guild.guildhall = GuildHouse("Crystal Glance", self.guild.world)
        today = datetime.date.today()
        self.guild.members = [
            GuildMember("Galarzaa", "Leader", level=285, vocation=Vocation.ROYAL_PALADIN, joined=today),
            GuildMember("Nezune", "Vice", level=412, vocation=Vocation.ELITE_KNIGHT, title="Nab", joined=today),
            GuildMember("Ondskan", "Vice", level=437, vocation=Vocation.ROYAL_PALADIN, joined=today),
            GuildMember("Faenryz", "Vice", level=207, vocation=Vocation.ROYAL_PALADIN, joined=today),
            GuildMember("Tschis", "Elite", level=205, vocation=Vocation.DRUID, joined=today),
            GuildMember("John Doe", "Elite", level=34, vocation=Vocation.MASTER_SORCERER, joined=today),
            GuildMember("Jane Doe", "Recruit", level=55, vocation=Vocation.SORCERER, joined=today),
            GuildMember("Fahgnoli", "Recruit", level=404, vocation=Vocation.MASTER_SORCERER, joined=today)
        ]
        self.guild.invites = [
            GuildInvite("Xzilla")
        ]
        self.guild_after = copy.deepcopy(self.guild)

    @patch('logging.Logger.error')
    @patch('builtins.open', new_callable=mock_open, read_data='')
    def test_config_empty(self, m_open, log_error):
        """Attempt loading an empty config file"""
        with self.assertRaises(SystemExit):
            guildwatcher.load_config()
            log_error.assert_called_once()

    @patch('logging.Logger.error')
    @patch('builtins.open', new_callable=mock_open)
    def test_config_no_file(self, m_open, log_error):
        """Attempt loading a file that doesn't exist."""
        m_open.side_effect = FileNotFoundError()
        with self.assertRaises(SystemExit):
            guildwatcher.load_config()

    def test_config_simple_file(self):
        """Testing a config file with simple guild syntax."""
        webhook_url = "http://discord.webhook.url.goes.here"
        content = """
        webhook_url: %s
        
        guilds:
        - Redd Alliance
        """ % webhook_url
        with patch('builtins.open', new_callable=mock_open, read_data=content):
            cfg = guildwatcher.load_config()

        self.assertIsInstance(cfg, guildwatcher.Config)
        self.assertEqual(webhook_url, cfg.webhook_url)
        self.assertEqual(1, len(cfg.guilds))
        self.assertEqual("Redd Alliance", cfg.guilds[0].name)
        self.assertEqual(webhook_url, cfg.guilds[0].webhook_url)

    def test_config_advanced_file(self):
        """Testing a config file with advanced guild syntax."""
        webhook_url = "http://discord.webhook.url.goes.here"
        second_webhook = "http://another.webhook.url"
        content = """
        webhook_url: %s

        guilds:
        - Redd Alliance
        - name: Bald Dwarfs
          webhook_url: %s
        """ % (webhook_url, second_webhook)
        with patch('builtins.open', new_callable=mock_open, read_data=content):
            cfg = guildwatcher.load_config()

        self.assertIsInstance(cfg, guildwatcher.Config)
        self.assertEqual(webhook_url, cfg.webhook_url)
        self.assertEqual(2, len(cfg.guilds))
        self.assertEqual("Redd Alliance", cfg.guilds[0].name)
        self.assertEqual(webhook_url, cfg.guilds[0].webhook_url)

        self.assertEqual("Bald Dwarfs", cfg.guilds[1].name)
        self.assertEqual(second_webhook, cfg.guilds[1].webhook_url)

    def test_new_guildhall(self):
        self.guild.guildhall = None
        changes = guildwatcher.compare_guild(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guildwatcher.ChangeType.GUILDHALL_CHANGED)
        self.assertEqual(changes[0].extra, self.guild_after.guildhall.name)

    def test_lost_guildhall(self):
        self.guild_after.guildhall = None
        changes = guildwatcher.compare_guild(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guildwatcher.ChangeType.GUILDHALL_REMOVED)
        self.assertEqual(changes[0].extra, self.guild.guildhall.name)

    def test_promoted_member(self):
        new_rank = "Elite"
        promoted_member = self.guild_after.members[6]
        promoted_member.rank = new_rank

        changes = guildwatcher.compare_guild(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guildwatcher.ChangeType.PROMOTED)
        self.assertEqual(changes[0].member.name, promoted_member.name)
        self.assertEqual(changes[0].member.rank, promoted_member.rank)

    def test_demoted_member(self):
        new_rank = "Recruit"
        demoted_member = self.guild_after.members[5]
        demoted_member.rank = new_rank

        changes = guildwatcher.compare_guild(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guildwatcher.ChangeType.DEMOTED)
        self.assertEqual(changes[0].member.name, demoted_member.name)
        self.assertEqual(changes[0].member.rank, demoted_member.rank)

    def test_new_member(self):
        new_member = GuildMember("Noob", "Recruit", level=12, vocation="Knight")
        self.guild_after.members.append(new_member)

        changes = guildwatcher.compare_guild(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guildwatcher.ChangeType.NEW_MEMBER)
        self.assertEqual(changes[0].member.name, new_member.name)

    def test_title_change(self):
        new_title = "Even Nabber"
        affected_member = self.guild_after.members[1]
        old_title = affected_member.title
        affected_member.title = new_title
        changes = guildwatcher.compare_guild(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guildwatcher.ChangeType.TITLE_CHANGE)
        self.assertEqual(changes[0].member.name, affected_member.name)
        self.assertEqual(changes[0].member.title, new_title)
        self.assertEqual(changes[0].extra, old_title)

    def test_member_deleted(self):
        # Kick member at position 6
        kicked = self.guild_after.members.pop(6)

        # Mock get_character to imitate non existing character
        guildwatcher.get_character = MagicMock(return_value=None)

        changes = guildwatcher.compare_guild(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guildwatcher.ChangeType.DELETED)
        self.assertEqual(changes[0].member.name, kicked.name)
        guildwatcher.get_character.assert_called_with(kicked.name)

    def test_member_kicked(self):
        # Kick member at position 1
        kicked = self.guild_after.members.pop(1)

        # Mock get_character to imitate existing character
        guildwatcher.get_character = MagicMock(return_value=Character(name=kicked.name))

        changes = guildwatcher.compare_guild(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guildwatcher.ChangeType.REMOVED)
        self.assertEqual(changes[0].member.name, kicked.name)
        guildwatcher.get_character.assert_called_with(kicked.name)

    def test_member_name_changed(self):
        # Change name of first member
        new_name = "Galarzaa Fidera"
        affected_member = self.guild_after.members[0]
        old_name = affected_member.name
        affected_member.name = new_name

        # Checking the missing character should return the new name
        guildwatcher.get_character = MagicMock(return_value=Character(name=new_name))

        changes = guildwatcher.compare_guild(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guildwatcher.ChangeType.NAME_CHANGE)
        self.assertEqual(changes[0].member.name, new_name)
        self.assertEqual(changes[0].extra, old_name)
        guildwatcher.get_character.assert_called_with(old_name)

    def test_invite_accepted(self):
        joining_member = self.guild_after.invites.pop()
        self.guild_after.members.append(GuildMember(joining_member.name, "Recruit", None, 400, Vocation.MASTER_SORCERER))

        changes = guildwatcher.compare_guild(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guildwatcher.ChangeType.NEW_MEMBER)
        self.assertEqual(changes[0].member.name, joining_member.name)

    def test_invite_removed(self):
        joining_member = self.guild_after.invites.pop()

        changes = guildwatcher.compare_guild(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guildwatcher.ChangeType.INVITE_REMOVED)
        self.assertEqual(changes[0].member.name, joining_member.name)

    def test_new_invite(self):
        new_invite = GuildInvite("Pecorino")
        self.guild_after.invites.append(new_invite)

        changes = guildwatcher.compare_guild(self.guild, self.guild_after)
        self.assertEqual(changes[0].type, guildwatcher.ChangeType.NEW_INVITE)
        self.assertEqual(changes[0].member.name, new_invite.name)

    def test_data_integrity(self):
        guildwatcher.save_data("tmp.data", self.guild)
        saved_guild = guildwatcher.load_data("tmp.data")

        changes = guildwatcher.compare_guild(self.guild, saved_guild)

        self.assertFalse(changes)

    def test_embeds(self):
        changes = [
            Change(ChangeType.NEW_MEMBER, GuildMember("Noob", "Recruit", level=19, vocation=Vocation.DRUID)),
            Change(ChangeType.REMOVED, GuildMember("John", "Member", level=56, vocation=Vocation.DRUID, joined=date.today())),
            Change(ChangeType.NAME_CHANGE, GuildMember("Tschis", "Vice", level=205, vocation=Vocation.DRUID), "Tschas"),
            Change(ChangeType.DELETED, GuildMember("Botter", "Vice", level=444, vocation=Vocation.ELITE_KNIGHT,
                                                   joined=date.today())),
            Change(ChangeType.TITLE_CHANGE, GuildMember("Nezune", level=404, rank="Vice", vocation=Vocation.ELITE_KNIGHT,
                                                        title="Nab"), "Challenge Pls"),
            Change(ChangeType.PROMOTED, GuildMember("Old", "Rank", level=142, vocation=Vocation.ROYAL_PALADIN,
                                                    joined=date.today())),
            Change(ChangeType.DEMOTED, GuildMember("Jane", "Rank", level=89, vocation=Vocation.MASTER_SORCERER,
                                                   joined=date.today())),
            Change(ChangeType.INVITE_REMOVED, GuildInvite("Unwanted", date=date.today())),
            Change(ChangeType.NEW_INVITE, GuildInvite("Good Guy", date=date.today())),
            Change(ChangeType.GUILDHALL_REMOVED, None, "Crystal Glance"),
            Change(ChangeType.GUILDHALL_CHANGED, None, "The Tibianic"),
            Change(ChangeType.APPLICATIONS_CHANGE, extra=True),
            Change(ChangeType.APPLICATIONS_CHANGE, extra=False),
            Change(ChangeType.REMOVED_DISBAND_WARNING),
            Change(ChangeType.NEW_DISBAND_WARNING, None, (
                'if there are still less than four vice leaders or an insufficient amount of premium accounts in the'
                ' leading ranks by then', datetime.date(2018, 8, 17))),
        ]
        embeds = guildwatcher.build_embeds(changes)
        import pprint
        pprint.pprint(embeds)
        self.assertTrue(embeds)
        requests.post = MagicMock()
        guildwatcher.publish_changes("https://canary.discordapp.com/api/webhooks/webhook", embeds)
        self.assertTrue(requests.post.call_count)

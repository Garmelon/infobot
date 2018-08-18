import asyncio
import configparser
import logging
import re

import yaboli
from yaboli.utils import *


class InfoBot(yaboli.Bot):
	"""
	Display information about the clients connected to a room in its nick.
	"""

	async def on_command_specific(self, room, message, command, nick, argstr):
		is_mentioned = similar(nick, room.session.nick) or similar(nick, "infobot")
		is_mentioned = is_mentioned or re.fullmatch("p?bl?n?|\(p?bl?n?\)", normalize(nick))
		if is_mentioned:
			if not argstr:
				await self.botrulez_ping(room, message, command)
				await self.botrulez_uptime(room, message, command)
				await self.botrulez_kill(room, message, command)
				await self.botrulez_restart(room, message, command)

				await self.command_recount(room, message, command)

			await self.command_help(room, message, command, argstr)
			await self.command_detail(room, message, command, argstr)

	async def on_command_general(self, room, message, command, argstr):
		if not argstr:
			await self.botrulez_ping(room, message, command)
			await self.botrulez_help(room, message, command, text="I count the types of clients in my nick")

		await self.command_hosts(room, message, command, argstr)

	@yaboli.command("help")
	async def command_help(self, room, message, argstr):
		nick = mention(room.session.nick)
		args = self.parse_args(argstr)
		if not args:
			text = (
				"Displays information about the clients in a room in its nick:"
				" (<people>P\u00A0<bots>B\u00A0<lurkers>L\u00A0<bot-lurkers>N)\n"
				"You can also use @InfoBot, @PBL or @(PBL) for bot commands.\n"
				"\n"
				"!recount {nick} - Recount people in the room\n"
				"!detail {nick} - Detailed list of clients in this room\n"
				"!detail {nick} @person - Detailed info regarding @person\n"
				"!hosts {nick} [--mention] - Lists all hosts currently in this room\n"
				"\n"
				"Created by @Garmy using https://github.com/Garmelon/yaboli.\n"
				"For additional info, try \"!help {nick} <topic>\". Topics:\n"
				"    count, lurkers, changelog"
			).format(nick=nick)
			await room.send(text, message.mid)
		else:
			for topic in args:
				if topic == "count":
					text = (
						"This bot counts the number of clients connected to a room. If you"
						" open a room in two different tabs, the bot counts you twice.\n"
						"The euphoria client, on the other hand, usually displays all"
						" connections of an account with the same nick as one in the nick list."
						" Because of that, this bot's count is always as high as, or higher than,"
						" the number of nicks on the nick list, similar to the number on the"
						" button to toggle the nick list.\n"
						"\n"
						"If the bot's count is off, try a !recount or a !restart {nick}."
					).format(nick=nick)
				elif topic == "lurkers":
					text = (
						"People or bots who are connected to the room but haven't chosen a"
						" nick are lurkers. The euphoria client doesn't display them in the"
						" nick list.\n"
						"This bot differentiates between people (L) and bots (N) who are"
						" lurking."
					)
				elif topic == "changelog":
					text = (
						"- add !recount command\n"
						"- fix bot counting incorrectly\n"
						"- port to rewrite-4 of yaboli\n"
						"- add !detail and !manager commands\n"
					)
				else:
					text = f"Topic {topic!r} does not exist."

				await room.send(text, message.mid)

	async def update_nick(self, room):
		p = len(room.listing.get(types=["account", "agent"], lurker=False))
		b = len(room.listing.get(types=["bot"], lurker=False))
		l = len(room.listing.get(types=["account", "agent"], lurker=True))
		n = len(room.listing.get(types=["bot"], lurker=True))

		name = []
		if p > 0: name.append(f"{p}P")
		if b > 0: name.append(f"{b}B")
		if l > 0: name.append(f"{l}L")
		if n > 0: name.append(f"{n}N")
		name = "\u0001(" + " ".join(name) + ")"

		if room.session.nick != name:
			await room.nick(name)

	async def on_connected(self, room, log):
		await self.update_nick(room)

	async def on_join(self, room, session):
		await self.update_nick(room)
		await room.who()
		await self.update_nick(room)

	async def on_part(self, room, session):
		await self.update_nick(room)
		await room.who()
		await self.update_nick(room)

	async def on_nick(self, room, sid, uid, from_nick, to_nick):
		await self.update_nick(room)
		await room.who()
		await self.update_nick(room)

	@yaboli.command("recount")
	async def command_recount(self, room, message):
		await room.who()
		await self.update_nick(room)
		await room.send("Recalibrated.", message.mid)

	@yaboli.command("detail")
	async def command_detail(self, room, message, argstr):
		sessions = room.listing.get()
		args = self.parse_args(argstr)

		if args:
			lines = []
			for arg in args:
				if arg.startswith("@") and arg[1:]:
					nick = arg[1:]
				else:
					nick = arg

				for ses in sessions:
					if similar(ses.nick, nick):
							lines.append(self.format_session(ses))

			if lines:
				text = "\n".join(lines)
			else:
				text = "No sessions found that match any of the nicks."
			await room.send(text, message.mid)

		else:
			sessions = sorted(sessions, key=lambda s: s.uid)
			lines = [self.format_session(s) for s in sessions]
			text = "\n".join(lines)
			await room.send(text, message.mid)

	@staticmethod
	def format_session(s):
		is_staff = "yes" if s.is_staff else "no"
		is_manager = "yes" if s.is_manager else "no"
		return f"UID: {s.uid}\t| SID: {s.sid}\t| staff: {is_staff}\t| host: {is_manager}\t| nick: {s.nick!r}"

	@yaboli.command("hosts")
	async def command_hosts(self, room, message, argstr):
		flags, args, kwargs = self.parse_flags(self.parse_args(argstr))
		sessions = room.listing.get()
		sessions = sorted(set(s.nick for s in sessions if s.is_manager))

		if "ping" in kwargs:
			sessions = [mention(s) for s in sessions]
		else:
			sessions = [s for s in sessions]

		if sessions:
			text = "Hosts that are currently in this room:\n" + "\n".join(sessions)
		else:
			text = "No hosts currently in this room."
		await room.send(text, message.mid)

def main(configfile):
	logging.basicConfig(level=logging.INFO)

	config = configparser.ConfigParser(allow_no_value=True)
	config.read(configfile)

	nick = config.get("general", "nick")
	cookiefile = config.get("general", "cookiefile", fallback=None)
	bot = InfoBot(nick, cookiefile=cookiefile)

	for room, password in config.items("rooms"):
		if not password:
			password = None
		bot.join_room(room, password=password)

	asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
	main("infobot.conf")

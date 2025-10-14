"""Entry point for the Discord War Bot."""

from __future__ import annotations

import importlib
import logging
import os
import pkgutil
from typing import List

import discord
from discord.ext import commands

from .core.scheduler import StagnationScheduler

GM_ROLE_ID = 123456789012345678
TIME_CHANNEL_ID = 987654321098765432
COMMANDS_PACKAGE = "warbot.commands"

log = logging.getLogger("warbot")


class WarBot(commands.Bot):
    """Custom bot that wires together cogs and background tasks."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.stagnation_scheduler = StagnationScheduler(self, GM_ROLE_ID, TIME_CHANNEL_ID)
        self._synced = False

    async def setup_hook(self) -> None:
        await self._load_command_cogs()
        self.stagnation_scheduler.start()
        log.info("Initial setup complete; waiting for ready event.")

    async def _load_command_cogs(self) -> None:
        loaded: List[str] = []
        package = importlib.import_module(COMMANDS_PACKAGE)
        for module in pkgutil.iter_modules(package.__path__):
            if module.name.startswith("_"):
                continue
            extension = f"{COMMANDS_PACKAGE}.{module.name}"
            await self.load_extension(extension)
            loaded.append(extension)
        log.info("Loaded command extensions: %s", ", ".join(loaded))

    async def on_ready(self) -> None:
        if not self._synced:
            synced = await self.tree.sync()
            log.info("Synced %d application commands.", len(synced))
            self._synced = True

        log.info("Bot ready as %s (%s)", self.user, self.user and self.user.id)
        log.info(
            "Stagnation loop running: %s", self.stagnation_scheduler.check_loop.is_running()
        )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Environment variable DISCORD_TOKEN is required.")

    bot = WarBot()
    bot.run(token)


if __name__ == "__main__":
    main()

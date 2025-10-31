"""Help and tutorial commands for the Discord War Tracking Bot."""

from __future__ import annotations

from typing import List

import discord
from discord import app_commands
from discord.ext import commands


class HelpCommands(commands.GroupCog, name="help"):
    """Help and tutorial commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(
        name="overview",
        description="Overview of the War Tracking Bot and available systems"
    )
    async def help_overview(self, interaction: discord.Interaction) -> None:
        """Show bot overview and main command groups."""
        embed = discord.Embed(
            title="📚 War Tracking Bot - Overview",
            description=(
                "Welcome to the Discord War Tracking Bot! This bot automates war resolution, "
                "intrigue operations, and time tracking for your nation roleplay.\n\n"
                "**Command Groups:**"
            ),
            color=discord.Color.blue()
        )

        embed.add_field(
            name="⚔️ /war - War System",
            value=(
                "**For Players:**\n"
                "• `/war action` - Submit your combat action\n"
                "• `/war status` - View war details\n"
                "• `/war list` - See active wars\n\n"
                "**For GMs:**\n"
                "• `/war create` - Start new war\n"
                "• `/war update` - Modify war settings\n"
                "• `/war resolve` - Execute GM-driven combat\n"
                "Use `/help war` for detailed guide"
            ),
            inline=False
        )

        embed.add_field(
            name="🕵️ /intrigue - Covert Operations",
            value=(
                "Espionage, sabotage, rebellion, assassination, and more!\n"
                "• `/intrigue start` - Launch operation\n"
                "• `/intrigue resolve` - Execute with roll\n"
                "• `/intrigue intel` - View gathered intel\n"
                "Use `/help intrigue` for detailed guide"
            ),
            inline=False
        )

        embed.add_field(
            name="🦾 /superunit - Super Units",
            value=(
                "Research and deploy powerful one-time units\n"
                "• `/superunit create` - Define new unit\n"
                "• `/superunit research` - Unlock intel\n"
                "• `/superunit status` - View progress\n"
                "Use `/help superunit` for detailed guide"
            ),
            inline=False
        )

        embed.add_field(
            name="⏰ /time - Time Tracking",
            value=(
                "Manage RP time and set reminders\n"
                "• `/time show` - Display current time\n"
                "• `/time skip` - Advance seasons/years\n"
                "• Timer commands for reminders"
            ),
            inline=False
        )

        embed.add_field(
            name="📖 More Help Topics",
            value=(
                "• `/help war` - Complete war system guide\n"
                "• `/help action` - How to submit war actions\n"
                "• `/help intrigue` - Intrigue operations guide\n"
                "• `/help npc` - PvE and NPC vs NPC wars\n"
                "• `/help quick` - Quick reference card"
            ),
            inline=False
        )

        embed.set_footer(text="Use /help <topic> for detailed guides on each system")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="action",
        description="Learn how to submit war actions (/war action)"
    )
    async def help_action(self, interaction: discord.Interaction) -> None:
        """Detailed tutorial for /war action command."""
        embed = discord.Embed(
            title="📖 How to Submit War Actions",
            description=(
                "The `/war action` command is how **players submit their combat actions** "
                "in player-driven wars. Here's a step-by-step guide:"
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="Step 1: Write Your Narrative",
            value=(
                "**Before using the command**, write your combat narrative in the war's RP channel.\n"
                "• Minimum 100 characters required\n"
                "• Describe your tactics, what your forces are doing\n"
                "• Make it engaging and in-character!\n\n"
                "**Example:**\n"
                "```The 7th Mechanized Division advances under cover of orbital bombardment. "
                "Artillery batteries rain plasma shells on enemy fortifications while drone swarms "
                "saturate their air defense grid...```"
            ),
            inline=False
        )

        embed.add_field(
            name="Step 2: Get the Message Link",
            value=(
                "After posting your narrative:\n"
                "• Right-click (or long-press on mobile) your message\n"
                "• Select **Copy Message Link**\n"
                "• This link proves you wrote narrative and prevents meta-gaming"
            ),
            inline=False
        )

        embed.add_field(
            name="Step 3: Roll Your D20",
            value=(
                "**You roll the d20 yourself** (in Discord or IRL)\n"
                "• Type `/roll 1d20` in Discord (if you have a dice bot)\n"
                "• Or use physical dice and report the result\n"
                "• The bot does NOT roll for you - you control your fate!"
            ),
            inline=False
        )

        embed.add_field(
            name="Step 4: Submit the Command",
            value=(
                "Now use `/war action` with all parameters:\n\n"
                "```/war action\n"
                "  war_id: 1 (autocomplete shows your wars)\n"
                "  main: Attack (or Defend, or Super Unit)\n"
                "  minor: Prepare_Attack (or Sabotage, Fortify, etc.)\n"
                "  narrative_link: [paste your message link]\n"
                "  roll: 15 (your d20 result)```"
            ),
            inline=False
        )

        embed.add_field(
            name="What Happens Next?",
            value=(
                "**If opponent is NPC:** Bot auto-generates their action and resolves immediately\n"
                "**If opponent is player:** Wait for them to submit their action, then auto-resolves\n"
                "**Result:** Combat results posted to war channel with damage, momentum updates"
            ),
            inline=False
        )

        embed.add_field(
            name="Main Actions Explained",
            value=(
                "**Attack** - Standard offensive assault\n"
                "**Defend** - Defensive posture (+2 bonus to your roll)\n"
                "**Super Unit** - Deploy your super unit (if you have one researched)"
            ),
            inline=False
        )

        embed.add_field(
            name="Minor Actions Explained",
            value=(
                "**Prepare Attack** - +1 to your NEXT attack\n"
                "**Sabotage** - Enemy gets -1 to their roll THIS turn\n"
                "**Fortify Defense** - +1 to your NEXT defense\n"
                "**Heal** - Recover HP instead of dealing damage\n"
                "**Prepare Super Unit** - Ready your super unit for NEXT turn"
            ),
            inline=False
        )

        embed.add_field(
            name="❗ Common Mistakes",
            value=(
                "❌ Forgetting to write narrative first\n"
                "❌ Pasting the wrong link (link to someone else's message)\n"
                "❌ Narrative too short (under 100 characters)\n"
                "❌ Waiting for bot to roll (you must roll yourself!)\n"
                "❌ Submitting before opponent is ready (both must submit for resolution)"
            ),
            inline=False
        )

        embed.set_footer(text="Still confused? Ask your GM for a demonstration!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="war",
        description="Complete guide to the war system"
    )
    async def help_war(self, interaction: discord.Interaction) -> None:
        """Detailed war system guide."""
        embed = discord.Embed(
            title="⚔️ War System - Complete Guide",
            description="Everything you need to know about wars in this bot.",
            color=discord.Color.red()
        )

        embed.add_field(
            name="War Types",
            value=(
                "**PvP (Player vs Player):** Both sides controlled by players\n"
                "**PvE (Player vs Environment):** One side is AI-controlled NPC\n"
                "**EvE (Environment vs Environment):** Both sides are NPCs (auto-resolves)"
            ),
            inline=False
        )

        embed.add_field(
            name="War Theaters",
            value=(
                "Theater affects which stats matter most:\n"
                "**Exosphere** - Space/air combat (uses Exosphere stat)\n"
                "**Naval** - Sea/water combat (uses Naval stat)\n"
                "**Land** - Ground combat (uses Military stat)\n"
                "**Multi-Theater** - Combined arms (uses average of all stats)"
            ),
            inline=False
        )

        embed.add_field(
            name="Dual Momentum System",
            value=(
                "**Tactical Momentum (-3 to +3):**\n"
                "• Adds to your combat roll\n"
                "• Resets to 0 when you lose\n\n"
                "**Strategic Momentum (0-10):**\n"
                "• Multiplies damage dealt (1.0x to 2.0x)\n"
                "• Winner gains +1, loser loses -1 each turn\n"
                "• Both sides can have momentum simultaneously!"
            ),
            inline=False
        )

        embed.add_field(
            name="War Modes",
            value=(
                "**GM-Driven:** GM uses `/war resolve` to execute each turn manually\n"
                "**Player-Driven:** Players use `/war action` and it auto-resolves\n"
                "**NPC Auto-Resolve:** For EvE wars, bot resolves every 12 hours automatically"
            ),
            inline=False
        )

        embed.add_field(
            name="Key Player Commands",
            value=(
                "`/war action` - Submit your combat action (main player command)\n"
                "`/war status war_id:X` - View war details, HP, momentum\n"
                "`/war list` - See all active wars you're in"
            ),
            inline=False
        )

        embed.add_field(
            name="Key GM Commands",
            value=(
                "`/war create` - Start new war (smart wizard)\n"
                "`/war update` - Modify war (stats, roster, settings)\n"
                "`/war resolve` - Execute GM-driven combat\n"
                "`/war end` - Conclude war and declare winner"
            ),
            inline=False
        )

        embed.add_field(
            name="Learn More",
            value=(
                "`/help action` - How to submit war actions\n"
                "`/help npc` - PvE and NPC vs NPC wars\n"
                "`/help quick` - Quick reference for actions/modifiers"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="npc",
        description="Guide to PvE and NPC vs NPC wars"
    )
    async def help_npc(self, interaction: discord.Interaction) -> None:
        """Guide for NPC/AI wars."""
        embed = discord.Embed(
            title="🤖 NPC Wars - PvE & EvE Guide",
            description="How AI-controlled opponents work in this bot.",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="NPC Archetypes",
            value=(
                "**NATO Doctrine** - Combined arms, balanced stats\n"
                "**CSAT Doctrine** - Mass mobilization, ground-heavy\n"
                "**Guerrilla Force** - Asymmetric, hit-and-run\n"
                "**Swarm Doctrine** - Drone-heavy, overwhelming numbers\n"
                "**Elite Force** - Special ops, precision strikes\n"
                "**Defensive Bloc** - Fortifications, attrition\n"
                "**Insurgent/Rebel** - Terrorism, rebellion tactics"
            ),
            inline=False
        )

        embed.add_field(
            name="Tech Levels",
            value=(
                "**Legacy (0.7x)** - Cold War era (AK-47s, T-72 tanks)\n"
                "**Modern (1.0x)** - Contemporary (M4s, drones)\n"
                "**Advanced (1.2x)** - Near-future (smart weapons, camo)\n"
                "**Cutting Edge (1.4x)** - 2240 bleeding-edge (nanotech, AI)"
            ),
            inline=False
        )

        embed.add_field(
            name="NPC Personalities",
            value=(
                "**Aggressive** - 70% attack focus, high risk\n"
                "**Defensive** - 70% defend focus, low risk\n"
                "**Adaptive** - Adjusts based on whether winning/losing\n"
                "**Balanced** - Even mix of tactics\n"
                "**Berserker** - 90% attack, ignores defense"
            ),
            inline=False
        )

        embed.add_field(
            name="PvE (Player vs Environment)",
            value=(
                "One side is human, other is NPC\n"
                "• Player uses `/war action` to submit\n"
                "• NPC auto-generates counter-action\n"
                "• Resolves immediately\n"
                "• NPC learns and adapts over time!"
            ),
            inline=False
        )

        embed.add_field(
            name="EvE (Environment vs Environment)",
            value=(
                "Both sides are NPCs - fully autonomous!\n"
                "• Auto-resolves every 12 hours (customizable)\n"
                "• Perfect for player-incited rebellions\n"
                "• 50-turn limit (defender wins if reached)\n"
                "• GM notified when either side near death\n"
                "• Can escalate to PvE/PvP mid-war with `/war npc escalate`"
            ),
            inline=False
        )

        embed.add_field(
            name="Setting Up PvE War",
            value=(
                "1. `/war create` - Choose PvE type\n"
                "2. Follow prompts to configure NPC side\n"
                "3. Add players to player side\n"
                "4. Players use `/war action` - NPC responds automatically!"
            ),
            inline=False
        )

        embed.add_field(
            name="Setting Up EvE War",
            value=(
                "1. `/war create` - Choose EvE type\n"
                "2. Configure both NPCs (archetype/tech/personality)\n"
                "3. Enable auto-resolution (12hr intervals)\n"
                "4. War runs in background autonomously!"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="intrigue",
        description="Guide to intrigue operations"
    )
    async def help_intrigue(self, interaction: discord.Interaction) -> None:
        """Guide for intrigue operations."""
        embed = discord.Embed(
            title="🕵️ Intrigue System Guide",
            description="Covert operations: espionage, sabotage, rebellion, and more!",
            color=discord.Color.dark_grey()
        )

        embed.add_field(
            name="Operation Types",
            value=(
                "**Espionage (DC 12, 15% detection)** - Gather intel on enemy stats/wars\n"
                "**Sabotage (DC 14, 30% detection)** - Damage infrastructure, reduce stats\n"
                "**Rebellion (DC 16, 50% detection)** - Incite uprising (takes 2-3 ops)\n"
                "**Influence (DC 13, 20% detection)** - Spread ideology/culture\n"
                "**Assassination (DC 18, 40% detection)** - Eliminate leaders\n"
                "**Counter-Intel (DC 10, 10% detection)** - Protect from enemy ops"
            ),
            inline=False
        )

        embed.add_field(
            name="How It Works",
            value=(
                "1. Use `/intrigue start` to launch operation\n"
                "2. Choose type, scale, target strength, operator skill\n"
                "3. Use `/intrigue resolve op_id:X roll:Y` with your d20 roll\n"
                "4. Bot calculates: d20 + modifiers vs DC\n"
                "5. Detection roll happens after (% chance based on op type)\n"
                "6. If detected: Target notified, casus belli, relations damaged"
            ),
            inline=False
        )

        embed.add_field(
            name="Operation Scale",
            value=(
                "**Small** - Low impact, easier (+2 modifier)\n"
                "**Medium** - Standard impact (no modifier)\n"
                "**Large** - High impact, harder (-2 modifier)\n"
                "**Massive** - Extreme impact, very hard (-4 modifier)"
            ),
            inline=False
        )

        embed.add_field(
            name="Sabotage Effects",
            value=(
                "Reduces target stats (Military/Naval/Exosphere):\n"
                "• Small: -5 stat points\n"
                "• Medium: -10 stat points\n"
                "• Large: -15 stat points\n"
                "• Massive: -20 stat points\n"
                "Affects ALL active wars involving target!"
            ),
            inline=False
        )

        embed.add_field(
            name="Rebellion Mechanics",
            value=(
                "Rebellions require **2-3 successful operations** to trigger full war:\n"
                "1st success: Unrest begins, target gets -1 penalty\n"
                "2nd success: Uprising intensifies, -2 penalty\n"
                "3rd success: Full rebellion, GM creates NPC war (Insurgent vs Empire)\n"
                "One-shot rebellions only on critical unrest + nat 20!"
            ),
            inline=False
        )

        embed.add_field(
            name="Key Commands",
            value=(
                "`/intrigue start` - Launch operation\n"
                "`/intrigue resolve` - Execute with your d20 roll\n"
                "`/intrigue list` - View active operations\n"
                "`/intrigue intel target:Faction` - View gathered intelligence\n"
                "`/intrigue alerts faction:YourFaction` - See detected enemy ops"
            ),
            inline=False
        )

        embed.set_footer(text="Always gather intel before major operations!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="quick",
        description="Quick reference card for actions and modifiers"
    )
    async def help_quick(self, interaction: discord.Interaction) -> None:
        """Quick reference card."""
        embed = discord.Embed(
            title="⚡ Quick Reference Card",
            description="Fast lookup for common values",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="War Main Actions",
            value=(
                "**Attack** - Standard assault (no bonus)\n"
                "**Defend** - Defensive posture (+2 to roll)\n"
                "**Super Unit** - Deploy super unit (variable bonus)"
            ),
            inline=False
        )

        embed.add_field(
            name="War Minor Actions",
            value=(
                "**Prepare Attack** - +1 to NEXT attack\n"
                "**Sabotage** - Enemy gets -1 THIS turn\n"
                "**Fortify Defense** - +1 to NEXT defense\n"
                "**Heal** - Recover HP instead of damage\n"
                "**Prepare Super Unit** - Ready for NEXT turn"
            ),
            inline=False
        )

        embed.add_field(
            name="Damage Calculation",
            value=(
                "Damage = Margin of Victory × (1.0 + Strategic Momentum / 10)\n"
                "• Win by 5 with 0 momentum = 5 damage\n"
                "• Win by 5 with 5 momentum = 7.5 damage\n"
                "• Win by 5 with 10 momentum = 10 damage\n"
                "Max damage per turn: 30 (capped)"
            ),
            inline=False
        )

        embed.add_field(
            name="Intrigue DCs",
            value=(
                "Espionage: DC 12 (15% detection)\n"
                "Sabotage: DC 14 (30% detection)\n"
                "Influence: DC 13 (20% detection)\n"
                "Rebellion: DC 16 (50% detection)\n"
                "Assassination: DC 18 (40% detection)\n"
                "Counter-Intel: DC 10 (10% detection)"
            ),
            inline=False
        )

        embed.add_field(
            name="Tech Level Multipliers",
            value=(
                "Legacy: 0.7x (Cold War)\n"
                "Modern: 1.0x (Contemporary)\n"
                "Advanced: 1.2x (Near-future)\n"
                "Cutting Edge: 1.4x (2240 bleeding-edge)"
            ),
            inline=False
        )

        embed.set_footer(text="Use /help <topic> for detailed guides")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="superunit",
        description="Guide to super units and intel system"
    )
    async def help_superunit(self, interaction: discord.Interaction) -> None:
        """Guide for super units."""
        embed = discord.Embed(
            title="🦾 Super Units Guide",
            description="Powerful one-time units with intelligence gathering system",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="What Are Super Units?",
            value=(
                "Super units are **one-time powerful abilities** that can turn the tide of battle.\n"
                "• They are theater-specific (Exosphere/Naval/Military)\n"
                "• Used as a Main Action in `/war action`\n"
                "• Consumed after use (can't use again)\n"
                "• Combat bonus based on intel researched (0% to 100%)"
            ),
            inline=False
        )

        embed.add_field(
            name="Intel System",
            value=(
                "Before deploying, you must research intel about the unit:\n"
                "• Each super unit has 1-7 intel pieces to unlock\n"
                "• 0% intel = -2 penalty (don't deploy unprepared!)\n"
                "• 100% intel = +2 bonus (fully researched)\n"
                "• Intel is unlocked via `/superunit research` with DC 15+ or nat 20"
            ),
            inline=False
        )

        embed.add_field(
            name="Combat Modifier Formula",
            value=(
                "**Modifier = -2 + (Intel % / 25)**\n"
                "• 0% intel = -2 (very risky!)\n"
                "• 25% intel = -1\n"
                "• 50% intel = 0 (neutral)\n"
                "• 75% intel = +1\n"
                "• 100% intel = +2 (maximum bonus)"
            ),
            inline=False
        )

        embed.add_field(
            name="Creating Super Units (GM)",
            value=(
                "```/superunit create\n"
                "  name: \"Titan-Class Dreadnought\"\n"
                "  max_intel: 5\n"
                "  description: \"Massive orbital platform...\"\n"
                "  war_id: 1```\n"
                "Then use `/superunit set_intel` to describe each intel piece"
            ),
            inline=False
        )

        embed.add_field(
            name="Researching Intel (Players)",
            value=(
                "```/superunit research\n"
                "  unit_id: 1\n"
                "  researcher: @YourName\n"
                "  roll: 18```\n"
                "• DC 15+ unlocks 1 random intel\n"
                "• Natural 20 unlocks 2 intel pieces!"
            ),
            inline=False
        )

        embed.add_field(
            name="Deploying in Combat",
            value=(
                "When using `/war action`:\n"
                "• Set `main: Super Unit`\n"
                "• Bot checks your intel %\n"
                "• Applies modifier to your roll\n"
                "• Super unit is consumed after use\n"
                "**Strategy:** Research to 75-100% before deploying!"
            ),
            inline=False
        )

        embed.set_footer(text="Never deploy at 0% intel - it's a -2 penalty!")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Register the help commands cog."""
    await bot.add_cog(HelpCommands(bot))

import json
import os
import random
from dataclasses import dataclass
from typing import Dict

import discord
from discord.ext import commands
from dotenv import load_dotenv

# ================== BOT SETUP ==================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = "economy.json"

CASHIER_ROLE_NAME = "Cashier"

CASHIER_ROLE_NAME = "Cashier"  # must match the role name exactly
WITHDRAW_MIN = 1

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ================== ECONOMY SYSTEM ==================
def _load_bank() -> Dict[str, Dict[str, int]]:
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_bank(bank: Dict[str, Dict[str, int]]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(bank, f, indent=2)

def ensure_account(user_id: int) -> None:
    bank = _load_bank()
    uid = str(user_id)
    if uid not in bank:
        bank[uid] = {"wallet": 0}
        _save_bank(bank)

def get_wallet(user_id: int) -> int:
    ensure_account(user_id)
    return _load_bank()[str(user_id)]["wallet"]

def add_wallet(user_id: int, amount: int) -> int:
    ensure_account(user_id)
    bank = _load_bank()
    uid = str(user_id)
    bank[uid]["wallet"] += amount
    if bank[uid]["wallet"] < 0:
        bank[uid]["wallet"] = 0
    _save_bank(bank)
    return bank[uid]["wallet"]

# ================== SLOT MACHINE ==================
@dataclass(frozen=True)
class Symbol:
    emoji: str
    weight: int

SYMBOLS = [
    Symbol("🪐", 40),   # planet
    Symbol("🌙", 30),   # moon
    Symbol("👨‍🚀", 20), # explorer
    Symbol("🚀", 8),    # rocket
    Symbol("💎", 2),    # cosmic crystal
]

THREE_KIND_PAYOUTS = {
    "🪐": 2,
    "🌙": 3,
    "👨‍🚀": 5,
    "🚀": 15,
    "💎": 50,
}

def spin_reel() -> str:
    return random.choices(
        [s.emoji for s in SYMBOLS],
        weights=[s.weight for s in SYMBOLS],
        k=1
    )[0]

def payout_multiplier(r1: str, r2: str, r3: str) -> float:
    if r1 == r2 == r3:
        return float(THREE_KIND_PAYOUTS.get(r1, 0))
    # only adjacent 2-match (see step 2)
    if r1 == r2 or r2 == r3:
        return 0.25
    return 0.0

# ================== COMMANDS ==================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command(name="bal", aliases=["balance"])
async def balance(ctx):
    chips = get_wallet(ctx.author.id)
    await ctx.send(f"🛰️ {ctx.author.mention} has **{chips}** cosmic chips.")

@bot.command(name="addchips")
@commands.has_role(CASHIER_ROLE_NAME)
async def addchips(ctx, member: discord.User, amount: int):
    if amount == 0:
        return await ctx.send("Amount must be non-zero.")

    new_bal = add_wallet(member.id, amount)
    await ctx.send(
        f"🪙 {member.mention} received **{amount}** cosmic chips.\n"
        f"💰 New balance: **{new_bal}**"
    )

@bot.command(name="slots")
async def slots(ctx, amount: int):
    if amount <= 0:
        return await ctx.send("Amount must be a positive integer.")

    wallet = get_wallet(ctx.author.id)
    if amount > wallet:
        return await ctx.send(f"❌ You only have **{wallet}** chips.")

    add_wallet(ctx.author.id, -amount)

    r1, r2, r3 = spin_reel(), spin_reel(), spin_reel()
    mult = payout_multiplier(r1, r2, r3)

    embed = discord.Embed(
        title="🌌 Starfarer Slots",
        description=f"🎰 | {r1} | {r2} | {r3} |"
    )

    if mult == 0:
        embed.add_field(name="Outcome", value=f"Lost **{amount}** chips drifting through space.")
    else:
      winnings = max(1, int(amount * mult))  # floors decimals (e.g., 10 * 0.25 = 2)
add_wallet(ctx.author.id, amount + winnings)
        embed.add_field(name="Outcome", value=f"🚀 Mission success! Won **{winnings}** chips (x{mult}).")

    embed.add_field(name="Balance", value=f"💰 {get_wallet(ctx.author.id)}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="🌌 Starfarer Slots — Command Guide",
        description="Explore the galaxy and test your luck!",
        color=discord.Color.purple()
    )

    embed.add_field(
        name="🎰 Slot Machine",
        value="`!slots <amount>`\nSpin the reels using cosmic tokens.",
        inline=False
    )

    embed.add_field(
        name="💰 Balance",
        value="`!bal`\nCheck your current token balance.",
        inline=False
    )

    embed.add_field(
    name="🏧 Withdraw",
    value="`!withdraw <amount> [note]`\nRequests a cashier payout. Tokens are deducted immediately.",
    inline=False
)

    embed.set_footer(text="🌠 May the odds be ever in your orbit")

    await ctx.send(embed=embed)

@bot.command(name="rules", aliases=["payouts", "paytable"])
async def rules(ctx):
    embed = discord.Embed(
        title="📜 Starfarer Slots — Rules & Payouts",
        description="Cosmic tokens in, cosmic tokens out. Here’s how it works:",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🎟️ Betting Rules",
        value=(
            "• Use `!slots <amount>` (amount must be a positive integer)\n"
            "• You must have enough tokens to place the bet\n"
            "• Your bet is deducted first\n"
            "• If you win, you get **your bet back + profit**"
        ),
        inline=False
    )

    embed.add_field(
        name="✨ Matching Rules",
        value=(
            "• **2 adjacent matching symbols** = **x.25 profit**\n"
            "• **3 matching symbols** = special payout (see table below)\n"
            "• No matches = you lose your bet"
        ),
        inline=False
    )

    embed.add_field(
        name="💫 3-of-a-kind Pay Table (Profit Multipliers)",
        value=(
            "🪐🪐🪐  = x2 profit\n"
            "🌙🌙🌙  = x3 profit\n"
            "👨‍🚀👨‍🚀👨‍🚀 = x5 profit\n"
            "🚀🚀🚀  = x15 profit\n"
            "💎💎💎  = x50 profit"
        ),
        inline=False
    )

    embed.set_footer(text="Tip: Bigger multipliers usually come from rarer symbols.")
    await ctx.send(embed=embed)

@bot.command(name="withdraw", aliases=["cashout", "payout"])
async def withdraw(ctx: commands.Context, amount: int, *, note: str = ""):
    # Validate amount
    if amount < WITHDRAW_MIN:
        return await ctx.send(f"Amount must be at least {WITHDRAW_MIN}.")

    wallet = get_wallet(ctx.author.id)
    if amount > wallet:
        return await ctx.send(f"❌ You only have **{wallet}** tokens available.")

    # Deduct immediately (prevents double-spending)
    add_wallet(ctx.author.id, -amount)
    remaining = get_wallet(ctx.author.id)

    # Find cashier role to ping
    cashier_role = discord.utils.get(ctx.guild.roles, name=CASHIER_ROLE_NAME)
    cashier_ping = cashier_role.mention if cashier_role else "**@Cashier role not found**"

    note_text = note.strip()
    note_line = f"\n📝 Note: {note_text}" if note_text else ""

    embed = discord.Embed(
        title="🏧 Withdrawal Request — Starfarer Casino",
        description=(
            f"👤 Player: {ctx.author.mention}\n"
            f"🪙 Amount: **{amount}** tokens\n"
            f"💰 Remaining balance: **{remaining}** tokens"
            f"{note_line}"
        ),
        color=discord.Color.gold()
    )

    await ctx.send(content=f"{cashier_ping} New withdrawal request!", embed=embed)
    await ctx.send("✅ Withdrawal request submitted. A cashier will assist you here.")

@addchips.error
async def addchips_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You must be an Administrator to use `!addchips`.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Usage: `!addchips @user <amount>`")
    else:
        await ctx.send(f"❌ Error: {error}")

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN missing in .env")
    bot.run(TOKEN)








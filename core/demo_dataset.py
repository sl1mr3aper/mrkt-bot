"""Realistic synthetic data for the MRKT bot when run without API credentials.

The data here mimics the structure of the real ``api.tgmrkt.io`` responses but is
generated locally — there is **no** way to fetch live MRKT data without a valid
``api_id``/``api_hash`` pair (the public API returns 401 without a JWT).

The dataset covers:

* 50+ named collections (a superset of the public Telegram Gifts catalogue plus
  community-known rarities), each with realistic floor prices and 24h volumes;
* ~25 backdrops, ~25 symbols and ~250 models distributed across collections;
* ~600 listings spread between the cheapest end of each collection and a long
  tail of premium items;
* ~80 simulated user trades so the analytics screens (top gainers / losers /
  P&L / liquidity) show meaningful numbers in DRY-RUN mode.

The generator is deterministic (seeded) so the bot UI is reproducible between
restarts.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

# ─── canonical reference data ──────────────────────────────────────


COLLECTIONS: list[dict[str, Any]] = [
    {"name": "PlushPepe", "title": "Plush Pepe", "floor": 1.85, "volume_24h": 4321.0},
    {"name": "DurovsCap", "title": "Durov's Cap", "floor": 4.20, "volume_24h": 2210.0},
    {"name": "AstralShard", "title": "Astral Shard", "floor": 0.95, "volume_24h": 8870.0},
    {"name": "GenieLamp", "title": "Genie Lamp", "floor": 12.50, "volume_24h": 980.0},
    {"name": "DiamondRing", "title": "Diamond Ring", "floor": 7.30, "volume_24h": 1640.0},
    {"name": "EternalRose", "title": "Eternal Rose", "floor": 3.10, "volume_24h": 3450.0},
    {"name": "HeroicHelmet", "title": "Heroic Helmet", "floor": 2.40, "volume_24h": 2880.0},
    {"name": "ToyBear", "title": "Toy Bear", "floor": 1.10, "volume_24h": 5210.0},
    {"name": "MagicPotion", "title": "Magic Potion", "floor": 0.80, "volume_24h": 6730.0},
    {"name": "WitchHat", "title": "Witch Hat", "floor": 0.65, "volume_24h": 4120.0},
    {"name": "EasterEgg", "title": "Easter Egg", "floor": 0.55, "volume_24h": 3990.0},
    {"name": "GingerCookie", "title": "Ginger Cookie", "floor": 0.40, "volume_24h": 7650.0},
    {"name": "LolPop", "title": "Lol Pop", "floor": 0.35, "volume_24h": 8210.0},
    {"name": "HomemadeCake", "title": "Homemade Cake", "floor": 0.45, "volume_24h": 4380.0},
    {"name": "LootBag", "title": "Loot Bag", "floor": 1.50, "volume_24h": 2550.0},
    {"name": "HexPot", "title": "Hex Pot", "floor": 0.95, "volume_24h": 1890.0},
    {"name": "BondedRing", "title": "Bonded Ring", "floor": 5.40, "volume_24h": 1320.0},
    {"name": "SwissWatch", "title": "Swiss Watch", "floor": 9.80, "volume_24h": 870.0},
    {"name": "PreciousPeach", "title": "Precious Peach", "floor": 6.20, "volume_24h": 1180.0},
    {"name": "MiniOscar", "title": "Mini Oscar", "floor": 2.85, "volume_24h": 2310.0},
    {"name": "JellyBunny", "title": "Jelly Bunny", "floor": 0.60, "volume_24h": 3690.0},
    {"name": "SignetRing", "title": "Signet Ring", "floor": 4.00, "volume_24h": 1620.0},
    {"name": "ScarletKite", "title": "Scarlet Kite", "floor": 1.75, "volume_24h": 2810.0},
    {"name": "TopHat", "title": "Top Hat", "floor": 1.20, "volume_24h": 3450.0},
    {"name": "CrystalBall", "title": "Crystal Ball", "floor": 2.10, "volume_24h": 2670.0},
    {"name": "VintageCigar", "title": "Vintage Cigar", "floor": 1.95, "volume_24h": 1830.0},
    {"name": "RecordPlayer", "title": "Record Player", "floor": 0.85, "volume_24h": 2540.0},
    {"name": "BerryBox", "title": "Berry Box", "floor": 0.50, "volume_24h": 4920.0},
    {"name": "TamaGadget", "title": "Tama Gadget", "floor": 1.40, "volume_24h": 3110.0},
    {"name": "Skateboard", "title": "Skateboard", "floor": 0.70, "volume_24h": 3780.0},
    {"name": "JackInTheBox", "title": "Jack-in-the-Box", "floor": 1.05, "volume_24h": 1990.0},
    {"name": "ElectricSkull", "title": "Electric Skull", "floor": 3.40, "volume_24h": 1240.0},
    {"name": "EvilEye", "title": "Evil Eye", "floor": 1.55, "volume_24h": 2180.0},
    {"name": "VoodooDoll", "title": "Voodoo Doll", "floor": 0.90, "volume_24h": 2710.0},
    {"name": "Pumpkin", "title": "Pumpkin", "floor": 0.45, "volume_24h": 4060.0},
    {"name": "SpicedWine", "title": "Spiced Wine", "floor": 1.30, "volume_24h": 1740.0},
    {"name": "Kazoo", "title": "Kazoo", "floor": 0.30, "volume_24h": 5580.0},
    {"name": "PartyHat", "title": "Party Hat", "floor": 0.55, "volume_24h": 3270.0},
    {"name": "Snowman", "title": "Snowman", "floor": 0.70, "volume_24h": 2820.0},
    {"name": "Mistletoe", "title": "Mistletoe", "floor": 0.40, "volume_24h": 4730.0},
    {"name": "SantaHat", "title": "Santa Hat", "floor": 0.50, "volume_24h": 5310.0},
    {"name": "JinglyBell", "title": "Jingly Bell", "floor": 0.35, "volume_24h": 5980.0},
    {"name": "WinterWreath", "title": "Winter Wreath", "floor": 0.60, "volume_24h": 3170.0},
    {"name": "SwagBag", "title": "Swag Bag", "floor": 0.85, "volume_24h": 2410.0},
    {"name": "SharpTooth", "title": "Sharp Tooth", "floor": 1.15, "volume_24h": 2230.0},
    {"name": "BlackOuija", "title": "Black Ouija", "floor": 2.50, "volume_24h": 1370.0},
    {"name": "GoldenStar", "title": "Golden Star", "floor": 4.80, "volume_24h": 940.0},
    {"name": "DesertSpear", "title": "Desert Spear", "floor": 1.60, "volume_24h": 2050.0},
    {"name": "FreshSocks", "title": "Fresh Socks", "floor": 0.25, "volume_24h": 6230.0},
    {"name": "RoboArm", "title": "Robo Arm", "floor": 1.85, "volume_24h": 1480.0},
    {"name": "NeonHeart", "title": "Neon Heart", "floor": 1.40, "volume_24h": 2860.0},
    {"name": "Pochita", "title": "Pochita", "floor": 6.90, "volume_24h": 720.0},
    {"name": "BoxingGlove", "title": "Boxing Glove", "floor": 1.25, "volume_24h": 1640.0},
    {"name": "Cupcake", "title": "Cupcake", "floor": 0.40, "volume_24h": 4810.0},
    {"name": "Trophy", "title": "Trophy", "floor": 3.60, "volume_24h": 1110.0},
    {"name": "GlitchScroll", "title": "Glitch Scroll", "floor": 5.10, "volume_24h": 880.0},
    # ─── extended catalogue: community-known + seasonal items ─────────
    {"name": "FallenLeaf", "title": "Fallen Leaf", "floor": 0.18, "volume_24h": 9120.0},
    {"name": "PetalPurse", "title": "Petal Purse", "floor": 0.42, "volume_24h": 4870.0},
    {"name": "DreamCatcher", "title": "Dream Catcher", "floor": 1.05, "volume_24h": 2860.0},
    {"name": "MysticOrb", "title": "Mystic Orb", "floor": 2.95, "volume_24h": 1740.0},
    {"name": "SnowFox", "title": "Snow Fox", "floor": 1.65, "volume_24h": 2310.0},
    {"name": "FlashBoots", "title": "Flash Boots", "floor": 0.78, "volume_24h": 3340.0},
    {"name": "BronzeCoin", "title": "Bronze Coin", "floor": 0.22, "volume_24h": 8540.0},
    {"name": "SilverCoin", "title": "Silver Coin", "floor": 0.65, "volume_24h": 6210.0},
    {"name": "GoldCoin", "title": "Gold Coin", "floor": 1.95, "volume_24h": 4870.0},
    {"name": "PlatinumCoin", "title": "Platinum Coin", "floor": 5.40, "volume_24h": 1980.0},
    {"name": "FlameStaff", "title": "Flame Staff", "floor": 3.10, "volume_24h": 1450.0},
    {"name": "FrostStaff", "title": "Frost Staff", "floor": 3.20, "volume_24h": 1380.0},
    {"name": "ShadowBlade", "title": "Shadow Blade", "floor": 4.50, "volume_24h": 1120.0},
    {"name": "DawnBlade", "title": "Dawn Blade", "floor": 4.30, "volume_24h": 1180.0},
    {"name": "RoyalScepter", "title": "Royal Scepter", "floor": 7.80, "volume_24h": 720.0},
    {"name": "Lighthouse", "title": "Lighthouse", "floor": 1.40, "volume_24h": 2630.0},
    {"name": "Telescope", "title": "Telescope", "floor": 1.85, "volume_24h": 1980.0},
    {"name": "Compass", "title": "Compass", "floor": 0.95, "volume_24h": 3120.0},
    {"name": "Sextant", "title": "Sextant", "floor": 1.10, "volume_24h": 2270.0},
    {"name": "Microscope", "title": "Microscope", "floor": 2.10, "volume_24h": 1490.0},
    {"name": "Hourglass", "title": "Hourglass", "floor": 1.30, "volume_24h": 2540.0},
    {"name": "AbacusBeads", "title": "Abacus Beads", "floor": 0.80, "volume_24h": 2820.0},
    {"name": "InkQuill", "title": "Ink Quill", "floor": 0.55, "volume_24h": 3470.0},
    {"name": "OldManuscript", "title": "Old Manuscript", "floor": 1.95, "volume_24h": 1530.0},
    {"name": "DragonScale", "title": "Dragon Scale", "floor": 6.40, "volume_24h": 880.0},
    {"name": "PhoenixFeather", "title": "Phoenix Feather", "floor": 8.20, "volume_24h": 760.0},
    {"name": "UnicornHorn", "title": "Unicorn Horn", "floor": 11.00, "volume_24h": 540.0},
    {"name": "GriffinClaw", "title": "Griffin Claw", "floor": 5.80, "volume_24h": 990.0},
    {"name": "MermaidScale", "title": "Mermaid Scale", "floor": 4.10, "volume_24h": 1230.0},
    {"name": "FairyDust", "title": "Fairy Dust", "floor": 0.85, "volume_24h": 3450.0},
    {"name": "ElvenBow", "title": "Elven Bow", "floor": 3.70, "volume_24h": 1320.0},
    {"name": "DwarvenAxe", "title": "Dwarven Axe", "floor": 3.90, "volume_24h": 1290.0},
    {"name": "OrcShield", "title": "Orc Shield", "floor": 2.60, "volume_24h": 1640.0},
    {"name": "GoblinPouch", "title": "Goblin Pouch", "floor": 0.60, "volume_24h": 3780.0},
    {"name": "TrollClub", "title": "Troll Club", "floor": 1.15, "volume_24h": 2410.0},
    {"name": "BansheeWail", "title": "Banshee Wail", "floor": 2.30, "volume_24h": 1560.0},
    {"name": "GhostLantern", "title": "Ghost Lantern", "floor": 1.60, "volume_24h": 2120.0},
    {"name": "ZombieHand", "title": "Zombie Hand", "floor": 0.75, "volume_24h": 2980.0},
    {"name": "WerewolfClaw", "title": "Werewolf Claw", "floor": 2.05, "volume_24h": 1820.0},
    {"name": "VampireFang", "title": "Vampire Fang", "floor": 2.85, "volume_24h": 1340.0},
    {"name": "MummyWraps", "title": "Mummy Wraps", "floor": 0.90, "volume_24h": 2660.0},
    {"name": "PirateHook", "title": "Pirate Hook", "floor": 1.40, "volume_24h": 2340.0},
    {"name": "PirateMap", "title": "Pirate Map", "floor": 1.85, "volume_24h": 1920.0},
    {"name": "TreasureChest", "title": "Treasure Chest", "floor": 5.20, "volume_24h": 1080.0},
    {"name": "LuckyClover", "title": "Lucky Clover", "floor": 0.45, "volume_24h": 4830.0},
    {"name": "RabbitFoot", "title": "Rabbit Foot", "floor": 0.55, "volume_24h": 3920.0},
    {"name": "WishboneCharm", "title": "Wishbone Charm", "floor": 0.70, "volume_24h": 3340.0},
    {"name": "CarvedTotem", "title": "Carved Totem", "floor": 1.25, "volume_24h": 2210.0},
    {"name": "MonkBeads", "title": "Monk Beads", "floor": 0.95, "volume_24h": 2790.0},
    {"name": "TempleBell", "title": "Temple Bell", "floor": 1.70, "volume_24h": 1990.0},
    {"name": "GardenGnome", "title": "Garden Gnome", "floor": 0.85, "volume_24h": 2840.0},
    {"name": "BeeHive", "title": "Bee Hive", "floor": 1.10, "volume_24h": 2380.0},
    {"name": "TerrariumGlobe", "title": "Terrarium Globe", "floor": 1.95, "volume_24h": 1670.0},
    {"name": "BonsaiTree", "title": "Bonsai Tree", "floor": 2.40, "volume_24h": 1490.0},
    {"name": "TeaCeremony", "title": "Tea Ceremony", "floor": 1.55, "volume_24h": 2070.0},
    {"name": "CoffeePress", "title": "Coffee Press", "floor": 0.80, "volume_24h": 3160.0},
    {"name": "WineBarrel", "title": "Wine Barrel", "floor": 1.60, "volume_24h": 1880.0},
    {"name": "GoldKey", "title": "Gold Key", "floor": 3.20, "volume_24h": 1320.0},
    {"name": "SilverKey", "title": "Silver Key", "floor": 1.80, "volume_24h": 2410.0},
    {"name": "BronzeKey", "title": "Bronze Key", "floor": 0.90, "volume_24h": 3470.0},
    {"name": "FabergeEgg", "title": "Faberge Egg", "floor": 14.00, "volume_24h": 380.0},
    {"name": "ChessKnight", "title": "Chess Knight", "floor": 1.65, "volume_24h": 2110.0},
    {"name": "ChessQueen", "title": "Chess Queen", "floor": 4.20, "volume_24h": 1080.0},
    {"name": "ChessKing", "title": "Chess King", "floor": 5.40, "volume_24h": 940.0},
    {"name": "DiceSet", "title": "Dice Set", "floor": 0.65, "volume_24h": 3680.0},
    {"name": "PlayingCard", "title": "Playing Card", "floor": 0.30, "volume_24h": 6240.0},
    {"name": "TarotCard", "title": "Tarot Card", "floor": 1.20, "volume_24h": 2620.0},
    {"name": "DominoTile", "title": "Domino Tile", "floor": 0.40, "volume_24h": 4810.0},
    {"name": "MahjongTile", "title": "Mahjong Tile", "floor": 0.55, "volume_24h": 4170.0},
    {"name": "GoStone", "title": "Go Stone", "floor": 0.45, "volume_24h": 4480.0},
    {"name": "RubikCube", "title": "Rubik Cube", "floor": 0.95, "volume_24h": 2870.0},
    {"name": "Yo-Yo", "title": "Yo-Yo", "floor": 0.35, "volume_24h": 5210.0},
    {"name": "PaperPlane", "title": "Paper Plane", "floor": 0.20, "volume_24h": 7430.0},
    {"name": "OrigamiCrane", "title": "Origami Crane", "floor": 0.50, "volume_24h": 4150.0},
    {"name": "PaintBrush", "title": "Paint Brush", "floor": 0.65, "volume_24h": 3210.0},
    {"name": "OilPalette", "title": "Oil Palette", "floor": 1.10, "volume_24h": 2480.0},
    {"name": "EaselFrame", "title": "Easel Frame", "floor": 1.85, "volume_24h": 1740.0},
    {"name": "SoundWave", "title": "Sound Wave", "floor": 1.40, "volume_24h": 2230.0},
    {"name": "Headphones", "title": "Headphones", "floor": 0.95, "volume_24h": 2810.0},
    {"name": "SyntheKey", "title": "Synthe Key", "floor": 2.15, "volume_24h": 1690.0},
    {"name": "VinylRecord", "title": "Vinyl Record", "floor": 0.85, "volume_24h": 2980.0},
    {"name": "GuitarPick", "title": "Guitar Pick", "floor": 0.30, "volume_24h": 5640.0},
]


BACKDROPS: list[str] = [
    "Sky", "Forest", "Volcano", "Cosmos", "Beach", "Desert", "Aurora", "Void",
    "Lavender", "Sunrise", "Sunset", "Glacier", "Storm", "Meadow", "Reef",
    "Magma", "Twilight", "Tundra", "Citadel", "Nebula", "Garden", "Dunes",
    "Cliff", "Marsh", "Foundry",
]


SYMBOLS: list[str] = [
    "Heart", "Star", "Crown", "Lightning", "Rose", "Skull", "Diamond", "Moon",
    "Sun", "Spade", "Club", "Anchor", "Feather", "Compass", "Eye", "Wave",
    "Flame", "Snowflake", "Leaf", "Cloud", "Arrow", "Bell", "Dagger", "Cube",
    "Key",
]


# ─── per-collection model lists (each ≈4–8 models) ────────────────


def _models_for(collection: str) -> list[str]:
    """Deterministic-but-varied list of model names for a given collection."""
    base = {
        "PlushPepe": ["Classic Pepe", "Sad Pepe", "Cool Pepe", "King Pepe", "Hacker Pepe"],
        "DurovsCap": ["Black Cap", "Red Cap", "Gold Cap", "Cyber Cap"],
        "AstralShard": ["Crystal", "Obsidian", "Ruby", "Sapphire", "Emerald", "Topaz"],
        "GenieLamp": ["Brass", "Silver", "Gold", "Diamond", "Onyx"],
        "DiamondRing": ["Plain", "Engraved", "Halo", "Pavé", "Solitaire", "Eternity"],
        "EternalRose": ["Crimson", "Ivory", "Black", "Gold-Dipped", "Frost"],
        "HeroicHelmet": ["Spartan", "Roman", "Viking", "Samurai", "Knight"],
        "ToyBear": ["Brown", "Panda", "Polar", "Honey", "Punk"],
        "MagicPotion": ["Healing", "Mana", "Luck", "Storm", "Blood"],
        "WitchHat": ["Plain", "Star-Lit", "Bramble", "Cursed", "Velvet"],
        "EasterEgg": ["Painted", "Speckled", "Gold-Leaf", "Marbled"],
        "GingerCookie": ["Classic", "Glazed", "Frosted", "Cinnamon"],
        "LolPop": ["Cherry", "Berry", "Mint", "Toxic"],
        "HomemadeCake": ["Vanilla", "Chocolate", "Strawberry", "Red Velvet"],
        "LootBag": ["Common", "Uncommon", "Rare", "Mythic"],
        "HexPot": ["Iron", "Copper", "Black-Iron", "Bone"],
        "BondedRing": ["Argent", "Aurum", "Platinum", "Carbon"],
        "SwissWatch": ["Steel", "Gold", "Rose Gold", "Tourbillon"],
        "PreciousPeach": ["Honey", "Sunset", "Velvet", "Imperial"],
        "MiniOscar": ["Bronze", "Silver", "Gold", "Lifetime"],
        "JellyBunny": ["Pink", "Blue", "Mint", "Cyber"],
        "SignetRing": ["Iron", "Bronze", "Silver", "Gold"],
        "ScarletKite": ["Crimson", "Ember", "Obsidian", "Phoenix"],
        "TopHat": ["Velvet", "Silk", "Cyber", "Steampunk"],
        "CrystalBall": ["Clear", "Smoky", "Mystic", "Galaxy"],
        "VintageCigar": ["Cuban", "Habana", "Toscano", "Reserve"],
        "RecordPlayer": ["Vinyl", "Belt", "Tube", "Spinner"],
        "BerryBox": ["Strawberry", "Blueberry", "Raspberry", "Cloudberry"],
        "TamaGadget": ["Pixel", "Retro", "Holo", "Glitch"],
        "Skateboard": ["Street", "Vert", "Long", "Cruiser"],
        "JackInTheBox": ["Classic", "Cursed", "Cyber", "Carnival"],
        "ElectricSkull": ["Volt", "Plasma", "Tesla", "Static"],
        "EvilEye": ["Indigo", "Crimson", "Onyx", "Solar"],
        "VoodooDoll": ["Cloth", "Straw", "Wax", "Bone"],
        "Pumpkin": ["Common", "Cursed", "Glow", "Rotten"],
        "SpicedWine": ["Cabernet", "Merlot", "Rosé", "Glühwein"],
        "Kazoo": ["Brass", "Plastic", "Wood", "Crystal"],
        "PartyHat": ["Confetti", "Glitter", "Neon", "Royal"],
        "Snowman": ["Classic", "Frostbite", "Sentinel", "Holiday"],
        "Mistletoe": ["Plain", "Frost", "Gilded", "Crystal"],
        "SantaHat": ["Plush", "Velvet", "Glittered", "Royal"],
        "JinglyBell": ["Brass", "Silver", "Gold", "Crystal"],
        "WinterWreath": ["Pine", "Holly", "Frost", "Ribboned"],
        "SwagBag": ["Canvas", "Leather", "Holo", "Cyber"],
        "SharpTooth": ["Wolf", "Saber", "Dragon", "Kraken"],
        "BlackOuija": ["Plain", "Engraved", "Cursed", "Phantom"],
        "GoldenStar": ["5-Point", "6-Point", "8-Point", "Burst"],
        "DesertSpear": ["Bronze", "Iron", "Steel", "Obsidian"],
        "FreshSocks": ["Stripes", "Plain", "Holo", "Argyle"],
        "RoboArm": ["MK1", "MK2", "MK3", "MK7"],
        "NeonHeart": ["Pink", "Cyan", "Lime", "Violet"],
        "Pochita": ["Standard", "Bloodlust", "Dormant", "Awakened"],
        "BoxingGlove": ["Red", "Blue", "Gold", "Champion"],
        "Cupcake": ["Vanilla", "Chocolate", "Velvet", "Birthday"],
        "Trophy": ["Bronze", "Silver", "Gold", "Diamond"],
        "GlitchScroll": ["Lambda", "Sigma", "Omega", "Aleph"],
    }
    if collection in base:
        return base[collection]
    # Auto-derived models for the extended catalogue: pick a deterministic
    # palette of style words so each collection still has 4–6 distinct models.
    palettes: list[list[str]] = [
        ["Bronze", "Silver", "Gold", "Platinum", "Mythic"],
        ["Common", "Uncommon", "Rare", "Epic", "Legendary"],
        ["Frost", "Flame", "Storm", "Shadow", "Aether"],
        ["Crimson", "Cobalt", "Emerald", "Amber", "Onyx"],
        ["Aurora", "Twilight", "Eclipse", "Solstice", "Nebula"],
        ["Vintage", "Modern", "Cyber", "Retro", "Holo"],
        ["Wood", "Iron", "Glass", "Crystal", "Diamond"],
        ["Pixel", "Vector", "Scribble", "Glitch", "Neon"],
    ]
    rng = random.Random(collection)
    palette = rng.choice(palettes)
    suffix = rng.choice(
        ["Edition", "Variant", "Form", "Style", "Cut", "Finish", "Tier", "Mark"]
    )
    return [f"{p} {suffix}" for p in palette]


# ─── helpers ───────────────────────────────────────────────────────


@dataclass
class DemoTrade:
    gift_id: str
    gift_name: str
    collection: str
    buy_price: float
    sell_price: float
    gross_profit: float
    net_profit: float
    profit_pct: float
    sold_at: datetime


def _rarity_band(promille: float) -> str:
    if promille < 5:
        return "Legendary"
    if promille < 20:
        return "Epic"
    if promille < 80:
        return "Rare"
    if promille < 200:
        return "Uncommon"
    return "Common"


def make_collections() -> list[dict[str, Any]]:
    """Return a copy of the canonical collections list (already shaped for the API)."""
    return [
        {
            "name": c["name"],
            "title": c["title"],
            "floor_price": c["floor"],
            "volume": c["volume_24h"],
            "is_new": False,
            "previous_floor": round(c["floor"] * random.Random(c["name"]).uniform(0.85, 1.10), 3),
        }
        for c in COLLECTIONS
    ]


def make_models_index() -> dict[str, list[str]]:
    return {c["name"]: list(_models_for(c["name"])) for c in COLLECTIONS}


def make_listings(*, per_collection: int = 12, seed: int = 1337) -> list[dict[str, Any]]:
    """Return ~600 listings spread across all collections."""
    rng = random.Random(seed)
    out: list[dict[str, Any]] = []
    gid = 1
    for coll in COLLECTIONS:
        floor = float(coll["floor"])
        models = _models_for(coll["name"])
        for _ in range(per_collection):
            model = rng.choice(models)
            backdrop = rng.choice(BACKDROPS)
            symbol = rng.choice(SYMBOLS)
            number = rng.randint(1, 9999)
            model_promille = rng.choices(
                [3, 8, 25, 60, 120, 180, 350],
                weights=[1, 2, 4, 6, 8, 6, 4],
            )[0]
            backdrop_promille = rng.choices(
                [5, 25, 80, 150, 300],
                weights=[1, 3, 6, 6, 4],
            )[0]
            symbol_promille = rng.choices(
                [2, 8, 30, 100, 300],
                weights=[1, 2, 5, 6, 6],
            )[0]
            rarity_score = _composite_rarity_promille(
                model_promille, backdrop_promille, symbol_promille
            )
            multiplier = _price_multiplier_for_rarity(rarity_score)
            price = round(floor * rng.uniform(0.95, multiplier), 3)
            out.append({
                "id": f"g{gid}",
                "name": f"{model} #{number}",
                "title": f"{model} #{number}",
                "number": number,
                "collection": coll["name"],
                "collection_title": coll["title"],
                "model": model,
                "backdrop": backdrop,
                "symbol": symbol,
                "modelRarity": round(model_promille / 10.0, 2),
                "backdropRarity": round(backdrop_promille / 10.0, 2),
                "symbolRarity": round(symbol_promille / 10.0, 2),
                "rarity_band": _rarity_band(rarity_score),
                "is_on_sale": True,
                "is_mine": False,
                "minted": True,
                "mintable": rng.random() < 0.15,
                "price": price,
                "floor_price": floor,
            })
            gid += 1
    return out


def _composite_rarity_promille(model: float, backdrop: float, symbol: float) -> float:
    """Weighted composite (model 0.55 / backdrop 0.30 / symbol 0.15)."""
    return 0.55 * model + 0.30 * backdrop + 0.15 * symbol


def _price_multiplier_for_rarity(promille: float) -> float:
    """A rough price ladder mirroring the spec."""
    if promille < 5:
        return 9.0
    if promille < 20:
        return 5.0
    if promille < 80:
        return 3.0
    if promille < 200:
        return 1.7
    return 1.2


def make_trades(user_id: int, *, count: int = 80, seed: int = 4242) -> list[DemoTrade]:
    """Generate a fake trade history so analytics are not empty in DRY-RUN."""
    rng = random.Random(seed)
    listings = make_listings(seed=seed)
    out: list[DemoTrade] = []
    now = datetime.now(UTC)
    for _ in range(count):
        g = rng.choice(listings)
        buy = round(g["price"] * rng.uniform(0.85, 1.0), 3)
        sell = round(buy * rng.uniform(0.7, 1.6), 3)
        commission = round(sell * 0.05, 3)
        gross = round(sell - buy, 3)
        net = round(gross - commission, 3)
        pct = round((net / buy) * 100.0 if buy > 0 else 0.0, 2)
        sold_at = now - timedelta(
            hours=rng.randint(1, 24 * 30),
            minutes=rng.randint(0, 59),
        )
        out.append(
            DemoTrade(
                gift_id=g["id"],
                gift_name=g["title"],
                collection=g["collection"],
                buy_price=buy,
                sell_price=sell,
                gross_profit=gross,
                net_profit=net,
                profit_pct=pct,
                sold_at=sold_at,
            )
        )
    return out

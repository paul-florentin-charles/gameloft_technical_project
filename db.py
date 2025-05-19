from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

DATABASE_URL = "sqlite:///./profile_matcher.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Association tables for many-to-many relations
player_devices = Table(
    "player_devices",
    Base.metadata,
    Column("player_id", String, ForeignKey("players.player_id")),
    Column("device_id", Integer, ForeignKey("devices.id")),
)

player_inventory = Table(
    "player_inventory",
    Base.metadata,
    Column("player_id", String, ForeignKey("players.player_id")),
    Column("item_id", Integer, ForeignKey("inventory_items.id")),
)

campaign_countries = Table(
    "campaign_countries",
    Base.metadata,
    Column("campaign_name", String, ForeignKey("campaigns.name")),
    Column("country", String),
)

campaign_items_has = Table(
    "campaign_items_has",
    Base.metadata,
    Column("campaign_name", String, ForeignKey("campaigns.name")),
    Column("item", String),
)

campaign_items_does_not_have = Table(
    "campaign_items_does_not_have",
    Base.metadata,
    Column("campaign_name", String, ForeignKey("campaigns.name")),
    Column("item", String),
)


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model = Column(String)
    carrier = Column(String)
    firmware = Column(String)
    player_id = Column(String, ForeignKey("players.player_id"))


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    quantity = Column(Integer)
    player_id = Column(String, ForeignKey("players.player_id"))


class Clan(Base):
    __tablename__ = "clans"

    id = Column(String, primary_key=True)
    name = Column(String)


class Player(Base):
    __tablename__ = "players"

    player_id = Column(String, primary_key=True, index=True)
    credential = Column(String)
    created = Column(String)
    modified = Column(String)
    last_session = Column(String)
    total_spent = Column(Integer)
    total_refund = Column(Integer)
    total_transactions = Column(Integer)
    last_purchase = Column(String)
    level = Column(Integer)
    xp = Column(Integer)
    total_playtime = Column(Integer)
    country = Column(String)
    language = Column(String)
    birthdate = Column(String)
    gender = Column(String)
    _customfield = Column(String)
    clan_id = Column(String, ForeignKey("clans.id"))
    clan = relationship("Clan", backref="players")
    devices = relationship("Device", backref="player", cascade="all, delete-orphan")
    inventory = relationship(
        "InventoryItem", backref="player", cascade="all, delete-orphan"
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    name = Column(String, primary_key=True, index=True)
    game = Column(String)
    priority = Column(Float)
    start_date = Column(String)
    end_date = Column(String)
    enabled = Column(Boolean)
    last_updated = Column(String)
    matcher_level_min = Column(Integer)
    matcher_level_max = Column(Integer)
    # Relations for has/does_not_have
    countries = relationship(
        "CampaignCountry", backref="campaign", cascade="all, delete-orphan"
    )
    items_has = relationship(
        "CampaignItemHas", backref="campaign", cascade="all, delete-orphan"
    )
    items_does_not_have = relationship(
        "CampaignItemDoesNotHave", backref="campaign", cascade="all, delete-orphan"
    )


class CampaignCountry(Base):
    __tablename__ = "campaign_countries_table"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_name = Column(String, ForeignKey("campaigns.name"))
    country = Column(String)


class CampaignItemHas(Base):
    __tablename__ = "campaign_items_has_table"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_name = Column(String, ForeignKey("campaigns.name"))
    item = Column(String)


class CampaignItemDoesNotHave(Base):
    __tablename__ = "campaign_items_does_not_have_table"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_name = Column(String, ForeignKey("campaigns.name"))
    item = Column(String)


Base.metadata.create_all(bind=engine)

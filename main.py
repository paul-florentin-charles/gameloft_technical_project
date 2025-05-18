from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from db import (
    Campaign,
    CampaignCountry,
    CampaignItemDoesNotHave,
    CampaignItemHas,
    Clan,
    Device,
    InventoryItem,
    Player,
    SessionLocal,
)
from schemas import (
    CampaignMatcherSchema,
    CampaignSchema,
    ClanSchema,
    DeviceSchema,
    InventoryItemSchema,
    PlayerSchema,
)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_player_profile(db: Session, player_id: str) -> dict:
    player = db.query(Player).filter(Player.player_id == player_id).first()
    if not player:
        return {}

    # Assemble player dict from normalized tables
    profile = {
        "player_id": player.player_id,
        "credential": player.credential,
        "created": player.created,
        "modified": player.modified,
        "last_session": player.last_session,
        "total_spent": player.total_spent,
        "total_refund": player.total_refund,
        "total_transactions": player.total_transactions,
        "last_purchase": player.last_purchase,
        "active_campaigns": [],  # Will be filled later
        "devices": [
            {"id": d.id, "model": d.model, "carrier": d.carrier, "firmware": d.firmware}
            for d in player.devices
        ],
        "level": player.level,
        "xp": player.xp,
        "total_playtime": player.total_playtime,
        "country": player.country,
        "language": player.language,
        "birthdate": player.birthdate,
        "gender": player.gender,
        "inventory": [
            {"name": item.name, "quantity": item.quantity} for item in player.inventory
        ],
        "clan": {"id": player.clan.id, "name": player.clan.name}
        if player.clan
        else None,
        "_customfield": player._customfield,
    }

    # Validate and parse using PlayerSchema
    return PlayerSchema(**profile).dict()


def get_current_campaigns(db: Session) -> list:
    result: list[dict[str, Any]] = []
    for campaign in db.query(Campaign).all():
        result.append(
            {
                "game": campaign.game,
                "name": campaign.name,
                "priority": campaign.priority,
                "matchers": {
                    "level": {
                        "min": campaign.matcher_level_min,
                        "max": campaign.matcher_level_max,
                    },
                    "has": {
                        "country": [
                            campaign_country.country
                            for campaign_country in campaign.countries
                        ],
                        "items": [
                            campaign_item_has.item
                            for campaign_item_has in campaign.items_has
                        ],
                    },
                    "does_not_have": {
                        "items": [
                            campaign_item_not_have.item
                            for campaign_item_not_have in campaign.items_does_not_have
                        ],
                    },
                },
                "start_date": campaign.start_date,
                "end_date": campaign.end_date,
                "enabled": campaign.enabled,
                "last_updated": campaign.last_updated,
            }
        )

    return result


def profile_matches_campaign(profile: dict[str, Any], campaign: dict[str, Any]) -> bool:
    matchers = campaign["matchers"]

    # Level matcher
    level = profile.get("level", 0)
    if not (matchers["level"]["min"] <= level <= matchers["level"]["max"]):
        return False

    # Has matcher
    if profile.get("country") not in matchers["has"].get("country", []):
        return False
    inventory_list = profile.get("inventory", [])
    def get_item_quantity(inv, name):
        for entry in inv:
            if entry["name"] == name:
                return entry["quantity"]
        return 0
    for item in matchers["has"].get("items", []):
        if get_item_quantity(inventory_list, item) < 1:
            return False

    # Does not have matcher
    for item in matchers.get("does_not_have", {}).get("items", []):
        if get_item_quantity(inventory_list, item) > 0:
            return False

    # Date check
    start = datetime.strptime(campaign["start_date"], "%Y-%m-%d %H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    end = datetime.strptime(campaign["end_date"], "%Y-%m-%d %H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )

    if not (start <= datetime.now(timezone.utc) <= end):
        return False

    if not campaign["enabled"]:
        return False

    return True


@app.get("/get_client_config/{player_id}")
def get_client_config(player_id: str, db: Session = Depends(get_db)):
    profile = get_player_profile(db, player_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Player not found")

    active_campaigns: list[str] = []
    for campaign in get_current_campaigns(db):
        if profile_matches_campaign(profile, campaign):
            active_campaigns.append(campaign["name"])

    updated_profile = profile.copy()
    updated_profile["active_campaigns"] = active_campaigns

    return updated_profile


@app.post("/create_mock_data")
def create_mock_data(db: Session = Depends(get_db)):
    # Clear tables
    db.query(Device).delete()
    db.query(InventoryItem).delete()
    db.query(Player).delete()
    db.query(Clan).delete()
    db.query(CampaignCountry).delete()
    db.query(CampaignItemHas).delete()
    db.query(CampaignItemDoesNotHave).delete()
    db.query(Campaign).delete()
    db.commit()

    # Create mock data using Pydantic models
    player_seed = PlayerSchema(
        player_id="97983be2-98b7-11e7-90cf-082e5f28d836",
        credential="apple_credential",
        created="2021-01-10 13:37:17Z",
        modified="2021-01-23 13:37:17Z",
        last_session="2021-01-23 13:37:17Z",
        total_spent=400,
        total_refund=0,
        total_transactions=5,
        last_purchase="2021-01-22 13:37:17Z",
        devices=[
            DeviceSchema(model="apple iphone 11", carrier="vodafone", firmware="123")
        ],
        level=3,
        xp=1000,
        total_playtime=144,
        country="CA",
        language="fr",
        birthdate="2000-01-10 13:37:17Z",
        gender="male",
        inventory=[
            InventoryItemSchema(name="cash", quantity=123),
            InventoryItemSchema(name="coins", quantity=123),
            InventoryItemSchema(name="item_1", quantity=1),
            InventoryItemSchema(name="item_34", quantity=3),
            InventoryItemSchema(name="item_55", quantity=2),
        ],
        clan=ClanSchema(id="123456", name="Hello world clan"),
        _customfield="mycustom",  # Use public field, not _customfield
    )

    campaign_seed = CampaignSchema(
        name="mycampaign",
        game="mygame",
        priority=10.5,
        matchers=CampaignMatcherSchema(
            level={"min": 1, "max": 3},
            has={"country": ["US", "RO", "CA"], "items": ["item_1"]},
            does_not_have={"items": ["item_4"]},
        ),
        start_date="2025-04-25 00:00:00Z",
        end_date="2025-06-25 00:00:00Z",
        enabled=True,
        last_updated="2025-05-16 11:46:58Z",
    )

    # Insert clan
    clan = Clan(id=player_seed.clan.id, name=player_seed.clan.name)
    db.add(clan)
    db.commit()

    # Insert player
    player = Player(
        player_id=player_seed.player_id,
        credential=player_seed.credential,
        created=player_seed.created,
        modified=player_seed.modified,
        last_session=player_seed.last_session,
        total_spent=player_seed.total_spent,
        total_refund=player_seed.total_refund,
        total_transactions=player_seed.total_transactions,
        last_purchase=player_seed.last_purchase,
        level=player_seed.level,
        xp=player_seed.xp,
        total_playtime=player_seed.total_playtime,
        country=player_seed.country,
        language=player_seed.language,
        birthdate=player_seed.birthdate,
        gender=player_seed.gender,
        _customfield=player_seed.customfield,  # Use public field
        clan_id=clan.id,
    )
    db.add(player)
    db.commit()

    # Insert devices
    for device in player_seed.devices:
        db.add(
            Device(
                model=device.model,
                carrier=device.carrier,
                firmware=device.firmware,
                player_id=player.player_id,
            )
        )

    #  Insert inventory
    for item in player_seed.inventory:
        db.add(
            InventoryItem(
                name=item.name, quantity=item.quantity, player_id=player.player_id
            )
        )
    db.commit()

    # Insert campaign
    campaign = Campaign(
        name=campaign_seed.name,
        game=campaign_seed.game,
        priority=campaign_seed.priority,
        start_date=campaign_seed.start_date,
        end_date=campaign_seed.end_date,
        enabled=campaign_seed.enabled,
        last_updated=campaign_seed.last_updated,
        matcher_level_min=campaign_seed.matchers.level["min"],
        matcher_level_max=campaign_seed.matchers.level["max"],
    )
    db.add(campaign)
    db.commit()

    # Insert campaign matchers
    for country in campaign_seed.matchers.has["country"]:
        db.add(CampaignCountry(campaign_name=campaign.name, country=country))
    for item in campaign_seed.matchers.has["items"]:
        db.add(CampaignItemHas(campaign_name=campaign.name, item=item))
    for item in campaign_seed.matchers.does_not_have["items"]:
        db.add(CampaignItemDoesNotHave(campaign_name=campaign.name, item=item))
    db.commit()

    return {"message": "Created mock player and campaign data."}

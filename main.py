from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from db import (
    Base,
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
    player = db.get(Player, player_id)
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
        "active_campaigns": [],
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
    models: list[type[Base]] = [
        Device,
        InventoryItem,
        Player,
        Clan,
        CampaignCountry,
        CampaignItemHas,
        CampaignItemDoesNotHave,
        Campaign,
    ]

    for model in models:
        db.query(model).delete()

    db.commit()

    # Create mock data using Pydantic models
    player_mock_data = PlayerSchema(
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
        _customfield="mycustom",
    )

    campaign_mock_data = CampaignSchema(
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
    clan = Clan(id=player_mock_data.clan.id, name=player_mock_data.clan.name)
    db.add(clan)
    db.flush()

    # Insert player
    player = Player(
        player_id=player_mock_data.player_id,
        credential=player_mock_data.credential,
        created=player_mock_data.created,
        modified=player_mock_data.modified,
        last_session=player_mock_data.last_session,
        total_spent=player_mock_data.total_spent,
        total_refund=player_mock_data.total_refund,
        total_transactions=player_mock_data.total_transactions,
        last_purchase=player_mock_data.last_purchase,
        level=player_mock_data.level,
        xp=player_mock_data.xp,
        total_playtime=player_mock_data.total_playtime,
        country=player_mock_data.country,
        language=player_mock_data.language,
        birthdate=player_mock_data.birthdate,
        gender=player_mock_data.gender,
        _customfield=player_mock_data.customfield,
        clan_id=clan.id,
    )
    db.add(player)
    db.flush()

    # Insert devices
    for device in player_mock_data.devices:
        db.add(
            Device(
                model=device.model,
                carrier=device.carrier,
                firmware=device.firmware,
                player_id=player.player_id,
            )
        )

    #  Insert inventory
    for item in player_mock_data.inventory:
        db.add(
            InventoryItem(
                name=item.name, quantity=item.quantity, player_id=player.player_id
            )
        )
    db.flush()

    # Insert campaign
    campaign = Campaign(
        name=campaign_mock_data.name,
        game=campaign_mock_data.game,
        priority=campaign_mock_data.priority,
        start_date=campaign_mock_data.start_date,
        end_date=campaign_mock_data.end_date,
        enabled=campaign_mock_data.enabled,
        last_updated=campaign_mock_data.last_updated,
        matcher_level_min=campaign_mock_data.matchers.level["min"],
        matcher_level_max=campaign_mock_data.matchers.level["max"],
    )
    db.add(campaign)
    db.flush()

    # Insert campaign matchers
    for country in campaign_mock_data.matchers.has["country"]:
        db.add(CampaignCountry(campaign_name=campaign.name, country=country))
    for item in campaign_mock_data.matchers.has["items"]:
        db.add(CampaignItemHas(campaign_name=campaign.name, item=item))
    for item in campaign_mock_data.matchers.does_not_have["items"]:
        db.add(CampaignItemDoesNotHave(campaign_name=campaign.name, item=item))

    db.commit()

    return {"message": "Created mock player and campaign data."}

from typing import List

from pydantic import BaseModel, Field


class DeviceSchema(BaseModel):
    model: str
    carrier: str
    firmware: str


class InventoryItemSchema(BaseModel):
    name: str
    quantity: int


class ClanSchema(BaseModel):
    id: str
    name: str


class PlayerSchema(BaseModel):
    player_id: str
    credential: str
    created: str
    modified: str
    last_session: str
    total_spent: int
    total_refund: int
    total_transactions: int
    last_purchase: str
    active_campaigns: list[str]
    devices: List[DeviceSchema]
    level: int
    xp: int
    total_playtime: int
    country: str
    language: str
    birthdate: str
    gender: str
    inventory: List[InventoryItemSchema]
    clan: ClanSchema
    customfield: str = Field(..., alias="_customfield")


class CampaignMatcherSchema(BaseModel):
    level: dict
    has: dict
    does_not_have: dict


class CampaignSchema(BaseModel):
    name: str
    game: str
    priority: float
    matchers: CampaignMatcherSchema
    start_date: str
    end_date: str
    enabled: bool
    last_updated: str

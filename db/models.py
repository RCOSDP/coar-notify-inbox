from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActorResource(BaseModel):
    id: str
    type: list[str] | str
    name: list[str] | str


class InboxResource(BaseModel):
    id: str
    inbox: str
    type: list[str] | str


class UrlObject(BaseModel):
    id: str
    media_type: str | None = Field(alias="mediaType", default=None)
    type: list[str] | str | None = None


class DocumentObject(BaseModel):
    id: str
    object: str | None = None
    type: list[str] | str | None = None
    ietf_cite_as: str | None = Field(alias="ietf:cite-as", default=None)
    url: UrlObject | None = None
    name: str | None = None


class ContextObject(BaseModel):
    id: str
    ietf_cite_as: str | None = Field(alias="ietf:cite-as", default=None)
    type: list[str] | str | None = None


class Notification(BaseModel):
    id: str
    updated: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    at_context: list[str] = Field(alias="@context")
    type: list[str] | str
    origin: InboxResource
    target: InboxResource
    object: DocumentObject
    actor: ActorResource | None = None
    context: ContextObject | None = None
    in_reply_to: str | None = Field(alias="inReplyTo", default=None)

    model_config = ConfigDict(
        use_alias=True,
        populate_by_name=True,
        validate_assignment=True
    )

    @field_validator("updated")
    @classmethod
    def validate_updated(cls, v: str | datetime):
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v


class NotificationState(BaseModel):
    id: str
    read: bool


class NotificationStateUpdatePayload(BaseModel):
    read: bool

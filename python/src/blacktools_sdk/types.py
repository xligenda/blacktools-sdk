from __future__ import annotations

from typing import Literal, TypedDict


class TokenPair(TypedDict):
    access_token: str
    refresh_token: str
    user_id: int
    expires_at: int  # unix


class PermsCheckResult(TypedDict):
    granted: bool


class _ProfileRequired(TypedDict):
    user_id: int
    nickname: str
    created_at: str  # RFC3339


class Profile(_ProfileRequired, total=False):
    discord_id: str
    vk_id: int
    tg_id: int
    forum_id: int
    google_id: str
    roles: list[str]
    vk_name: str
    telegram_name: str
    forum_name: str
    forum_view_url: str
    email: str


class PostSnapshot(TypedDict):
    server_code: str
    # S<index>" for a server post, "G" for a global
    server_name: str
    permission_group: str
    access_level: int
    is_temp: bool
    is_moderator: bool
    ticket: str


PostHistoryKind = Literal["moderator", "other"]
"""Which posts a post history covers: Discord moderator posts, or every other post."""

PostHistoryEventKind = Literal[
    "assigned", "promoted", "demoted", "regrouped", "discharged", "temp_on", "temp_off", "changed"
]


class _PostHistoryActorRequired(TypedDict):
    discord_id: str


class PostHistoryActor(_PostHistoryActorRequired, total=False):
    name: str


class _PostHistoryEventRequired(TypedDict):
    kind: PostHistoryEventKind
    occurred_at: str  # RFC3339
    backfilled: bool


class PostHistoryEvent(_PostHistoryEventRequired, total=False):
    permission_group: str
    access_level: int
    prev_permission_group: str
    prev_access_level: int
    actor: PostHistoryActor  # who toggled ВРИО, only on temp_on/temp_off


class _PostHistoryPostRequired(TypedDict):
    server_code: str  # "S<index>" for a server post, "G" for a global
    server_name: str
    permission_group: str
    access_level: int
    is_moderator: bool
    is_temp: bool
    ticket: str
    assigned_at: str  # RFC3339
    events: list[PostHistoryEvent]  # newest first


class PostHistoryPost(_PostHistoryPostRequired, total=False):
    discharged_at: str  # RFC3339, absent while the post is active


class _PostHistoryRequired(TypedDict):
    posts: list[PostHistoryPost]  # active first, then discharged ones newest first


class PostHistory(_PostHistoryRequired, total=False):
    tracked_since: str  # RFC3339, changes before it are reconstructed (backfilled)


WarnKind = Literal["warning", "reprimand"]


class _WarnRequired(TypedDict):
    id: int
    reason: str
    value: int
    kind: WarnKind
    issued_at: str  # RFC3339
    issued_by: str  # RFC3339


class Warn(_WarnRequired, total=False):
    revoked_at: str  # RFC3339
    revoked_by: str


class ExpandedConnections(TypedDict, total=False):
    vk_name: str
    telegram_name: str
    discord_name: str
    forum_name: str
    forum_view_url: str


class _StaffRoleAssignmentRequired(TypedDict):
    assignment_id: int
    kind: str
    granted_by: str
    created_at: str  # RFC3339


class StaffRoleAssignment(_StaffRoleAssignmentRequired, total=False):
    role_name: str


class _ModeratorRequired(TypedDict):
    user_id: str
    sso_user_id: int
    nickname: str
    permission_group: str
    access_level: int
    is_temp: bool
    roles: list[StaffRoleAssignment]


class Moderator(_ModeratorRequired, total=False):
    discord_name: str
    avatar_url: str
    tg_id: int
    promoted_at: str  # RFC3339
    active_warnings: int  # absent if counts hidden
    active_reprimands: int  # absent if counts hidden


class _ConnectionsRequired(TypedDict):
    discord_id: str


class Connections(_ConnectionsRequired, total=False):
    discord_name: str
    vk_id: int
    vk_name: str
    tg_id: int
    telegram_name: str
    forum_id: int
    forum_name: str
    forum_view_url: str
    google_id: str
    google_email: str


ButtonStyle = Literal["ok", "no", "grey", "warm", "link"]


class _ButtonRequired(TypedDict):
    label: str  # 1 - 40 chars


class Button(_ButtonRequired, total=False):
    style: ButtonStyle
    url: str  # absolute url, up to 512 chars
    payload: str  # 1024 bytes


class _NotifyRequestRequired(TypedDict):
    kind: str
    title: str
    body: str


class NotifyRequest(_NotifyRequestRequired, total=False):
    buttons: list[Button]  # max 3
    idempotency_key: str  # up to 128 chars


class NotifyServerResult(TypedDict):
    delivered: int
    failed: int
    total: int


class NotifyModeratorResult(TypedDict):
    delivered: bool


class WebhookConfig(TypedDict):
    url: str
    secret: str


class WebhookAction(TypedDict):
    index: int
    label: str
    payload: str


class _WebhookUserRequired(TypedDict):
    id: int


class WebhookUser(_WebhookUserRequired, total=False):
    discord_id: str
    tg_id: int


class _WebhookEventRequired(TypedDict):
    type: str
    id: str
    notification_id: int
    kind: str
    action: WebhookAction
    user: WebhookUser
    channel: Literal["app", "telegram", "discord"]
    occurred_at: str  # RFC3339


class WebhookEvent(_WebhookEventRequired, total=False):
    server_index: int


class WebhookResponse(TypedDict, total=False):
    message: str  # up to 200 chars
    acted_label: str

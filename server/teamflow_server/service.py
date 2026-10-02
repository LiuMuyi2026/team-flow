"""service 层：状态机与规则。REST 与 MCP 两个适配层都只调这里。

M0 原型：数据放内存。所有公开方法在同一把可重入锁里执行，用来模拟数据库事务和
"UPDATE ... WHERE status='open' AND assignee IS NULL" 这种条件更新的原子性
（FastAPI 的同步端点和 FastMCP 的同步工具都跑在线程池里，所以锁是真的在起作用）。

规则来源：docs/plan.md 第 3.1、5.1–5.4、6.2、6.4 节。
"""

from __future__ import annotations

import fnmatch
import json
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable, Literal

from . import config
from .errors import DomainError
from .sanitize import clean, ident_or_hash, mask, one_line, scan, sha256, unsafe_title

TZ = timezone(timedelta(hours=8))  # Asia/Shanghai，无夏令时
WS = "team"

HANDLE_RE = re.compile(r"^[a-z][a-z0-9_]{1,15}$")
ID_RE = re.compile(r"^([TB])-(\d{1,6})$")

CLIENT_NAMES = {"claude_code": "Claude Code", "codex": "Codex", "cli": "命令行", "cloud": "云端会话"}

LIMITS = {"title": 120, "body": 4000, "note": 500, "comment": 2000, "detail": 2000, "tried": 1000}

TEXT_EVENT_TYPES = {"note", "comment", "task.released", "task.canceled", "task.done", "task.declined", "blocker.resolved"}

# 网页详情页（for_human）给每条动态带的结构化字段：只放 handle、枚举、编号，不放自由文本
HUMAN_EVENT_DATA = ("to", "need", "reason", "v", "through")

# MCP 工具名（与 mcp_server.TOOL_ORDER 一致，测试里断言）。tool_map 条目的 tool 字段只认这些。
TOOL_NAMES = ("inbox", "list_tasks", "get_item", "team_status", "create_task", "claim_task", "update_task", "report_blocker", "comment")
READ_TOOL_NAMES = frozenset({"inbox", "list_tasks", "get_item", "team_status"})

# Claude Code 的 tools/call 带 _meta["claudecode/toolUseId"]，等于同一次调用 PostToolUse hook 输入的 tool_use_id
# （spike/results/S3.md 结论 3）。一方 API 是 toolu_ + 字母数字；Bedrock、Vertex 的形如 toolu_bdrk_…、toolu_vrtx_…，
# 所以放行下划线。不合格的一律丢弃（不记、不匹配）。
TOOL_USE_RE = re.compile(r"^toolu_[A-Za-z0-9_]{8,80}$")
TOOL_MAP_TTL = timedelta(hours=24)  # 映射（和按 tool_use_id 找事件的索引）只保留 24 小时
START_EVENT_TYPES = frozenset({"task.claimed", "task.started"})


def tool_use_id(raw: Any) -> str | None:
    """校验 tool_use_id（_meta["claudecode/toolUseId"] 或 tool_map 条目里的）：不合格返回 None。"""
    return raw if isinstance(raw, str) and TOOL_USE_RE.fullmatch(raw) else None  # fullmatch：$ 会放过结尾的换行


def session_tag(s: "AgentSession") -> str:
    """会话短标签（"会话 1a6941c0"）：external_id 去掉哈希前缀和分隔符后的前 8 个字母数字。"""
    ext = s.external_id[2:] if s.external_id.startswith("h:") else s.external_id
    return re.sub(r"[^0-9A-Za-z]", "", ext)[:8]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hm(dt: datetime | None) -> str | None:
    return dt.astimezone(TZ).strftime("%H:%M") if dt else None


def mdhm(dt: datetime | None) -> str | None:
    return dt.astimezone(TZ).strftime("%m-%d %H:%M") if dt else None


def client_name(client: str | None) -> str:
    return CLIENT_NAMES.get(client or "", client or "")


# ---------------------------------------------------------------------------
# 实体
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Actor:
    """一次写入的发起者（actor 四元组 + via）。PAT 一律按 agent 记账（H1）。"""

    handle: str
    kind: Literal["human", "agent"]
    client: str | None = None  # claude_code / codex / cli；人为 None
    token_id: str | None = None
    via: str = "mcp"  # mcp / rest / hook / dev / wechat / seed
    session: str | None = None  # 精确归属到的会话 external_id（必须经 resolve_session 校验）
    attribution: str = "member"  # exact / member
    thread: str | None = None  # Codex 子线程（x-codex-turn-metadata.thread_id），只作记录，不参与归属
    tool_use: str | None = None  # Claude Code 的 _meta["claudecode/toolUseId"]（已校验格式），记到这次调用产生的事件上
    session_src: str | None = None  # 精确归属的来源：codex_meta / header / tool_map

    @property
    def bk(self) -> str:
        return self.kind


@dataclass
class Member:
    handle: str
    name: str
    active: bool = True
    git_emails: list[str] = field(default_factory=list)


@dataclass
class Project:
    key: str
    name: str
    repo_patterns: list[str] = field(default_factory=list)


@dataclass
class Task:
    id: str
    no: int
    title: str
    body: str | None
    created_by: str
    created_by_kind: str
    created_by_client: str | None
    created_via: str
    created_at: datetime
    steward: str
    status: str = "open"  # open / in_progress / done / canceled
    assignee: str | None = None
    assign_state: str = "none"  # none / pending / accepted
    assign_seq: int = 0
    assigned_by: str | None = None
    assigned_by_kind: str | None = None
    assigned_by_client: str | None = None
    content_version: int = 1
    content_sha256: str = ""
    urgent: bool = False
    project: str | None = None
    parent: str | None = None
    claimed_client: str | None = None
    claimed_at: datetime | None = None
    started_at: datetime | None = None
    done_at: datetime | None = None
    last_activity_at: datetime | None = None

    @property
    def author(self) -> str:
        return self.created_by

    @property
    def label(self) -> str:
        if self.status == "open":
            if self.assignee is None:
                return "pool"
            return "pending" if self.assign_state == "pending" else "todo"
        return {"in_progress": "doing"}.get(self.status, self.status)


@dataclass
class Blocker:
    id: str
    no: int
    title: str
    detail: str | None
    tried: str | None
    raised_by: str
    raised_by_kind: str
    raised_by_client: str | None
    created_at: datetime
    task_id: str | None = None
    project: str | None = None
    needs: str | None = None
    need_state: str = "none"  # none / proposed / asked
    helper: str | None = None
    status: str = "open"  # open / resolved
    content_version: int = 1
    content_sha256: str = ""
    task_closed: bool = False
    resolved_at: datetime | None = None
    last_activity_at: datetime | None = None

    @property
    def author(self) -> str:
        return self.raised_by


@dataclass
class Event:
    id: int
    type: str
    subject: str | None
    actor: str | None
    actor_kind: str  # human / agent / system
    client: str | None
    via: str
    at: datetime
    text: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    token_id: str | None = None
    session: str | None = None  # actor_session_id：精确归属到的会话 external_id
    thread: str | None = None
    tool_use: str | None = None  # 产生这条事件的 MCP 调用的 claudecode/toolUseId（和 token_id 一起用来对映射）
    attribution: str | None = None  # agent 事件：exact / member；人和系统的事件为 None
    session_src: str | None = None  # exact 的来源：codex_meta / header / tool_map（tool_map 是事后补上的）


@dataclass
class Acceptance:
    """本人对某个对象的"看见"记录。

    content_version / content_sha256 为 None 表示只"转发"过动态（推进了 through_event_id），从没接受过正文：
    转发绝不授予或升级正文可见性（I1）。
    """

    handle: str
    subject: str
    content_version: int | None
    content_sha256: str | None
    through_event_id: int
    via: str
    at: datetime

    @property
    def accepted(self) -> bool:
        return self.content_version is not None


@dataclass
class AgentSession:
    client: str
    external_id: str
    handle: str
    token_id: str | None
    repo: str | None = None
    branch: str | None = None
    head: str | None = None
    cwd_name: str | None = None
    interactive: bool | None = None
    source: str | None = None
    machine_id: str | None = None
    current_task: str | None = None
    current_task_ev: int | None = None  # 设置 current_task 的那条事件 ID：迟到的映射不能用更早的事件覆盖更新的指向
    started_at: datetime | None = None
    last_seen_at: datetime | None = None
    ended_at: datetime | None = None
    end_reason: str | None = None


@dataclass
class ToolMap:
    """PostToolUse 上报的映射：(token_id, tool_use_id) → 会话。只保留 24 小时。"""

    session: str  # 会话 external_id（登记它的 token 必须是上报映射的 token，client 必须是 claude_code）
    tool: str | None
    at: datetime
    expires_at: datetime


@dataclass
class IdemRec:
    fingerprint: str
    state: str  # in_flight / done
    status: int = 0
    response: Any = None
    expires_at: datetime | None = None


# ---------------------------------------------------------------------------
# service
# ---------------------------------------------------------------------------


class Service:
    def __init__(self, clock: Callable[[], datetime] = now_utc) -> None:
        self.clock = clock
        self.lock = threading.RLock()
        self.reset()

    # -- 基础 ----------------------------------------------------------------

    def reset(self) -> None:
        with self.lock:
            self.members: dict[str, Member] = {}
            self.projects: dict[str, Project] = {}
            self.tasks: dict[str, Task] = {}
            self.blockers: dict[str, Blocker] = {}
            self.events: list[Event] = []
            self.acceptances: dict[tuple[str, str], Acceptance] = {}
            self.sessions: dict[tuple[str, str], AgentSession] = {}
            self.outbox: list[dict[str, Any]] = []
            self.audit: list[dict[str, Any]] = []
            self.idem: dict[tuple[str, str, str], IdemRec] = {}
            self.dedupe: dict[tuple[str, str, str], tuple[datetime, dict[str, Any]]] = {}
            self.hook_keys: dict[tuple[str, str], datetime] = {}
            # (token_id, tool_use_id) → 映射；(token_id, tool_use_id) → 这次调用产生的事件（24 小时内的索引）
            self.tool_maps: dict[tuple[str, str], ToolMap] = {}
            self.call_events: dict[tuple[str, str], list[Event]] = {}
            self.commit_keys: set[tuple[str, str]] = set()
            self.cursors: dict[str, int] = {}
            self.pool_seen: dict[str, datetime] = {}
            self.next_task_no = 1
            self.next_blocker_no = 1
            self._next_event_id = 1

    def now(self) -> datetime:
        return self.clock()

    def url(self, obj_id: str) -> str:
        kind = "task" if obj_id.startswith("T-") else "blocker"
        return f"{config.public_url()}/{kind}?w={WS}&id={obj_id}"

    def add_member(self, handle: str, name: str, git_emails: Iterable[str] = ()) -> Member:
        if not HANDLE_RE.fullmatch(handle):
            raise ValueError(f"bad handle {handle!r}")
        with self.lock:
            m = Member(handle, name, True, list(git_emails))
            self.members[handle] = m
            return m

    def add_project(self, key: str, name: str, repo_patterns: Iterable[str] = ()) -> Project:
        with self.lock:
            p = Project(key, name, list(repo_patterns))
            self.projects[key] = p
            return p

    def _emit(
        self,
        type_: str,
        subject: str | None,
        actor: Actor | None,
        text: str | None = None,
        **data: Any,
    ) -> Event:
        exact = bool(actor and actor.session and actor.attribution == "exact")
        ev = Event(
            id=self._next_event_id,
            type=type_,
            subject=subject,
            actor=actor.handle if actor else None,
            actor_kind=actor.kind if actor else "system",
            client=actor.client if actor else None,
            via=actor.via if actor else "system",
            at=self.now(),
            text=text,
            data={k: v for k, v in data.items() if v is not None},
            token_id=actor.token_id if actor else None,
            session=actor.session if exact and actor else None,
            thread=actor.thread if actor else None,
            tool_use=tool_use_id(actor.tool_use) if actor else None,
            attribution=("exact" if exact else "member") if actor and actor.kind == "agent" else None,
            session_src=(actor.session_src if exact and actor else None),
        )
        self._next_event_id += 1
        self.events.append(ev)
        if ev.tool_use and ev.token_id:
            self.call_events.setdefault((ev.token_id, ev.tool_use), []).append(ev)
            if ev.attribution == "member":
                # 映射先到、或在调用途中到了：这条事件直接判 exact（会话仍要有效）
                s = self._tool_map_target(ev.token_id, ev.tool_use, ev.actor, ev.client)
                if s is not None:
                    self._attach(ev, s)
        return ev

    def _notify(self, to: str | None, kind: str, subject: str, text: str, actor: Actor | None, dedupe_key: str) -> None:
        """模拟微信模板消息：只放编号、handle、客户端（H5）。M0 不真的发送，只进 outbox。"""
        if not to or (actor and to == actor.handle):
            return  # 不给自己发
        member = self.members.get(to)
        if not member or not member.active:
            return
        now = self.now()
        for n in reversed(self.outbox):
            if n["to"] == to and n["dedupe_key"] == dedupe_key:
                if kind != "agent_asks" or now - n["at"] < timedelta(minutes=10):
                    return
                break
        self.outbox.append({"to": to, "kind": kind, "subject": subject, "text": text, "dedupe_key": dedupe_key, "at": now})

    def _audit(self, action: str, actor: Actor | None, result: str, **detail: Any) -> None:
        self.audit.append(
            {"at": self.now(), "action": action, "h": actor.handle if actor else None, "result": result, **detail}
        )

    # -- 校验与清洗 ----------------------------------------------------------------

    def _text(self, field_name: str, value: str | None, *, required: bool = False) -> str | None:
        v = clean(value)
        if not v:
            if required:
                raise DomainError("invalid", f"{field_name} 不能为空。")
            return None
        limit = LIMITS[field_name]
        if len(v) > limit:
            raise DomainError("invalid", f"{field_name} 最多 {limit} 字，现在是 {len(v)} 字，请精简后重试。")
        hit = scan(v)
        if hit:
            raise DomainError(
                "secret_detected",
                f"{field_name} 里疑似有密钥或个人信息（规则 {hit.rule}，第 {hit.pos + 1} 个字符起）。"
                "请删掉这部分后重试，不要把密钥、token 或个人信息写进看板。",
                rule=hit.rule,
                pos=hit.pos,
            )
        return v

    def _title(self, actor: Actor, value: str | None) -> str | None:
        """标题：清洗、长度、扫描之外（plan 5.1 闸门表、I6）：

        - 所有标题一律单行。人写的把换行（含 U+2028/2029、NEL 等）折成空格；agent 写的带换行直接 422。
        - agent 写的标题更严：团队档下标题是唯一不经接受就跨人送到 agent 的自由文本，所以在 NFKC 骨架上
          检查网址或域名、路径、管道或重定向、反引号、命令替换（规则见 sanitize 的"标题"一节）。
        """
        if actor.kind != "agent" and value is not None:
            value = one_line(value)
        v = self._text("title", value, required=True)
        if actor.kind == "agent":
            hit = unsafe_title(v)
            if hit:
                self._audit("title.rejected", actor, "invalid", rule=hit.rule)
                raise DomainError(
                    "invalid",
                    "agent 写的标题必须是一行文字，不能有网址或域名、路径（~/、/etc、.aws/、C:\\、%VAR%、$HOME/）、"
                    f"管道或重定向（| >> 2> > 文件）、反引号、$( 或 ${{；这次是第 {hit.pos + 1} 个字符起的{hit.desc}。"
                    "标题请用文字描述，网址、路径和命令写进正文（正文要对方本人接受后才会给对方的 agent）。",
                    status=422,
                    rule=hit.rule,
                    pos=hit.pos,
                )
        return one_line(v)

    def _member(self, handle: str | None, *, what: str = "成员") -> Member:
        h = (handle or "").strip().lstrip("@").lower()
        m = self.members.get(h)
        if not m or not m.active:
            known = "、".join(sorted(x.handle for x in self.members.values() if x.active))
            raise DomainError("invalid", f"没有叫 {handle} 的{what}。可选的有：{known}。")
        return m

    def _norm_id(self, raw: str) -> str:
        s = (raw or "").strip().upper()
        if s.isdigit():
            s = "T-" + s
        m = ID_RE.match(s)
        if not m:
            raise DomainError("not_found", f"{raw} 不是有效的编号，任务形如 T-42，困难形如 B-7。")
        return f"{m.group(1)}-{int(m.group(2))}"

    def _task(self, raw: str) -> Task:
        tid = self._norm_id(raw)
        t = self.tasks.get(tid)
        if not t:
            raise DomainError("not_found", f"没有找到 {tid}。可以用 list_tasks 查看现有任务。", id=tid)
        return t

    def _blocker(self, raw: str) -> Blocker:
        bid = self._norm_id(raw)
        b = self.blockers.get(bid)
        if not b:
            raise DomainError("not_found", f"没有找到 {bid}。", id=bid)
        return b

    def _obj(self, raw: str) -> Task | Blocker:
        oid = self._norm_id(raw)
        return self._task(oid) if oid.startswith("T-") else self._blocker(oid)

    @staticmethod
    def _check_task(t: Task) -> None:
        """不变量 I1–I3（plan 5.2），数据库里是 CHECK 约束；这里每次改动后断言。"""
        assert (t.assignee is None) == (t.assign_state == "none"), f"I1 {t.id}"
        assert t.status != "in_progress" or t.assign_state == "accepted", f"I2 {t.id}"
        assert (t.done_at is not None) == (t.status == "done"), f"I3 {t.id}"

    def _touch(self, obj: Task | Blocker) -> None:
        obj.last_activity_at = self.now()

    # -- 信任与"看见"闸门 ----------------------------------------------------------

    @staticmethod
    def trust(author: str | None, author_kind: str, viewer: str) -> str:
        side = "self" if author == viewer else "peer"
        kind = "human" if author_kind == "human" else "agent"
        return f"{side}_{kind}"

    def envelope(self, text: str | None, author: str | None, author_kind: str, author_client: str | None, viewer: str) -> dict[str, Any]:
        """信封：{"t","by","trust","client"}。读取时按同一版规则再清洗一遍。"""
        return {
            "t": clean(text),
            "by": author,
            "trust": self.trust(author, author_kind, viewer),
            "client": author_client if author_kind != "human" else None,
        }

    def _title_env(self, obj: Task | Blocker, viewer: str) -> dict[str, Any]:
        """标题信封。读取时再折一次行：标题一律单行，旧数据里万一有换行也不会原样送到 agent。"""
        if isinstance(obj, Task):
            env = self.envelope(obj.title, obj.created_by, obj.created_by_kind, obj.created_by_client, viewer)
        else:
            env = self.envelope(obj.title, obj.raised_by, obj.raised_by_kind, obj.raised_by_client, viewer)
        env["t"] = one_line(env["t"])
        return env

    def can_see_content(self, viewer: str, obj: Task | Blocker) -> bool:
        """本人是作者直接为真；否则要有接受过正文的 acceptance，且版本和 sha 都等于对象当前值。
        start、get_item、闸门共用。只转发过动态（没接受正文）的记录不算。"""
        if obj.author == viewer:
            return True
        acc = self.acceptances.get((viewer, obj.id))
        return (
            acc is not None
            and acc.accepted
            and acc.content_version == obj.content_version
            and acc.content_sha256 == obj.content_sha256
        )

    def _text_visible(self, viewer: str, ev: Event, obj: Task | Blocker) -> bool:
        """评论类文字：人写的，接受过正文后都给，只转发过的给到 through 为止；agent 写的只给到 through。"""
        if ev.actor == viewer:
            return True
        acc = self.acceptances.get((viewer, obj.id))
        if acc is None:
            return False
        if ev.actor_kind == "human" and acc.accepted:
            return True
        return ev.id <= acc.through_event_id

    def _content_acceptors(self, obj_id: str, me: str) -> list[Acceptance]:
        """除我之外接受过正文的人（只转发过动态的不算）。"""
        return [a for (h, s), a in self.acceptances.items() if s == obj_id and h != me and a.accepted]

    def _events_view(self, viewer: str, obj: Task | Blocker, limit: int | None, *, for_human: bool = False) -> list[dict[str, Any]]:
        """动态列表。agent 看到的（for_human=False）按闸门过滤：最近 limit 条，看不到的文字折成 withheld。

        for_human=True 是网页详情页（plan 5.1"人在网页上看到的，就是同一个函数加上 for_human=True 的输出"、
        7.1"全部评论"）：全部动态、全部文字（同一版清洗），每条文字另标 agent=本人的 agent 现在能不能读到，
        页面据此提示"转发后，您的 Claude Code / Codex 才能读到这些评论"。"""
        evs = [e for e in self.events if e.subject == obj.id and e.type != "commit"]
        if not for_human:
            evs = evs[-limit:] if limit and limit > 0 else []
        out: list[dict[str, Any]] = []
        held: dict[str, int] = {}
        for e in evs:
            item: dict[str, Any] = {
                "e": e.id,
                "ty": e.type,
                "by": e.actor,
                "trust": self.trust(e.actor, e.actor_kind, viewer) if e.actor else "system",
                "client": e.client,
                "at": mdhm(e.at),
            }
            if for_human:
                item["ts"] = e.at.astimezone(TZ).isoformat(timespec="seconds")
                data = {k: e.data[k] for k in HUMAN_EVENT_DATA if k in e.data}
                if data:
                    item["data"] = data
                if e.text is not None:
                    item["t"] = clean(e.text)
                    item["agent"] = self._text_visible(viewer, e, obj)
                out.append({k: v for k, v in item.items() if v is not None})
                continue
            if e.text is not None:
                if self._text_visible(viewer, e, obj):
                    item["t"] = clean(e.text)
                elif e.actor_kind == "agent":
                    held[e.actor or "?"] = held.get(e.actor or "?", 0) + 1
                    continue
                else:
                    item["withheld"] = "needs_accept"
            out.append({k: v for k, v in item.items() if v is not None})
        for by, n in held.items():
            out.append({"withheld": "peer_agent_text", "by": by, "n": n, "url": self.url(obj.id)})
        return out

    # -- 相关性与计数 ----------------------------------------------------------------

    def _related(self, subject: str | None, me: str) -> bool:
        if not subject:
            return False
        if subject.startswith("T-"):
            t = self.tasks.get(subject)
            return bool(t) and me in (t.assignee, t.created_by, t.assigned_by, t.steward)
        b = self.blockers.get(subject)
        if not b:
            return False
        if me in (b.raised_by, b.helper):
            return True
        # agent 的点名只是提议（proposed）：主人确认（asked）之前，被点名的人的增量、fwd、收件箱里都没有它（plan 5.4）
        return me == b.needs and b.need_state == "asked"

    def _relevant_events(self, me: str, after: int) -> list[Event]:
        return [e for e in self.events if e.id > after and e.actor != me and e.type != "commit" and self._related(e.subject, me)]

    def new_count(self, actor: Actor) -> int:
        with self.lock:
            return len(self._relevant_events(actor.handle, self.cursors.get(actor.token_id or actor.handle, 0)))

    def _unforwarded(self, me: str, obj_id: str) -> list[Event]:
        """某个对象上他人 agent 写的、超出我 through_event_id 的文字（"待您转发"）。"""
        acc = self.acceptances.get((me, obj_id))
        through = acc.through_event_id if acc else 0
        return [
            e
            for e in self.events
            if e.subject == obj_id and e.text is not None and e.actor != me and e.actor_kind == "agent" and e.id > through
        ]

    def _fwd(self, me: str) -> list[dict[str, Any]]:
        """待您转发：与我有关的对象上，他人 agent 写的、超出我 through_event_id 的文字条数。"""
        rows: list[dict[str, Any]] = []
        objs: list[Task | Blocker] = [*self.tasks.values(), *self.blockers.values()]
        for obj in objs:
            if not (self._related(obj.id, me) or (me, obj.id) in self.acceptances):
                continue
            pending = self._unforwarded(me, obj.id)
            if pending:
                rows.append({"id": obj.id, "n": len(pending), "by": pending[-1].actor})
        return rows

    # -- 读 ----------------------------------------------------------------------

    def inbox(self, actor: Actor, limit: int = 10, advance: bool = True) -> dict[str, Any]:
        me = actor.handle
        limit = max(1, min(int(limit or 10), 20))
        with self.lock:
            mine = [t for t in self.tasks.values() if t.assignee == me]
            doing = [t for t in mine if t.status == "in_progress"]
            todo = [t for t in mine if t.status == "open" and t.assign_state == "accepted"]
            to_accept = [t for t in mine if t.status == "open" and t.assign_state == "pending"]
            help_me = [b for b in self.blockers.values() if b.status == "open" and b.needs == me and b.need_state == "asked" and b.helper is None]
            proposed = [
                b for b in self.blockers.values() if b.status == "open" and b.raised_by == me and b.need_state == "proposed"
            ]
            replies = [
                e
                for e in self.events
                if e.type in ("task.accepted", "task.declined", "task.done")
                and e.actor != me
                and e.subject in self.tasks
                and me in (self.tasks[e.subject].created_by, self.tasks[e.subject].assigned_by)
                and self.now() - e.at < timedelta(days=3)
            ]
            pool = [t for t in self.tasks.values() if t.label == "pool"]
            titled: list[Task | Blocker] = [*doing[:limit], *todo[:limit], *to_accept[:limit], *help_me[:limit]]
            key = actor.token_id or me
            new = len(self._relevant_events(me, self.cursors.get(key, 0)))
            if advance:
                self.cursors[key] = self._next_event_id - 1
            out = {
                "me": me,
                "doing": [t.id for t in doing[:limit]],
                "todo": [t.id for t in todo[:limit]],
                "to_accept": [
                    {"id": t.id, "by": t.assigned_by, "bk": t.assigned_by_kind, "client": t.assigned_by_client}
                    for t in to_accept[:limit]
                ],
                "help_me": [{"id": b.id, "by": b.raised_by} for b in help_me[:limit]],
                "proposed": [{"id": b.id, "h": b.needs, "client": b.raised_by_client} for b in proposed[:limit]],
                "fwd": self._fwd(me)[:limit],
                "replies": [{"id": e.subject, "ev": e.type.split(".")[-1], "by": e.actor} for e in replies[-limit:]],
                "pool": len(pool),
                "new": new,
                "titles": {o.id: self._title_env(o, me) for o in titled},
            }
            return out

    def list_tasks(
        self,
        actor: Actor,
        view: str = "mine",
        project: str | None = None,
        q: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        me = actor.handle
        limit = max(1, min(int(limit or 20), 50))
        try:
            offset = max(0, int(cursor or 0))
        except ValueError:
            raise DomainError("invalid", "cursor 无效，请用上一页返回的 next。") from None
        with self.lock:
            rows = list(self.tasks.values())
            if view == "pool":
                rows = [t for t in rows if t.label == "pool"]
            elif view == "mine":
                rows = [t for t in rows if (t.assignee == me or t.created_by == me) and t.status in ("open", "in_progress")]
            elif view == "doing":
                rows = [t for t in rows if t.status == "in_progress"]
            elif view == "done":
                rows = [t for t in rows if t.status == "done"]
            elif view != "all":
                raise DomainError("invalid", "view 只能是 pool、mine、doing、done、all 之一。")
            if project:
                rows = [t for t in rows if t.project == project]
            if q:
                ql = q.lower()
                rows = [t for t in rows if ql in t.title.lower() or ql == t.id.lower()]
            rows.sort(key=lambda t: (t.last_activity_at or t.created_at), reverse=True)
            page = rows[offset : offset + limit]
            out_rows = []
            for t in page:
                blk = [b.id for b in self.blockers.values() if b.task_id == t.id and b.status == "open"]
                r: dict[str, Any] = {"id": t.id, "t": self._title_env(t, me), "st": t.label}
                if t.assignee:
                    r["who"] = t.assignee
                if blk:
                    r["blk"] = blk
                r["upd"] = mdhm(t.last_activity_at or t.created_at)
                out_rows.append(r)
            nxt = str(offset + limit) if offset + limit < len(rows) else None
            return {"rows": out_rows, "next": nxt}

    def get_item(self, actor: Actor, raw_id: str, events: int = 5, *, for_human: bool = False) -> dict[str, Any]:
        """详情。agent 拿到的按"看见"闸门过滤；for_human=True 是网页详情页（只有人的会话能要）：

        - 正文、困难详情、tried 一律给（同一版清洗），本人要先看过才能决定接受或认领；
        - 动态是全部动态、全部文字，每条文字标 agent=本人的 agent 现在能不能读到；
        - 另给 page（表单要原样带回的 v、sha、seq、through）和 agent（本人的 agent 现在能看到什么）。
        """
        me = actor.handle
        if for_human and actor.kind != "human":
            raise DomainError("human_only", "网页详情只给本人看，agent 请用 get_item。")
        events = max(0, min(int(events if events is not None else 5), 10))
        with self.lock:
            obj = self._obj(raw_id)
            out: dict[str, Any] = {"id": obj.id, "t": self._title_env(obj, me)}
            if isinstance(obj, Task):
                out.update(
                    {
                        "kind": "task",
                        "st": obj.label,
                        "who": obj.assignee,
                        "by": obj.created_by,
                        "v": obj.content_version,
                    }
                )
                if obj.assign_state == "pending":
                    out["assign"] = {"seq": obj.assign_seq, "by": obj.assigned_by}
                    if for_human:  # "赵的 Claude Code 请您协作"：页面要知道是人还是哪个 agent 指派的
                        out["assign"].update(bk=obj.assigned_by_kind, client=obj.assigned_by_client)
                if obj.parent:
                    out["parent"] = obj.parent
                if obj.project:
                    out["project"] = obj.project
                if for_human or self.can_see_content(me, obj):
                    if obj.body:
                        out["content"] = self.envelope(obj.body, obj.created_by, obj.created_by_kind, obj.created_by_client, me)
                elif obj.body:
                    out["withheld"] = "needs_accept"
                blk = [b.id for b in self.blockers.values() if b.task_id == obj.id and b.status == "open"]
                if blk:
                    out["blk"] = blk
            else:
                out.update(
                    {
                        "kind": "blocker",
                        "st": obj.status,
                        "task": obj.task_id,
                        "need": obj.needs,
                        "need_state": obj.need_state,
                        "helper": obj.helper,
                        "v": obj.content_version,
                    }
                )
                if obj.task_closed:
                    out["task_closed"] = True
                if for_human or self.can_see_content(me, obj):
                    c: dict[str, Any] = {}
                    if obj.detail:
                        c["detail"] = self.envelope(obj.detail, obj.raised_by, obj.raised_by_kind, obj.raised_by_client, me)
                    if obj.tried:
                        c["tried"] = self.envelope(obj.tried, obj.raised_by, obj.raised_by_kind, obj.raised_by_client, me)
                    if c:
                        out["content"] = c
                elif obj.detail or obj.tried:
                    out["withheld"] = "needs_accept"
            out["ev"] = self._events_view(me, obj, events, for_human=for_human)
            out["url"] = self.url(obj.id)
            if for_human:
                out.update(self._human_extras(me, obj))
            return {k: v for k, v in out.items() if v is not None}

    def _human_extras(self, me: str, obj: Task | Blocker) -> dict[str, Any]:
        """网页详情页另给的两块：page（表单原样带回的值）和 agent（本人的 agent 现在能看到什么）。"""
        acc = self.acceptances.get((me, obj.id))
        has_text = bool(obj.body) if isinstance(obj, Task) else bool(obj.detail or obj.tried)
        if self.can_see_content(me, obj):
            content = "visible" if has_text else "none"
        else:
            content = "needs_accept" if has_text else "none"
        extra: dict[str, Any] = {
            "page": self.page_view(obj.id),
            "agent": {
                "content": content,
                "through": acc.through_event_id if acc else 0,
                "unforwarded": len(self._unforwarded(me, obj.id)),
            },
            "created": (obj.created_at).astimezone(TZ).isoformat(timespec="seconds"),
        }
        if isinstance(obj, Task) and obj.urgent:
            extra["urgent"] = True
        return extra

    def titles(self, viewer: str, ids: Iterable[str]) -> dict[str, dict[str, Any]]:
        """一批对象的标题信封（网页首页用：home 只放 ID，标题按同一个函数另取）。不存在的 ID 跳过。"""
        with self.lock:
            out: dict[str, dict[str, Any]] = {}
            for oid in ids:
                obj = self.tasks.get(oid) or self.blockers.get(oid)
                if obj is not None:
                    out[oid] = self._title_env(obj, viewer)
            return out

    def team_status(self, actor: Actor, project: str | None = None) -> dict[str, Any]:
        me = actor.handle
        with self.lock:
            tasks = [t for t in self.tasks.values() if not project or t.project == project]
            blockers = [b for b in self.blockers.values() if not project or b.project == project]
            task_ids = {t.id for t in tasks}
            others = []
            for m in sorted(self.members.values(), key=lambda m: m.handle):
                if m.handle == me or not m.active:
                    continue
                others.append(
                    {
                        "h": m.handle,
                        "doing": [t.id for t in tasks if t.assignee == m.handle and t.status == "in_progress"],
                        "blockers": [b.id for b in blockers if b.raised_by == m.handle and b.status == "open"],
                        # 精确归属到会话的：{client, s, task}，即"bob · Claude Code · 会话 1a6941c0 在做 T-53"
                        "sess": [r for r in self._session_rows(m.handle) if r["task"] in task_ids],
                    }
                )
            helpers = self._suggest(me, project=project, exclude=set())
            counts = {
                "pool": sum(1 for t in tasks if t.label == "pool"),
                "pending": sum(1 for t in tasks if t.label == "pending"),
                "todo": sum(1 for t in tasks if t.label == "todo"),
                "doing": sum(1 for t in tasks if t.label == "doing"),
                "blockers": sum(1 for b in blockers if b.status == "open"),
            }
            return {"others": others, "helpers": helpers, "counts": counts}

    def _task_sessions(self, t: Task) -> list[AgentSession]:
        """指向某个进行中任务的会话：没结束、current_task 是它、会话属于负责人。只有精确归属才会设置 current_task
        （Codex 的 _meta、Claude Code 的 PostToolUse 映射），所以成员级的认领这里是空的。"""
        if t.status != "in_progress" or not t.assignee:
            return []
        rows = [
            s
            for s in self.sessions.values()
            if s.current_task == t.id and s.ended_at is None and s.handle == t.assignee
        ]
        return sorted(rows, key=lambda s: (s.current_task_ev or 0, s.external_id))

    def _session_rows(self, handle: str) -> list[dict[str, Any]]:
        """某人的会话在做什么：[{client, s, task}]。只有 ID、枚举值和会话短标签，不给仓库、分支、时长（7.4）。"""
        rows: list[dict[str, Any]] = []
        for t in sorted(self.tasks.values(), key=lambda t: t.no):
            if t.assignee != handle:
                continue
            for s in self._task_sessions(t):
                rows.append({"client": s.client, "s": session_tag(s), "task": t.id})
        return rows

    def home(self, viewer: str) -> dict[str, Any]:
        """首页（7.1）的结构化数据：①待我处理 ②困难（按卡住时长）③大家在做什么 ④计数。

        ③ 每个进行中的任务一行 {h, id, client, sess[{client, s}], today}：没有会话指向时是成员级
        （"李 · Codex · 在做 T-52"）；有精确归属的会话时带上会话短标签（"李 · Claude Code · 会话 1a6941c0 在做 T-52"）。
        只放 ID、handle、枚举值，标题由页面按闸门另取。"""
        with self.lock:
            me = self._member(viewer).handle
            ib = self.inbox(Actor(me, "human", None, None, "web"), limit=10, advance=False)
            today = self.now().astimezone(TZ).date()
            doing = []
            for t in sorted(self.tasks.values(), key=lambda t: (t.last_activity_at or t.created_at), reverse=True):
                if t.status != "in_progress":
                    continue
                row: dict[str, Any] = {"h": t.assignee, "id": t.id, "client": t.claimed_client}
                sess = [{"client": s.client, "s": session_tag(s)} for s in self._task_sessions(t)]
                if sess:
                    row["sess"] = sess
                last = t.last_activity_at or t.created_at
                row["today"] = last.astimezone(TZ).date() == today
                doing.append(row)
            open_b = sorted((b for b in self.blockers.values() if b.status == "open"), key=lambda b: b.created_at)
            return {
                "me": me,
                "mine": {k: ib[k] for k in ("to_accept", "help_me", "proposed", "fwd", "replies")},
                "blockers": [{"id": b.id, "by": b.raised_by, "task": b.task_id, "since": mdhm(b.created_at)} for b in open_b],
                "doing": doing,
                "counts": self.team_status(Actor(me, "human", None, None, "web"))["counts"],
            }

    def _suggest(self, me: str, project: str | None, exclude: set[str], repo: str | None = None) -> list[dict[str, str]]:
        """谁能帮忙：解决或帮过困难的、在同一仓库有会话的、同项目在做事的，取前 3 个，附理由（枚举）。"""
        scored: list[tuple[int, str, str]] = []
        for m in self.members.values():
            if m.handle == me or not m.active or m.handle in exclude:
                continue
            if any(b.helper == m.handle or (b.status == "resolved" and b.raised_by == m.handle) for b in self.blockers.values()):
                scored.append((0, m.handle, "solved_before"))
            elif repo and any(s.handle == m.handle and s.repo == repo for s in self.sessions.values()):
                scored.append((1, m.handle, "active_here"))
            elif project and any(t.assignee == m.handle and t.project == project for t in self.tasks.values()):
                scored.append((2, m.handle, "same_project"))
            else:
                scored.append((3, m.handle, "member"))
        scored.sort()
        return [{"h": h, "why": why} for _, h, why in scored[:3]]

    # -- 写：任务 ----------------------------------------------------------------

    def _dedupe(self, actor: Actor, tool: str, args: dict[str, Any]) -> tuple[tuple[str, str, str], dict[str, Any] | None]:
        """create_task / report_blocker / comment 按 (member, tool, sha256(规范化参数)) 去重 10 分钟。"""
        norm = json.dumps({k: v for k, v in args.items() if v not in (None, "", False)}, sort_keys=True, ensure_ascii=False)
        key = (actor.handle, tool, sha256(norm))
        hit = self.dedupe.get(key)
        if hit and hit[0] > self.now():
            return key, hit[1]
        return key, None

    def create_task(
        self,
        actor: Actor,
        title: str,
        body: str | None = None,
        assignee: str | None = None,
        project: str | None = None,
        urgent: bool = False,
        parent: str | None = None,
    ) -> dict[str, Any]:
        with self.lock:
            dkey, cached = self._dedupe(actor, "create_task", {"title": title, "body": body, "assignee": assignee, "project": project, "urgent": urgent, "parent": parent})
            if cached:
                return cached
            title_c = self._title(actor, title)
            body_c = self._text("body", body)
            target = self._member(assignee, what="成员").handle if assignee else None
            if project and project not in self.projects:
                raise DomainError("invalid", f"没有叫 {project} 的项目。可选的有：{'、'.join(sorted(self.projects))}。")
            parent_id = None
            if parent:
                p = self._task(parent)
                if p.parent:
                    raise DomainError("invalid", f"{p.id} 本身是子任务；上级任务只允许一层。")
                parent_id = p.id
            now = self.now()
            no = self.next_task_no
            self.next_task_no += 1
            t = Task(
                id=f"T-{no}",
                no=no,
                title=title_c or "",
                body=body_c,
                created_by=actor.handle,
                created_by_kind=actor.kind,
                created_by_client=actor.client,
                created_via=actor.via,
                created_at=now,
                steward=actor.handle,
                content_sha256=sha256(body_c),
                urgent=bool(urgent),
                project=project,
                parent=parent_id,
                last_activity_at=now,
            )
            self.tasks[t.id] = t
            self._emit("task.created", t.id, actor)
            if target == actor.handle:
                # 指派自己：直接 accepted
                t.assignee, t.assign_state, t.assign_seq = target, "accepted", 1
                t.assigned_by, t.assigned_by_kind, t.assigned_by_client = actor.handle, actor.kind, actor.client
                self.acceptances[(actor.handle, t.id)] = Acceptance(
                    actor.handle, t.id, t.content_version, t.content_sha256, self._next_event_id - 1, actor.via, now
                )
            elif target:
                # 指派他人：pending，并通知对方（作者是 agent 时模板里不放任何自由文本）
                t.assignee, t.assign_state, t.assign_seq = target, "pending", 1
                t.assigned_by, t.assigned_by_kind, t.assigned_by_client = actor.handle, actor.kind, actor.client
                self._emit("task.assigned", t.id, actor, to=target, seq=t.assign_seq)
                if actor.kind == "agent":
                    text = f"{actor.handle} 的 {client_name(actor.client)} 请您协作（{t.id}）"
                else:
                    short = re.sub(r"\d{4,}", "", t.title)[:16]
                    text = f"{actor.handle} 请您协作：{short}（{t.id}）"
                self._notify(target, "task_assigned", t.id, text, actor, f"assigned:{t.id}:{t.assign_seq}")
            self._check_task(t)
            result = {"id": t.id, "url": self.url(t.id), "st": t.label}
            self.dedupe[dkey] = (now + timedelta(minutes=10), result)
            return result

    def _taken_error(self, t: Task, actor: Actor | None = None) -> DomainError:
        who = t.assignee or "?"
        at = hm(t.claimed_at or t.started_at or t.last_activity_at)
        how = "可以在「待认领」里换一个。" if actor is not None and actor.kind == "human" else "可以用 list_tasks(view=pool) 换一个待认领任务。"
        return DomainError(
            "taken",
            f"{t.id} 已被 {who} 于 {at} 认领。{how}",
            id=t.id,
            by=who,
            at=at,
        )

    def claim_task(self, actor: Actor, raw_id: str) -> dict[str, Any]:
        """agent 的认领 / 开始。幂等：本人已在做的任务再认领一次直接返回成功。"""
        me = actor.handle
        with self.lock:
            t = self._task(raw_id)
            if t.status in ("done", "canceled"):
                word = "已完成" if t.status == "done" else "已取消"
                raise DomainError("invalid", f"{t.id} {word}，不能再认领。需要重新打开时请用户在手机上操作。", id=t.id, st=t.label)
            if t.assignee == me:
                if t.status == "in_progress":
                    return self._claim_summary(t, me)  # 幂等
                if t.assign_state == "pending":
                    raise DomainError(
                        "needs_accept",
                        f"{t.id} 是 {t.assigned_by} 指派给您的，需要您本人在手机上打开 {t.id} 点「接受」后才能开始。"
                        "请转告用户；接受后再调用 claim_task。",
                        id=t.id,
                        by=t.assigned_by,
                    )
                return self._start(actor, t)
            if t.assignee is not None:
                raise self._taken_error(t)
            # 待认领
            if t.created_by != me:
                self._notify(
                    me,
                    "agent_asks",
                    t.id,
                    f"您的 {client_name(actor.client)} 想开始 {t.id}，点这里认领",
                    None,  # 这条就是发给本人的
                    f"agent_asks:{t.id}",
                )
                self._audit("claim_task", actor, "needs_human", id=t.id)
                raise DomainError(
                    "needs_human",
                    f"{t.id} 是 {t.created_by} 发布的，认领就是承诺，需要您本人决定。已发到您的微信，请在手机上点「认领」；"
                    "认领后再调用 claim_task 开始。",
                    id=t.id,
                    by=t.created_by,
                )
            # 条件更新：WHERE status='open' AND assignee IS NULL（锁内执行，0 行就是 taken）
            if not self._cas_claim(t, actor):
                raise self._taken_error(t)
            self._emit("task.claimed", t.id, actor)
            return self._start(actor, t)

    def _cas_claim(self, t: Task, actor: Actor) -> bool:
        if not (t.status == "open" and t.assignee is None):
            return False
        now = self.now()
        t.assignee, t.assign_state = actor.handle, "accepted"
        t.assign_seq += 1
        t.assigned_by, t.assigned_by_kind, t.assigned_by_client = actor.handle, actor.kind, actor.client
        t.claimed_client, t.claimed_at = actor.client, now
        acc = self.acceptances.get((actor.handle, t.id))
        if acc is None or acc.content_version != t.content_version:
            self.acceptances[(actor.handle, t.id)] = Acceptance(
                actor.handle, t.id, t.content_version, t.content_sha256, acc.through_event_id if acc else 0, actor.via, now
            )
        self._touch(t)
        self._check_task(t)
        return True

    def _start(self, actor: Actor, t: Task) -> dict[str, Any]:
        if t.assign_state != "accepted" or not self.can_see_content(actor.handle, t):
            raise DomainError(
                "needs_accept",
                f"{t.id} 的内容有更新，需要您本人在手机上重新「接受」后才能开始。",
                id=t.id,
            )
        now = self.now()
        t.status = "in_progress"
        t.started_at = t.started_at or now
        t.claimed_client = actor.client or t.claimed_client
        t.claimed_at = t.claimed_at or now
        self._touch(t)
        ev = self._emit("task.started", t.id, actor)
        s = self._owned_session(actor)
        if s is not None:
            s.current_task, s.current_task_ev = t.id, ev.id
        self._check_task(t)
        return self._claim_summary(t, actor.handle)

    def _claim_summary(self, t: Task, me: str) -> dict[str, Any]:
        out: dict[str, Any] = {"id": t.id, "st": t.label, "t": self._title_env(t, me)}
        if t.body and self.can_see_content(me, t):
            out["next"] = "get_item"
        return out

    def update_task(
        self,
        actor: Actor,
        raw_id: str,
        note: str | None = None,
        status: str | None = None,
        title: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        me = actor.handle
        with self.lock:
            t = self._task(raw_id)
            if note is None and status is None and title is None and body is None:
                raise DomainError("invalid", "至少要给 note、status、title、body 中的一项。")
            note_c = self._text("note", note)
            is_assignee = t.assignee == me and t.assign_state == "accepted"
            # 编辑（只限本人或本人 agent 发布、且还没有他人 acceptance 的）
            if title is not None or body is not None:
                if t.created_by != me:
                    raise DomainError("not_allowed", f"{t.id} 是 {t.created_by} 发布的，只有发布人可以编辑。可以用 comment 提建议。", id=t.id)
                others = self._content_acceptors(t.id, me)
                if actor.kind == "agent" and others:
                    raise DomainError(
                        "not_allowed",
                        f"{t.id} 已被 {others[0].handle} 接受，agent 不能再改标题和正文；需要改的话请用户在手机上编辑。",
                        id=t.id,
                    )
                if t.status in ("done", "canceled"):
                    raise DomainError("invalid", f"{t.id} 已结束，不能编辑。", id=t.id)
                changed = False
                if title is not None:
                    tc = self._title(actor, title)
                    if tc != t.title:
                        t.title, changed = tc or t.title, True
                if body is not None:
                    bc = self._text("body", body)
                    if bc != t.body:
                        t.body, changed = bc, True
                if changed:
                    t.content_version += 1
                    t.content_sha256 = sha256(t.body)
                    acc = self.acceptances.get((me, t.id))
                    if acc:  # 作者本人的 acceptance 跟着新版本走
                        acc.content_version, acc.content_sha256 = t.content_version, t.content_sha256
                    self._emit("task.edited", t.id, actor, v=t.content_version)
            if status is not None and status != t.status:
                if status == "done":
                    if not is_assignee:
                        raise self._not_owner(t, "完成", actor)
                    if t.status not in ("open", "in_progress"):
                        raise DomainError("invalid", f"{t.id} 当前是 {t.label}，不能标记完成。", id=t.id)
                    if actor.kind == "agent" and not note_c:
                        raise DomainError("invalid", "标记完成要附一句说明（note）：做了什么，加上 PR 链接。", id=t.id)
                    t.status, t.done_at = "done", self.now()
                    self._emit("task.done", t.id, actor, text=note_c)
                    note_c = None
                    if t.assigned_by and t.assigned_by != me:
                        self._notify(t.assigned_by, "task_reply", t.id, f"您请 {me} 做的 {t.id} 已完成", actor, f"done:{t.id}")
                    elif t.created_by != me:
                        self._notify(t.created_by, "task_reply", t.id, f"您发布的 {t.id} 已由 {me} 完成", actor, f"done:{t.id}")
                    self._on_terminal(t)
                elif status == "open":
                    if not (is_assignee and t.status == "in_progress"):
                        raise self._not_owner(t, "取消认领", actor)
                    if actor.kind == "agent" and not note_c:
                        raise DomainError("invalid", "取消认领要写交接说明（note）：做到哪了、下一步是什么。", id=t.id)
                    t.status = "open"
                    self._emit("task.released", t.id, actor, text=note_c, reason="release")
                    note_c = None
                    self._clear_current(t.id)
                elif status == "in_progress":
                    if not is_assignee or t.status != "open":
                        raise self._not_owner(t, "开始", actor)
                    self._start(actor, t)
                elif status == "canceled":
                    if t.created_by != me:
                        raise DomainError("not_allowed", f"{t.id} 是 {t.created_by} 发布的，只有发布人可以取消。", id=t.id)
                    others = self._content_acceptors(t.id, me)
                    if actor.kind == "agent" and others:
                        raise DomainError("not_allowed", f"{t.id} 已被 {others[0].handle} 接受过，agent 不能取消；请用户在手机上操作。", id=t.id)
                    if not note_c:
                        raise DomainError("invalid", "取消任务要写原因（note）。", id=t.id)
                    t.status = "canceled"
                    self._emit("task.canceled", t.id, actor, text=note_c)
                    note_c = None
                    self._on_terminal(t)
                else:
                    raise DomainError("invalid", "status 只能是 open、in_progress、done、canceled 之一。")
            if note_c:
                if me not in (t.assignee, t.created_by):
                    raise DomainError("not_allowed", f"{t.id} 不是您负责或发布的，进度请用 comment 写。", id=t.id)
                self._emit("note", t.id, actor, text=note_c)
            self._touch(t)
            self._check_task(t)
            new = len(self._relevant_events(me, self.cursors.get(actor.token_id or me, 0)))
            return {"id": t.id, "st": t.label, "new": new}

    def _not_owner(self, t: Task, what: str, actor: Actor | None = None) -> DomainError:
        human = actor is not None and actor.kind == "human"
        if t.assign_state == "pending":
            return DomainError("needs_accept", f"{t.id} 还在等 {t.assignee} 本人接受，接受前不能{what}。", id=t.id)
        if t.assignee is None:
            how = "先点「认领」" if human else "先用 claim_task 认领"
            return DomainError("invalid", f"{t.id} 还没人认领，{how}。", id=t.id)
        who = "您" if human else "您的 agent"
        return DomainError("not_allowed", f"{t.id} 的负责人是 {t.assignee}，{who}不能{what}它；当前状态 {t.label}。", id=t.id, who=t.assignee)

    def _clear_current(self, tid: str) -> None:
        for s in self.sessions.values():
            if s.current_task == tid:
                s.current_task = None

    def _on_terminal(self, t: Task) -> None:
        """I7：进入终态时 pending→none、挂着的 open 困难标 task_closed、清 current_task。"""
        if t.assign_state == "pending":
            t.assignee, t.assign_state = None, "none"
        for b in self.blockers.values():
            if b.task_id == t.id and b.status == "open":
                b.task_closed = True
        self._clear_current(t.id)

    # -- 写：困难与评论 ----------------------------------------------------------------

    def report_blocker(
        self,
        actor: Actor,
        title: str,
        detail: str | None = None,
        tried: str | None = None,
        task: str | None = None,
        need: str | None = None,
    ) -> dict[str, Any]:
        with self.lock:
            dkey, cached = self._dedupe(actor, "report_blocker", {"title": title, "detail": detail, "tried": tried, "task": task, "need": need})
            if cached:
                return cached
            title_c = self._title(actor, title)
            detail_c = self._text("detail", detail)
            tried_c = self._text("tried", tried)
            t = self._task(task) if task else None
            needs = self._member(need).handle if need else None
            if needs == actor.handle:
                raise DomainError("invalid", "need 填的是您自己；请填要请谁帮忙，或者留空。")
            now = self.now()
            no = self.next_blocker_no
            self.next_blocker_no += 1
            b = Blocker(
                id=f"B-{no}",
                no=no,
                title=title_c or "",
                detail=detail_c,
                tried=tried_c,
                raised_by=actor.handle,
                raised_by_kind=actor.kind,
                raised_by_client=actor.client,
                created_at=now,
                task_id=t.id if t else None,
                project=t.project if t else None,
                needs=needs,
                content_sha256=sha256((detail_c or "") + "\n" + (tried_c or "")),
                last_activity_at=now,
            )
            if needs:
                # agent 点名只是提议，进主人的"待我处理"；人点名直接 asked 并通知
                b.need_state = "asked" if actor.kind == "human" else "proposed"
            self.blockers[b.id] = b
            self._emit("blocker.raised", b.id, actor, need=needs, need_state=b.need_state)
            if b.need_state == "asked":
                self._notify(needs, "blocker_needs_you", b.id, f"{actor.handle} 请您帮忙看 {b.id}", actor, f"asked:{b.id}")
            if t:
                self._touch(t)
            s = self._owned_session(actor)
            repo = s.repo if s else None
            result = {
                "id": b.id,
                "st": b.status,
                "need_state": b.need_state,
                "suggest": self._suggest(actor.handle, project=b.project, exclude=set(), repo=repo),
            }
            self.dedupe[dkey] = (now + timedelta(minutes=10), result)
            return result

    def comment(self, actor: Actor, target: str, body: str, resolve: bool = False) -> dict[str, Any]:
        with self.lock:
            dkey, cached = self._dedupe(actor, "comment", {"target": target, "body": body, "resolve": resolve})
            if cached:
                return cached
            obj = self._obj(target)
            body_c = self._text("comment", body, required=True)
            if resolve:
                if not isinstance(obj, Blocker):
                    raise DomainError("invalid", "resolve 只用于困难（B-xx）；任务完成请用 update_task(status=done)。")
                if obj.status != "open":
                    raise DomainError("invalid", f"{obj.id} 已经解决了。", id=obj.id)
                allowed = obj.raised_by == actor.handle if actor.kind == "agent" else actor.handle in (obj.raised_by, obj.helper)
                if not allowed:
                    raise DomainError("not_allowed", f"{obj.id} 是 {obj.raised_by} 报告的，您的 agent 只能标记自己报告的困难已解决。", id=obj.id)
                obj.status, obj.resolved_at = "resolved", self.now()
                ev = self._emit("blocker.resolved", obj.id, actor, text=body_c)
                self._notify(obj.needs if obj.need_state == "asked" else None, "task_reply", obj.id, f"{obj.id} 已解决", actor, f"resolved:{obj.id}")
            else:
                ev = self._emit("comment", obj.id, actor, text=body_c)
            self._touch(obj)
            result = {"id": ev.id}
            self.dedupe[dkey] = (self.now() + timedelta(minutes=10), result)
            return result

    # -- 人的动作（只认手机微信 H5；M0 由 DEV ONLY 端点模拟） ---------------------------

    def _require_human(self, actor: Actor) -> None:
        if actor.kind != "human":
            raise DomainError("human_only", "这个操作只能由本人在手机微信里完成，agent 和命令行都不行。")

    @staticmethod
    def _need_page_fields(**fields: Any) -> None:
        """人类动作必须带上页面渲染时看到的值（H3）：版本 v、sha（任务接受还有 seq），以及 through
        （页面渲染时最大的动态编号）。缺了就是请求不合法（400），不是冲突。

        through 必填：缺省时若取"本次动作的事件 ID"，页面渲染之后、点按钮之前对方 agent 写的评论就会被
        当成"已看到"放给本人的 agent（复审新问题 1）。"""
        missing = [n for n, x in fields.items() if x is None]
        if missing:
            raise DomainError(
                "invalid",
                f"缺少 {'、'.join(missing)}：要带上页面渲染时看到的版本和最大的动态编号（through），"
                "内容被改过时才能发现，页面之后才出现的动态也不会算作您已看过。",
            )

    def _check_through(self, through: Any) -> int:
        """through_event_id：页面渲染时的最大事件 ID。必填，不能超过当前最大事件 ID（不能"看见"还没发生的动态）。
        接受、认领、帮忙、转发共用。"""
        if through is None:
            raise DomainError("invalid", "缺少 through：要带上页面渲染时最大的动态编号。")
        if not isinstance(through, int) or isinstance(through, bool) or through < 0:
            raise DomainError("invalid", "through 必须是非负整数。")
        latest = self.latest_event_id()
        if through > latest:
            raise DomainError("invalid", f"through={through} 超过了当前最大的动态编号 {latest}。", latest=latest)
        return through

    def _version_conflict(self, obj: Task | Blocker, v: int, sha: str, seq: int | None = None) -> None:
        stale = v != obj.content_version or sha != obj.content_sha256
        if isinstance(obj, Task) and seq is not None and seq != obj.assign_seq:
            stale = True
        if stale:
            raise DomainError(
                "conflict",
                "内容刚被修改，请重新查看。",
                id=obj.id,
                v=obj.content_version,
                seq=obj.assign_seq if isinstance(obj, Task) else None,
            )

    def page_view(self, raw_id: str) -> dict[str, Any]:
        """DEV ONLY：模拟手机详情页渲染时表单里带的值。

        v、sha（任务还有 seq）是页面上看到的版本；through 是页面渲染时这个对象最大的动态编号。
        接受、认领、帮忙、转发都必须原样带回 through：页面渲染之后才出现的动态（比如对方 agent
        刚写的评论）编号比它大，不会算作本人已看到，也就不会放给本人的 agent。"""
        with self.lock:
            obj = self._obj(raw_id)
            out: dict[str, Any] = {
                "id": obj.id,
                "v": obj.content_version,
                "sha": obj.content_sha256,
                "through": max((e.id for e in self.events if e.subject == obj.id), default=0),
            }
            if isinstance(obj, Task):
                out["seq"] = obj.assign_seq
            return out

    def human_accept(
        self,
        actor: Actor,
        raw_id: str,
        *,
        v: int | None,
        sha: str | None,
        seq: int | None,
        through: int | None,
    ) -> dict[str, Any]:
        """人在手机上点「接受」：v、sha、seq、through 必填；版本与当前不一致返回 409（plan 5.3、H3），
        through 超过当前最大事件 ID 返回 400。"""
        self._require_human(actor)
        self._need_page_fields(v=v, sha=sha, seq=seq, through=through)
        with self.lock:
            t = self._task(raw_id)
            through_c = self._check_through(through)
            if t.assignee != actor.handle or t.assign_state != "pending" or t.status not in ("open", "in_progress"):
                raise DomainError("conflict", f"{t.id} 当前不是待您接受的状态（{t.label}）。", id=t.id)
            self._version_conflict(t, v, sha, seq)  # type: ignore[arg-type]
            self._emit("task.accepted", t.id, actor, v=t.content_version, seq=t.assign_seq)
            t.assign_state = "accepted"
            self._write_acceptance(actor, t, through_c)
            self._touch(t)
            self._check_task(t)
            if t.assigned_by:
                self._notify(t.assigned_by, "task_reply", t.id, f"{actor.handle} 接受了 {t.id}", actor, f"accepted:{t.id}:{t.assign_seq}")
            return {"id": t.id, "st": t.label, "v": t.content_version}

    def human_claim(
        self, actor: Actor, raw_id: str, *, v: int | None, sha: str | None, through: int | None
    ) -> dict[str, Any]:
        """人在手机上点「认领」：同时完成认领和接受当前版本。v、sha、through 必填，版本不一致返回 409。
        之后任务是"待开始"，由本人或其 agent 开始。"""
        self._require_human(actor)
        self._need_page_fields(v=v, sha=sha, through=through)
        with self.lock:
            t = self._task(raw_id)
            through_c = self._check_through(through)
            self._version_conflict(t, v, sha)  # type: ignore[arg-type]
            if not self._cas_claim(t, actor):
                raise self._taken_error(t, actor)
            self._emit("task.claimed", t.id, actor)
            self._write_acceptance(actor, t, through_c)
            self._check_task(t)
            return {"id": t.id, "st": t.label, "v": t.content_version}

    def human_forward(self, actor: Actor, raw_id: str, *, through: int | None) -> dict[str, Any]:
        """「转发给我的 agent」：只把"已看到的动态位置"推进到页面渲染时的最大事件 ID。

        through 必填，不能超过当前最大事件 ID；只增不减。绝不新建或升级正文的 acceptance：
        没接受过正文的，转发之后 agent 拿到的仍是 withheld。
        """
        self._require_human(actor)
        with self.lock:
            obj = self._obj(raw_id)
            through_c = self._check_through(through)
            key = (actor.handle, obj.id)
            prev = self.acceptances.get(key)
            if prev is None:
                self.acceptances[key] = Acceptance(actor.handle, obj.id, None, None, through_c, actor.via, self.now())
            else:
                prev.through_event_id = max(prev.through_event_id, through_c)
            self._emit("acceptance.forwarded", obj.id, actor, through=through_c)
            return {"id": obj.id, "through": self.acceptances[key].through_event_id}

    def human_help(
        self, actor: Actor, raw_id: str, *, v: int | None, sha: str | None, through: int | None
    ) -> dict[str, Any]:
        """人认领困难（帮忙）：WHERE status='open' AND helper IS NULL；同时写 acceptance。
        v、sha、through 必填，版本不一致返回 409。"""
        self._require_human(actor)
        self._need_page_fields(v=v, sha=sha, through=through)
        with self.lock:
            b = self._blocker(raw_id)
            through_c = self._check_through(through)
            self._version_conflict(b, v, sha)  # type: ignore[arg-type]
            if b.status != "open" or b.helper is not None:
                raise DomainError("taken", f"{b.id} 已经有 {b.helper} 在帮忙了。", id=b.id, by=b.helper)
            b.helper = actor.handle
            self._emit("blocker.helped", b.id, actor)
            self._write_acceptance(actor, b, through_c)
            self._notify(b.raised_by, "task_reply", b.id, f"{actor.handle} 来帮忙看 {b.id} 了", actor, f"helped:{b.id}")
            self._touch(b)
            return {"id": b.id, "helper": b.helper}

    def human_decline(self, actor: Actor, raw_id: str, *, seq: int | None, reason: str | None) -> dict[str, Any]:
        """被指派人在手机上点「拒绝」（plan 5.3）：seq 必填（I4：WHERE assign_seq=:seq），原因必填。

        负责人改回 steward（发布人），状态 accepted（"待开始"）；steward 已停用时退回待认领。通知指派人「li 没接 T-52」。
        原因按评论类文字处理（清洗、2000 字、扫描），对指派人的 agent 来说和评论一样要转发后才给。"""
        self._require_human(actor)
        self._need_page_fields(seq=seq)
        if not isinstance(reason, str) or not reason.strip():
            raise DomainError("invalid", "拒绝要写一句原因，对方好另做安排。")
        with self.lock:
            t = self._task(raw_id)
            reason_c = self._text("comment", reason, required=True)
            me = actor.handle
            if t.assignee != me or t.assign_state != "pending" or t.status not in ("open", "in_progress"):
                raise DomainError("conflict", f"{t.id} 当前不是待您接受的状态（{t.label}）。", id=t.id)
            if not isinstance(seq, int) or isinstance(seq, bool) or seq != t.assign_seq:
                raise DomainError("conflict", "内容刚被修改，请重新查看。", id=t.id, v=t.content_version, seq=t.assign_seq)
            notify_to = t.assigned_by or t.steward
            back = self.members.get(t.steward)
            if back is not None and back.active and back.handle != me:
                t.assignee, t.assign_state = back.handle, "accepted"
                t.assigned_by, t.assigned_by_kind, t.assigned_by_client = back.handle, "human", None
            else:
                t.assignee, t.assign_state = None, "none"
                t.assigned_by, t.assigned_by_kind, t.assigned_by_client = None, None, None
            self._emit("task.declined", t.id, actor, text=reason_c, to=t.assignee, seq=seq)
            self._notify(notify_to, "task_reply", t.id, f"{me} 没接 {t.id}", actor, f"declined:{t.id}:{seq}")
            self._touch(t)
            self._check_task(t)
            return {"id": t.id, "st": t.label, "who": t.assignee}

    def human_release(self, actor: Actor, raw_id: str, *, note: str | None = None, to_pool: bool = False) -> dict[str, Any]:
        """负责人在手机上点「取消认领」（plan 5.2）。

        - 不放回待认领：和 agent 的取消认领同一条规则（update_task(status=open)），只限进行中，负责人不变；
        - 放回待认领（to_pool）：进行中或待开始都可以，负责人清空、assign_seq 加 1（旧表单作废），回到待认领。"""
        self._require_human(actor)
        me = actor.handle
        with self.lock:
            t = self._task(raw_id)
            mine = t.assignee == me and t.assign_state == "accepted" and t.status in ("open", "in_progress")
            if not mine:
                if t.assignee == me and t.assign_state == "pending":
                    raise DomainError("needs_accept", f"{t.id} 还在等您接受；不想做请点「拒绝」。", id=t.id)
                raise DomainError("not_allowed", f"{t.id} 不在您手里（{t.label}），不能取消认领。", id=t.id, who=t.assignee)
            if not to_pool:
                if t.status == "open":
                    raise DomainError("invalid", f"{t.id} 还没开始；不做了的话，请选「放回待认领」。", id=t.id)
                return self.update_task(actor, t.id, status="open", note=note)
            note_c = self._text("note", note)
            t.status = "open"
            t.assignee, t.assign_state = None, "none"
            t.assign_seq += 1
            t.assigned_by, t.assigned_by_kind, t.assigned_by_client = None, None, None
            t.claimed_client, t.claimed_at = None, None
            self._emit("task.released", t.id, actor, text=note_c, reason="to_pool")
            self._clear_current(t.id)
            self._touch(t)
            self._check_task(t)
            return {"id": t.id, "st": t.label}

    def human_ask(self, actor: Actor, raw_id: str) -> dict[str, Any]:
        """主人确认 agent 提议的点名：proposed → asked，并通知被点名的人。"""
        self._require_human(actor)
        with self.lock:
            b = self._blocker(raw_id)
            if b.raised_by != actor.handle or b.need_state != "proposed":
                raise DomainError("conflict", f"{b.id} 当前没有待您确认的点名。", id=b.id)
            b.need_state = "asked"
            self._emit("blocker.asked", b.id, actor, need=b.needs)
            self._notify(b.needs, "blocker_needs_you", b.id, f"{actor.handle} 请您帮忙看 {b.id}", actor, f"asked:{b.id}")
            return {"id": b.id, "need_state": b.need_state}

    def _write_acceptance(self, actor: Actor, obj: Task | Blocker, through: int) -> None:
        """写入"接受了正文"的 acceptance：绑定对象当前的 content_version 和 sha（调用方已在锁内核对过版本）。"""
        prev = self.acceptances.get((actor.handle, obj.id))
        self.acceptances[(actor.handle, obj.id)] = Acceptance(
            actor.handle,
            obj.id,
            obj.content_version,
            obj.content_sha256,
            max(through, prev.through_event_id if prev else 0),
            actor.via,
            self.now(),
        )

    # -- hooks ------------------------------------------------------------------

    @staticmethod
    def norm_client(c: str | None) -> str | None:
        c = (c or "").strip().lower()
        return {"claude": "claude_code", "claude_code": "claude_code", "codex": "codex", "cli": "cli"}.get(c)

    def _upsert_session(self, actor: Actor, client: str, sid: str, *, reopen: bool = False, **fields: Any) -> AgentSession | None:
        """登记或更新会话。值为 None 的字段不覆盖；reopen=True 时清掉 ended_at（resume 之后又开始了）。"""
        key = (client, sid)
        s = self.sessions.get(key)
        now = self.now()
        if s is None:
            s = AgentSession(client=client, external_id=sid, handle=actor.handle, token_id=actor.token_id, started_at=now)
            self.sessions[key] = s
        elif s.token_id != actor.token_id:
            # 防冒用：会话的 token_id 必须等于当前 token，否则忽略并写审计（plan 6.5）
            self._audit("session.token_mismatch", actor, "ignored", client=client)
            return None
        for k, v in fields.items():
            if v is not None:
                setattr(s, k, v)
        if reopen:
            s.ended_at, s.end_reason = None, None
        s.last_seen_at = now
        return s

    def resolve_session(
        self,
        handle: str,
        client: str | None,
        token_id: str | None,
        raw_sid: str | None,
        *,
        source: str,
        via: str = "mcp",
    ) -> AgentSession | None:
        """统一的会话归属（plan 6.5、H7）：请求里自称的会话必须存在、未结束、token_id 与当前 token 相同、
        client 与 token 的 client 相同，才算精确归属；否则返回 None（降为成员级）并写审计。

        source 只进审计：header（X-Teamflow-Session）、codex_meta（x-codex-turn-metadata.session_id）、
        tool_map（Claude Code 的 PostToolUse 映射，D40）。
        """
        sid = ident_or_hash(str(raw_sid)) if raw_sid else None
        if not sid:
            return None
        with self.lock:
            s = self.sessions.get((client or "", sid))
            if s is None:
                reason = "unknown"
            elif s.ended_at is not None:
                reason = "ended"
            elif s.token_id is None or s.token_id != token_id:
                reason = "token_mismatch"
            elif s.client != client:
                reason = "client_mismatch"
            elif s.handle != handle:
                reason = "handle_mismatch"
            else:
                return s
            who = Actor(handle, "agent", client, token_id, via)
            self._audit("session.resolve", who, "member", reason=reason, source=source, client=client)
            return None

    def _owned_session(self, actor: Actor) -> AgentSession | None:
        """写入时再核对一次：actor 带的精确归属会话仍属于这个 token（会话可能在请求途中结束或被换手）。"""
        if not actor.session or actor.attribution != "exact":
            return None
        s = self.sessions.get((actor.client or "", actor.session))
        if s and s.ended_at is None and s.token_id == actor.token_id and s.client == actor.client and s.handle == actor.handle:
            return s
        return None

    # -- Claude Code 的 PostToolUse 映射（D40） -------------------------------------------
    #
    # Claude Code 的 MCP 调用没有可信的会话头（S3），只到成员级。PostToolUse hook 在本地 spool 写
    # {"type":"tool_map","session_id","tool_use_id","tool"}，由 Stop 拉起的 flush 经 hooks/batch 上报；
    # tool_use_id 等于这次调用 _meta["claudecode/toolUseId"]。服务端：
    # - 映射按 (token_id, tool_use_id) 存，只能补"同一 token_id 的"事件：A 的 token 碰不到 B 的事件；
    # - 映射指向的会话要过 resolve_session（同一 token、client=claude_code 登记、未结束），否则整条忽略并写审计；
    # - 只把成员级的事件补成 exact（actor_session_id=该会话），已经 exact 的不动；幂等；
    # - 同一个 tool_use_id 先后指向两个会话时，以先到的为准，后到的忽略并写审计；
    # - 映射先于调用到达时先存着（24 小时），调用到达时直接判 exact；
    # - 认领/开始类事件、且任务仍由该成员进行中时，设置该会话的 current_task（不覆盖更新的指向）。

    def _purge_tool_maps(self) -> None:
        now = self.now()
        for k, m in list(self.tool_maps.items()):
            if m.expires_at <= now:
                del self.tool_maps[k]
        cutoff = now - TOOL_MAP_TTL
        for k, evs in list(self.call_events.items()):
            if not evs or evs[-1].at < cutoff:
                del self.call_events[k]

    def _live_tool_map(self, token_id: str | None, tuid: str | None) -> ToolMap | None:
        if not token_id or not tuid:
            return None
        m = self.tool_maps.get((token_id, tuid))
        if m is None or m.expires_at <= self.now():
            return None
        return m

    def _claude_session_ok(self, s: AgentSession | None, token_id: str | None, handle: str | None) -> bool:
        return (
            s is not None
            and s.ended_at is None
            and s.client == "claude_code"
            and s.token_id is not None
            and s.token_id == token_id
            and s.handle == handle
        )

    def _tool_map_target(self, token_id: str | None, tuid: str | None, handle: str | None, client: str | None) -> AgentSession | None:
        """_emit 用（不写审计）：这次调用已有映射、而且映射的会话现在仍然有效，就返回该会话。"""
        if client != "claude_code":
            return None
        m = self._live_tool_map(token_id, tuid)
        if m is None:
            return None
        s = self.sessions.get(("claude_code", m.session))
        return s if self._claude_session_ok(s, token_id, handle) else None

    def tool_map_session(self, handle: str, client: str | None, token_id: str | None, raw_tuid: Any) -> AgentSession | None:
        """MCP 调用到达时（mcp_server._attribution）：映射已经先到了，就按它判 exact。

        会话仍要过 resolve_session（存在、未结束、同 token、同 client），不成立就是成员级并写审计。"""
        tuid = tool_use_id(raw_tuid)
        if client != "claude_code" or tuid is None:
            return None
        with self.lock:
            m = self._live_tool_map(token_id, tuid)
            if m is None:
                return None
            return self.resolve_session(handle, client, token_id, m.session, source="tool_map")

    def _attach(self, ev: Event, s: AgentSession) -> None:
        """把一条成员级事件补成 exact（幂等：已经有会话的不动）。认领/开始类事件顺带设置会话的 current_task。"""
        if ev.session is not None or ev.attribution != "member":
            return
        ev.session, ev.attribution, ev.session_src = s.external_id, "exact", "tool_map"
        if ev.type in START_EVENT_TYPES:
            self._current_from_event(s, ev)

    def _current_from_event(self, s: AgentSession, ev: Event) -> bool:
        """认领/开始类事件补成 exact 之后：任务仍由该成员进行中、这次调用之后没有别的调用再开始过它，
        而且会话没有指向更新的任务，才把会话的 current_task 设为它。"""
        t = self.tasks.get(ev.subject or "")
        if s.ended_at is not None or t is None or t.status != "in_progress" or t.assignee != s.handle:
            return False
        later = any(
            e.subject == t.id
            and e.id > ev.id
            and e.type in ("task.started", "task.released")
            and not (e.token_id == ev.token_id and e.tool_use == ev.tool_use)
            for e in self.events
        )
        if later:
            return False
        if s.current_task not in (None, t.id) and (s.current_task_ev or 0) > ev.id:
            return False
        s.current_task, s.current_task_ev = t.id, ev.id
        return True

    def _hook_tool_map(
        self, actor: Actor, client: str, sid: str | None, it: dict[str, Any], *, ended_here: set[str] = frozenset()  # type: ignore[assignment]
    ) -> tuple[str, str | None, int]:
        """处理一条 tool_map，返回 (st, err, 补成 exact 的事件数)。st：ok / bad / ignored。

        ended_here：同一批里由这枚 token 自己的 end 刚结束的会话。PostToolUse 写映射一定在 SessionEnd 之前，
        CLI 的 spool 却不保证上报顺序，所以这种会话仍然认（同 token、client、handle 照查），只是不再设置 current_task。"""
        tuid = tool_use_id(it.get("tool_use_id"))
        if tuid is None:
            return "bad", "tool_use_id", 0
        if not sid:
            return "bad", "session", 0
        tool = it.get("tool")
        if tool is not None and tool not in TOOL_NAMES:
            return "bad", "tool", 0
        if client != "claude_code" or not actor.token_id:
            # 只有 Claude Code 装 PostToolUse；Codex 的调用自带 _meta 的 session_id
            self._audit("tool_map.client", actor, "ignored", client=client)
            return "ignored", "client", 0
        s: AgentSession | None = None
        if sid in ended_here:
            cand = self.sessions.get((client, sid))
            if (
                cand is not None
                and cand.ended_at is not None
                and cand.client == "claude_code"
                and cand.token_id == actor.token_id
                and cand.handle == actor.handle
            ):
                s = cand
        if s is None:
            s = self.resolve_session(actor.handle, client, actor.token_id, sid, source="tool_map", via="hook")
        if s is None:  # 不存在、已结束、别的 token 或别人登记的：resolve_session 已写审计
            return "ignored", "session", 0
        key = (actor.token_id, tuid)
        prev = self._live_tool_map(actor.token_id, tuid)
        if prev is not None and prev.session != s.external_id:
            self._audit("tool_map.conflict", actor, "ignored", client=client)
            return "ignored", "conflict", 0
        now = self.now()
        if prev is None and tool not in READ_TOOL_NAMES:
            # 读工具不产生事件，不用存；其余（包括没写 tool 的）存 24 小时，调用晚到时直接判 exact
            self.tool_maps[key] = ToolMap(s.external_id, tool, now, now + TOOL_MAP_TTL)
        n = 0
        cutoff = now - TOOL_MAP_TTL
        for ev in self.call_events.get(key, []):
            if (
                ev.attribution == "member"
                and ev.session is None
                and ev.token_id == actor.token_id
                and ev.client == "claude_code"
                and ev.actor == s.handle
                and ev.at >= cutoff
            ):
                self._attach(ev, s)
                n += 1
        return "ok", None, n

    @staticmethod
    def _sid(d: dict[str, Any]) -> str | None:
        """会话 ID：CLI 发 session_id；也接受 session。标识类字段不匹配白名单的只存哈希。"""
        raw = d.get("session_id") or d.get("session")
        return ident_or_hash(str(raw)) if raw else None

    def _snapshot(self, actor: Actor, repo: str | None) -> dict[str, Any]:
        """session-start 与 delta 共用的结构化快照：只有 ID、计数、handle、枚举值（H5）。"""
        ib = self.inbox(actor, limit=10, advance=False)
        me = actor.handle
        since = self.pool_seen.get(me)
        pool_new = sum(1 for t in self.tasks.values() if t.label == "pool" and t.created_by != me and (since is None or t.created_at > since))
        repo_hint: list[str] = []
        if repo:
            pats = {k: p.repo_patterns for k, p in self.projects.items()}
            for t in self.tasks.values():
                if t.assignee == me and t.status in ("open", "in_progress") and t.project:
                    if any(fnmatch.fnmatch(repo, pat) for pat in pats.get(t.project, [])):
                        repo_hint.append(t.id)
        return {
            "v": 1,
            "me": me,
            "doing": ib["doing"],
            "todo": ib["todo"],
            "to_accept": ib["to_accept"],
            "help_me": ib["help_me"],
            "fwd": ib["fwd"],
            "proposed": ib["proposed"],
            "pool_new": pool_new,
            "repo_hint": sorted(repo_hint),
        }

    def hook_session_start(self, actor: Actor, payload: dict[str, Any]) -> dict[str, Any]:
        """SessionStart：登记会话，返回结构化快照 + cursor（给后续 /me/delta 用）。不返回成段文字。

        会话的 client 一律取 token 的 client，请求体里的 client 不作数（防止用一端的 token 登记另一端的会话）。
        """
        client = actor.client or self.norm_client(payload.get("client"))
        sid = self._sid(payload)
        if client is None:
            raise DomainError("invalid", "client 只能是 claude、codex 或 cli。")
        source = payload.get("source")
        source = source if source in ("startup", "resume", "clear", "compact", "fork") else "other"
        repo = ident_or_hash(payload.get("repo"))
        with self.lock:
            if sid:
                self._upsert_session(
                    actor,
                    client,
                    sid,
                    repo=repo,
                    branch=ident_or_hash(payload.get("branch")),
                    head=ident_or_hash(payload.get("head")),
                    cwd_name=ident_or_hash(payload.get("cwd_name")),
                    interactive=bool(payload["interactive"]) if isinstance(payload.get("interactive"), bool) else None,
                    source=source,
                    machine_id=ident_or_hash(payload.get("machine_id")),
                    reopen=True,
                )
            snap = self._snapshot(actor, repo)
            self.pool_seen[actor.handle] = self.now()
            snap["cursor"] = self.latest_event_id()
            return snap

    HOOK_TYPES = ("turn_end", "commit", "end", "start", "tool_map")
    _REASON = re.compile(r"^[a-z_]{1,32}$")
    _SHA = re.compile(r"^[0-9a-f]{7,40}$")

    def _hook_commit(self, actor: Actor, repo: str | None, sha: Any, title: Any) -> str:
        """记一条本人提交；返回 ok / masked / bad。提交标题命中扫描只遮蔽，不拒绝，不计熔断。"""
        sha = str(sha or "")
        if not self._SHA.fullmatch(sha) or not repo:  # fullmatch：$ 会放过结尾的换行
            return "bad"
        text, rules = mask(clean(str(title))[:200]) if title else ("", [])
        if (repo, sha) not in self.commit_keys:
            self.commit_keys.add((repo, sha))
            self._emit("commit", None, actor, text=text or None, repo=repo, sha=sha, masked=rules or None)
        return "masked" if rules else "ok"

    def hook_batch(self, actor: Actor, items: list[dict[str, Any]]) -> dict[str, Any]:
        """批量上报：最多 100 条，逐条处理并返回状态；按幂等键去重（保留 8 天）；命中扫描只遮蔽不拒绝。

        条目：{"type": turn_end|commit|end|start|tool_map, "key", "session_id", "client", "ts", ...}
        （也接受旧写法 ev / k / session）。turn_end 可带 commits[{sha,title}]（最多 5 条，只限本人邮箱）
        和 other_commits（他人提交只计数）。tool_map 带 tool_use_id、tool（D40，见 _hook_tool_map）：
        会话要过 resolve_session，不成立整条忽略（403 ignored）；结果多带 n（补成 exact 的事件数）。
        CLI 的 spool 不保证顺序，所以同一批里的 tool_map 放到最后处理：同批的 start / turn_end 先把会话登记上；
        同批的 end 刚结束的这枚 token 自己的会话仍然认（调用一定发生在结束之前），但不再设置 current_task。
        结果按条目原来的顺序返回。
        条目里的 client 强制等于 token 的 client；条目指向的会话属于别的 token 时，整条忽略（不记提交、
        不改会话、end 也不清对方会话的 current_task），写审计，返回 403 ignored。
        返回 results[{key, status, st}]：status 是逐条 HTTP 语义（200 成功、409 重复、422 不合格、403 忽略），st 是枚举。
        """
        if len(items) > 100:
            raise DomainError("too_many", "一次最多 100 条，请分批发送。", max=100)
        results: list[dict[str, Any]] = [{} for _ in items]
        codes = {"ok": 200, "masked": 200, "dup": 409, "bad": 422, "ignored": 403}
        idx = 0

        def res(key: str | None, st: str, err: str | None = None, at: int | None = None, **more: Any) -> None:
            r: dict[str, Any] = {"key": key, "status": codes[st], "st": st}
            if err:
                r["err"] = err
            r.update(more)
            results[idx if at is None else at] = r

        deferred: list[tuple[int, str, tuple[str, str], str, str | None, dict[str, Any]]] = []
        tool_map_keys: set[str] = set()
        ended_here: set[str] = set()  # 这一批里由这枚 token 自己的 end 结束的会话

        with self.lock:
            now = self.now()
            for k_, exp in list(self.hook_keys.items()):
                if exp < now:
                    del self.hook_keys[k_]
            self._purge_tool_maps()
            for idx, it in enumerate(items):
                if not isinstance(it, dict):
                    res(None, "bad", "item")
                    continue
                k = str(it.get("key") or it.get("k") or "")
                if not k or len(k) > 128:
                    res(k or None, "bad", "key")
                    continue
                hk = (actor.token_id or actor.handle, k)
                if hk in self.hook_keys:
                    res(k, "dup")
                    continue
                typ = it.get("type") or it.get("ev")
                if typ not in self.HOOK_TYPES:
                    res(k, "bad", "type")
                    continue
                claimed_client = self.norm_client(it.get("client"))
                client = actor.client or claimed_client or "cli"  # 强制等于 token 的 client
                if claimed_client and claimed_client != client:
                    self._audit("hook.client_mismatch", actor, "forced", claimed=claimed_client, client=client)
                sid = self._sid(it)
                if typ == "tool_map":
                    if k in tool_map_keys:
                        res(k, "dup")
                        continue
                    tool_map_keys.add(k)
                    deferred.append((idx, k, hk, client, sid, it))
                    continue
                if sid:
                    owner = self.sessions.get((client, sid))
                    if owner is not None and owner.token_id != actor.token_id:
                        self._audit("session.token_mismatch", actor, "ignored", client=client, type=str(typ))
                        res(k, "ignored", "session")
                        continue
                repo = ident_or_hash(it.get("repo"))
                st = "ok"
                if typ in ("turn_end", "start"):
                    if sid:
                        self._upsert_session(
                            actor,
                            client,
                            sid,
                            repo=repo,
                            branch=ident_or_hash(it.get("branch")),
                            head=ident_or_hash(it.get("head")),
                            cwd_name=ident_or_hash(it.get("cwd_name")),
                            reopen=(typ == "start"),
                        )
                    commits = it.get("commits") if isinstance(it.get("commits"), list) else []
                    for c in commits[:5]:
                        if isinstance(c, dict):
                            r = self._hook_commit(actor, repo, c.get("sha"), c.get("title"))
                            if r == "masked":
                                st = "masked"
                elif typ == "end":
                    if sid:
                        reason = it.get("reason") if isinstance(it.get("reason"), str) and self._REASON.fullmatch(it["reason"]) else "other"
                        if self._upsert_session(actor, client, sid, ended_at=now, end_reason=reason) is not None:
                            self._clear_session_task(client, sid)
                            ended_here.add(sid)
                elif typ == "commit":
                    r = self._hook_commit(actor, repo, it.get("sha"), it.get("title"))
                    if r == "bad":
                        res(k, "bad", "sha_or_repo")
                        continue
                    st = r
                    if sid:
                        self._upsert_session(actor, client, sid)
                self.hook_keys[hk] = now + timedelta(days=8)
                res(k, st)
            for i, k, hk, client, sid, it in deferred:
                st_, err_, n_ = self._hook_tool_map(actor, client, sid, it, ended_here=ended_here)
                if st_ != "ok":
                    res(k, st_, err_, at=i)
                    continue
                self.hook_keys[hk] = now + timedelta(days=8)
                res(k, "ok", at=i, n=n_)
            return {"results": results}

    def _clear_session_task(self, client: str, sid: str) -> None:
        s = self.sessions.get((client, sid))
        if s:
            s.current_task = None

    def delta(self, actor: Actor, cursor: int = 0, limit: int = 50) -> dict[str, Any]:
        """增量：当前结构化快照（与 session-start 同形）+ cursor 之后与我有关的事件（只有 ID/handle/枚举）。"""
        with self.lock:
            evs = self._relevant_events(actor.handle, cursor)
            page = evs[:limit]
            items = [
                {"e": e.id, "ty": e.type, "id": e.subject, "by": e.actor, "bk": "human" if e.actor_kind == "human" else "agent", "client": e.client}
                for e in page
            ]
            more = len(evs) > len(page)
            # 还有下一页时游标停在本页最后一条；否则推进到当前水位（跳过与我无关的事件）
            last = page[-1].id if more else max(cursor, self._next_event_id - 1)
            snap = self._snapshot(actor, None)
            snap.pop("repo_hint", None)
            return {**snap, "cursor": last, "items": items, "more": more}

    def latest_event_id(self) -> int:
        return self._next_event_id - 1

    # -- 幂等（Idempotency-Key / Codex _meta.callId） ----------------------------------

    def idem_begin(self, scope: str, owner: str, key: str, fingerprint: str) -> tuple[str, IdemRec | None]:
        """返回 ("new"|"replay"|"in_flight"|"mismatch", rec)。"""
        with self.lock:
            k = (scope, owner, key)
            now = self.now()
            rec = self.idem.get(k)
            if rec and rec.expires_at and rec.expires_at < now:
                rec = None
            if rec is None:
                self.idem[k] = IdemRec(fingerprint, "in_flight", expires_at=now + timedelta(days=1))
                return "new", None
            if rec.fingerprint != fingerprint:
                return "mismatch", rec
            if rec.state == "in_flight":
                return "in_flight", rec
            return "replay", rec

    def idem_finish(self, scope: str, owner: str, key: str, status: int, response: Any) -> None:
        with self.lock:
            rec = self.idem.get((scope, owner, key))
            if rec:
                rec.state, rec.status, rec.response = "done", status, response

    def idem_abort(self, scope: str, owner: str, key: str) -> None:
        with self.lock:
            self.idem.pop((scope, owner, key), None)

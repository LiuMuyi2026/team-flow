// 网页 API 的形状（docs/web-api.md）。只列页面用到的字段。

export type Trust = "self_human" | "self_agent" | "peer_human" | "peer_agent";
export type Client = "claude_code" | "codex" | "cli" | "cloud" | string;

/** 标题和正文的信封：纯文本 t + 作者信息。文字一律当纯文本渲染。 */
export interface Envelope {
  t: string;
  by: string | null;
  trust: Trust;
  client: Client | null;
  label: string;
}

export interface Member {
  h: string;
  name: string;
}

export interface Project {
  key: string;
  name: string;
}

export interface Me {
  me: string;
  name: string;
  csrf: string;
  mode: string;
  expires: string;
  members: Member[];
  projects: Project[];
}

export interface Counts {
  pool: number;
  pending: number;
  todo: number;
  doing: number;
  blockers: number;
}

export interface Home {
  me: string;
  mine: {
    to_accept: { id: string; by: string | null; bk: "human" | "agent" | null; client: Client | null }[];
    help_me: { id: string; by: string }[];
    proposed: { id: string; h: string | null; client: Client | null }[];
    fwd: { id: string; n: number; by: string }[];
    replies: { id: string; ev: "accepted" | "declined" | "done" | string; by: string }[];
  };
  blockers: {
    id: string;
    by: string;
    task: string | null;
    since: string;
    stuck_min?: number;
    need?: string;
    helper?: string;
  }[];
  doing: { h: string | null; id: string; client: Client | null; sess?: { client: Client; s: string }[]; today: boolean }[];
  counts: Counts;
  titles: Record<string, Envelope>;
  projects: (Project & { counts: Counts })[];
}

export type TaskView = "pool" | "doing" | "mine" | "done" | "all";

export interface TaskRow {
  id: string;
  t: Envelope;
  st: string;
  st_text: string;
  who?: string;
  blk?: string[];
  upd: string;
  path: string;
}

export interface TaskList {
  rows: TaskRow[];
  next: string | null;
}

export interface Ev {
  e: number;
  ty: string;
  by?: string;
  trust?: Trust;
  client?: Client | null;
  at: string;
  ts: string;
  t?: string;
  agent?: boolean;
  data?: Record<string, unknown>;
  label?: string;
  what: string;
}

export interface PageVals {
  id: string;
  v: number;
  sha: string;
  through: number;
  seq?: number;
}

export interface AgentView {
  content: "visible" | "needs_accept" | "none";
  through: number;
  unforwarded: number;
}

interface ItemBase {
  id: string;
  t: Envelope;
  st: string;
  st_text: string;
  v: number;
  ev: Ev[];
  page: PageVals;
  agent: AgentView;
  created: string;
  can: string[];
  path: string;
}

export interface TaskItem extends ItemBase {
  kind: "task";
  who?: string;
  by: string;
  assign?: { seq: number; by: string | null; bk?: "human" | "agent" | null; client?: Client | null };
  project?: string;
  parent?: string;
  blk?: string[];
  content?: Envelope;
  urgent?: boolean;
}

export interface BlockerItem extends ItemBase {
  kind: "blocker";
  task?: string;
  need?: string;
  need_state: "none" | "proposed" | "asked";
  need_text?: string;
  helper?: string;
  task_closed?: boolean;
  content?: { detail?: Envelope; tried?: Envelope };
}

export type Item = TaskItem | BlockerItem;

export interface WechatItem {
  n: number;
  kind: string;
  kind_text: string;
  text: string;
  subject: string | null;
  at: string | null;
  ts: string | null;
  path: string | null;
}

export interface Wechat {
  items: WechatItem[];
  total: number;
}

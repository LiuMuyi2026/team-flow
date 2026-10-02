// 页面上的说法：作者标注、作者类别、时长。全部是纯文本。
import type { Client, Envelope, Ev, Trust } from "./types";

const CLIENTS: Record<string, string> = {
  claude_code: "Claude Code",
  codex: "Codex",
  cli: "命令行",
  cloud: "云端 agent",
};

export function clientName(c: Client | null | undefined): string {
  if (!c) return "agent";
  return CLIENTS[c] ?? c;
}

/** 某人（handle）在页面上的叫法：本人叫「您」。 */
export function person(h: string | null | undefined, me: string): string {
  if (!h) return "有人";
  return h === me ? "您" : h;
}

/** 作者标注：「您」「您的 Codex」「alice」「alice 的 Claude Code」。 */
export function authorOf(by: string | null | undefined, trust: Trust | undefined, client: Client | null | undefined, me: string): string {
  if (!by) return "系统";
  const agent = trust ? trust.endsWith("_agent") : false;
  if (by === me) return agent ? `您的 ${clientName(client)}` : "您";
  return agent ? `${by} 的 ${clientName(client)}` : by;
}

/** 中文里夹英文 handle 时两边各空一格；「您」不空：`请${pad(who)}帮忙` → 「请 alice 帮忙」「请您帮忙」。 */
export function pad(who: string): string {
  return who.startsWith("您") ? who : ` ${who} `;
}

/**
 * 中文排版的空格：「您」和汉字之间、中文标点两边都不留空格。
 * 「已点名 您」→「已点名您」、「您 报告」→「您报告」、「已认领。 bob」→「已认领。bob」。
 */
export function tidy(s: string): string {
  return s
    .replace(/(?<=[\u4e00-\u9fff])\s+您|您\s+(?=[\u4e00-\u9fff])/g, "您")
    .replace(/([，。：；、！？（「])\s+/g, "$1")
    .replace(/\s+([，。：；、！？）」])/g, "$1");
}

/** 中文里夹英文 handle 时前面空一格；「您」开头的不空。 */
export function sp(who: string): string {
  return who.startsWith("您") ? who : ` ${who}`;
}

export function envAuthor(env: Envelope, me: string): string {
  return authorOf(env.by, env.trust, env.client, me);
}

export function evAuthor(ev: Ev, me: string): string {
  return authorOf(ev.by ?? null, ev.trust, ev.client ?? null, me);
}

/** 作者类别（plan 3.1 的四级信任）。 */
export function trustText(trust: Trust | undefined): string {
  switch (trust) {
    case "self_human":
      return "您本人写的";
    case "self_agent":
      return "您的 agent 写的";
    case "peer_human":
      return "队友本人写的";
    case "peer_agent":
      return "队友的 agent 写的";
    default:
      return "";
  }
}

/** 详情页正文上方的醒目标注：「这段话由 alice 的 Claude Code 生成」。 */
export function contentByline(env: Envelope, me: string): string {
  const who = envAuthor(env, me);
  if (env.trust.endsWith("_agent")) return `这段话由${sp(who)} 生成`;
  return env.by === me ? "这段话是您写的" : `这段话是${sp(who)} 本人写的`;
}

/** 卡住多久：「刚刚」「25 分钟」「3 小时」「2 天」。 */
export function stuckText(min: number | undefined): string {
  if (min === undefined || min < 1) return "刚刚卡住";
  if (min < 60) return `已卡 ${min} 分钟`;
  if (min < 24 * 60) return `已卡 ${Math.floor(min / 60)} 小时`;
  return `已卡 ${Math.floor(min / (24 * 60))} 天`;
}

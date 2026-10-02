// 风险高亮（plan 7.1）：不依赖 LLM，命中这些模式就标出来，提醒人接受前多看一眼。
// 只做提示，不拦截；真正的拦截（密钥、个人信息）在服务端，命中直接 422。

export interface RiskRule {
  id: string;
  /** 给人看的说法，出现在「请留意：这段文字提到了……」里 */
  text: string;
  re: RegExp;
}

export const RISK_RULES: RiskRule[] = [
  { id: "ssh", text: "SSH 密钥目录", re: /~\/\.ssh\b|\.ssh\/|\bid_(?:rsa|ed25519|ecdsa)\b|authorized_keys/gi },
  { id: "aws", text: "云服务凭据", re: /~\/\.aws\b|\.aws\/|\baws_(?:secret|access)[a-z_]*/gi },
  { id: "env", text: "环境变量", re: /(?<![\w.])\.env(?:\.[\w-]+)?\b|\bprintenv\b|\benv\s*\||环境变量/gi },
  {
    id: "token",
    text: "令牌或密码",
    re: /\b(?:access[_-]?)?tokens?\b|\bapi[_-]?keys?\b|\bsecrets?\b|\bpasswo?r?d\b|\bcredentials?\b|令牌|密码|密钥|凭据/gi,
  },
  { id: "pipe_sh", text: "下载后直接执行（curl | sh）", re: /\b(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|da)?sh\b/gi },
  { id: "rm", text: "删除命令", re: /\brm\s+-[a-z]*r[a-z]*f?\b[^\n]*|\bsudo\s+rm\b[^\n]*/gi },
  { id: "base64", text: "很长的编码串", re: /[A-Za-z0-9+/_-]{48,}={0,2}/g },
  { id: "url", text: "外部网址", re: /\b(?:https?|ftp):\/\/[^\s<>"'，。；）)\]]+|\bwww\.[a-z0-9-]+\.[^\s<>"'，。；）)\]]+/gi },
  {
    id: "ignore",
    text: "让 agent 忽略指令的说法",
    re: /(?:忽略|无视|不要理会|别管|忘掉|忘记)[^。\n]{0,24}?(?:指令|指示|规则|说明|要求|提示|设定)|\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+)?(?:the\s+)?(?:previous|prior|above|earlier|system)\s+(?:instructions?|prompts?|rules?)/gi,
  },
];

export interface Hit {
  start: number;
  end: number;
  rules: string[];
}

export interface Segment {
  text: string;
  /** 命中的规则说法；空表示普通文字 */
  risk: string[];
}

/** 找出全部命中，重叠的合并成一段。 */
export function findRisks(text: string): Hit[] {
  const raw: Hit[] = [];
  for (const rule of RISK_RULES) {
    rule.re.lastIndex = 0;
    for (const m of text.matchAll(rule.re)) {
      if (m.index === undefined || m[0].length === 0) continue;
      raw.push({ start: m.index, end: m.index + m[0].length, rules: [rule.text] });
    }
  }
  raw.sort((a, b) => a.start - b.start || b.end - a.end);
  const out: Hit[] = [];
  for (const h of raw) {
    const last = out[out.length - 1];
    if (last && h.start < last.end) {
      last.end = Math.max(last.end, h.end);
      for (const r of h.rules) if (!last.rules.includes(r)) last.rules.push(r);
    } else {
      out.push({ ...h, rules: [...h.rules] });
    }
  }
  return out;
}

export function segments(text: string): Segment[] {
  const hits = findRisks(text);
  const out: Segment[] = [];
  let pos = 0;
  for (const h of hits) {
    if (h.start > pos) out.push({ text: text.slice(pos, h.start), risk: [] });
    out.push({ text: text.slice(h.start, h.end), risk: h.rules });
    pos = h.end;
  }
  if (pos < text.length) out.push({ text: text.slice(pos), risk: [] });
  return out;
}

/** 一组文字里命中的规则说法（去重，按规则表顺序）。 */
export function riskKinds(...texts: (string | undefined | null)[]): string[] {
  const seen = new Set<string>();
  for (const t of texts) if (t) for (const h of findRisks(t)) for (const r of h.rules) seen.add(r);
  return RISK_RULES.map((r) => r.text).filter((t) => seen.has(t));
}

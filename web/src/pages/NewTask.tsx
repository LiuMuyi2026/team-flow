import { useState, type FormEvent } from "react";
import { api, messageOf } from "../api";
import { Notice, type NoticeMsg } from "../components/Notice";
import { useMe } from "../context";
import { useTitle } from "../hooks";
import { navigate } from "../router";

const TITLE_MAX = 120;
const BODY_MAX = 4000;

export function NewTask() {
  const me = useMe();
  useTitle("发布");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [assignee, setAssignee] = useState("");
  const [project, setProject] = useState("");
  const [urgent, setUrgent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<NoticeMsg | null>(null);
  const [tried, setTried] = useState(false);

  const others = me.members.filter((m) => m.h !== me.me);
  const titleMissing = !title.trim();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setTried(true);
    if (titleMissing || busy) return;
    setBusy(true);
    setMsg(null);
    try {
      const res = await api.createTask({
        title: title.trim(),
        body: body.trim() || undefined,
        assignee: assignee || undefined,
        project: project || undefined,
        urgent,
      });
      navigate(res.path);
    } catch (err) {
      setMsg({ kind: "error", text: messageOf(err) });
    } finally {
      setBusy(false);
    }
  };

  const assignHint =
    assignee === ""
      ? "留空就是待认领：谁都可以认领。"
      : assignee === me.me
        ? "指派给您自己：直接进入待开始。"
        : `指派给 ${assignee}：对方会收到微信，要对方接受后才算数。`;

  return (
    <form className="page form" onSubmit={(e) => void submit(e)} noValidate>
      <h1 className="page-title">发布</h1>

      <label className="field-label" htmlFor="f-title">
        标题
      </label>
      <input
        id="f-title"
        type="text"
        value={title}
        maxLength={TITLE_MAX}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="一句话说清楚要做什么"
        aria-invalid={tried && titleMissing ? true : undefined}
        autoComplete="off"
      />
      {tried && titleMissing && <p className="field-error">请先写标题。</p>}

      <label className="field-label" htmlFor="f-body">
        内容（选填）
      </label>
      <textarea id="f-body" rows={6} value={body} maxLength={BODY_MAX} onChange={(e) => setBody(e.target.value)} placeholder="背景、要求、链接，想到什么写什么" />
      <p className="hint">
        对方接受或认领后，对方的 agent 能读到这段内容。不要写密钥、token 和个人信息，写了会被拦下。
        {body.length > BODY_MAX - 300 ? ` 还能写 ${BODY_MAX - body.length} 字。` : ""}
      </p>

      <label className="field-label" htmlFor="f-assignee">
        指派给
      </label>
      <select id="f-assignee" value={assignee} onChange={(e) => setAssignee(e.target.value)}>
        <option value="">留空（待认领）</option>
        <option value={me.me}>我自己</option>
        {others.map((m) => (
          <option key={m.h} value={m.h}>
            {m.name && m.name !== m.h ? `${m.h}（${m.name}）` : m.h}
          </option>
        ))}
      </select>
      <p className="hint">{assignHint}</p>

      <label className="field-label" htmlFor="f-project">
        项目（选填）
      </label>
      <select id="f-project" value={project} onChange={(e) => setProject(e.target.value)}>
        <option value="">不选</option>
        {me.projects.map((p) => (
          <option key={p.key} value={p.key}>
            {p.name}
          </option>
        ))}
      </select>

      <label className="check">
        <input type="checkbox" checked={urgent} onChange={(e) => setUrgent(e.target.checked)} /> 紧急
      </label>
      <p className="hint">标了紧急，对方在免打扰时间也会收到微信。请只在真着急时用。</p>

      <div className="btn-row">
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "正在发布…" : "发布"}
        </button>
      </div>
      <Notice msg={msg} onClose={() => setMsg(null)} />
    </form>
  );
}

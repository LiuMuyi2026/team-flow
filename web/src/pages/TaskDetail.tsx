import { useEffect, useState } from "react";
import { api } from "../api";
import { Events } from "../components/Events";
import { CommentBox, TextAction } from "../components/Forms";
import { Notice } from "../components/Notice";
import { LONG_BODY, useReadToEnd } from "../components/ReadToEnd";
import { RiskNote, RiskText } from "../components/RiskText";
import { useDetail } from "../components/useDetail";
import { projectName, useMe } from "../context";
import { useTitle } from "../hooks";
import { authorOf, clientName, contentByline, envAuthor, person, sp, tidy } from "../labels";
import { riskKinds } from "../risk";
import { Link } from "../router";
import type { TaskItem } from "../types";
import { AgentLine, DetailMissing, ForwardBlock, StaleBanner, when } from "./detailParts";

export function TaskDetail({ id }: { id: string }) {
  const me = useMe();
  const d = useDetail<TaskItem>("task", id);
  const t = d.item;
  const body = t?.content?.t ?? "";
  const long = body.length > LONG_BODY;
  const gate = useReadToEnd(long, t ? `${t.page.v}:${t.page.sha}:${t.page.seq ?? ""}` : "");
  useTitle(t ? `${t.id} ${t.t.t}` : id);

  if (!t) return <DetailMissing id={id} error={d.error} loading={d.loading} />;

  const can = new Set(t.can);
  const page = t.page;
  const locked = !gate.seen;
  const busy = d.busy !== null;
  const kinds = riskKinds(t.t.t, body);
  const how = can.has("accept") ? "点「接受」" : can.has("claim") ? "点「认领」" : "";
  const assigner = t.assign ? authorOf(t.assign.by, t.assign.bk === "agent" ? "peer_agent" : "peer_human", t.assign.client, me.me) : "";

  const accept = () =>
    d.run("accept", () => api.taskAction(t.id, "accept", { v: page.v, sha: page.sha, seq: page.seq, through: page.through }), "已接受。您的 agent 现在能读到正文和截至刚才的评论了。");
  const claim = () =>
    d.run("claim", () => api.taskAction(t.id, "claim", { v: page.v, sha: page.sha, through: page.through }), "已认领，任务归您了。您的 agent 现在能读到正文。");
  const start = () => d.run("start", () => api.taskAction(t.id, "start", {}), "已开始。");
  const forward = () =>
    d.run("forward", () => api.taskAction(t.id, "forward", { through: page.through }), "已转发。您的 agent 下一回合就能读到这些评论。");

  return (
    <article className="detail">
      <p className="crumb">
        {t.id} · {t.st_text}
        {t.project ? ` · ${projectName(me, t.project)}` : ""}
        {t.urgent ? " · 紧急" : ""}
      </p>
      <h1 className="title">
        <RiskText text={t.t.t} />
      </h1>
      <p className="meta">
        {tidy(`${envAuthor(t.t, me.me)} 发布`)} · {when(t.created)}
      </p>
      <dl className="facts">
        {t.assign && t.who === me.me && (
          <>
            <dt>请您协作</dt>
            <dd>{assigner} 把这件事指派给了您，等您接受。</dd>
          </>
        )}
        {t.assign && t.who !== me.me && (
          <>
            <dt>指派给</dt>
            <dd>{person(t.who, me.me)}，等对方接受</dd>
          </>
        )}
        {!t.assign && (
          <>
            <dt>负责人</dt>
            <dd>{t.who ? person(t.who, me.me) : "还没有人认领"}</dd>
          </>
        )}
        {t.parent && (
          <>
            <dt>上级任务</dt>
            <dd>
              <Link to={`/task?w=team&id=${t.parent}`}>{t.parent}</Link>
            </dd>
          </>
        )}
        {t.blk && t.blk.length > 0 && (
          <>
            <dt>卡在</dt>
            <dd>
              {t.blk.map((b, i) => (
                <span key={b}>
                  {i > 0 ? "、" : ""}
                  <Link to={`/blocker?w=team&id=${b}`}>{b}</Link>
                </span>
              ))}
            </dd>
          </>
        )}
      </dl>

      <section className="block" aria-labelledby="sec-content">
        <h2 id="sec-content">内容</h2>
        {t.content ? (
          <>
            <p className="byline">{contentByline(t.content, me.me)}</p>
            <RiskNote kinds={kinds} />
            <div className="body text">
              <RiskText text={body} />
            </div>
            <div ref={gate.ref} className="end-mark" aria-hidden="true" />
            <p className="hint">这就是您的 agent 能拿到的那段文字，和这里显示的一字不差。</p>
          </>
        ) : (
          <>
            <RiskNote kinds={kinds} />
            <p className="muted">没有正文，只有标题。</p>
          </>
        )}
        <AgentLine content={t.agent.content} how={how} />
      </section>

      <section className="block" aria-labelledby="sec-ev">
        <h2 id="sec-ev">动态和评论（{t.ev.length}）</h2>
        <Events ev={t.ev} me={me.me} />
      </section>

      <section className="block actions" aria-labelledby="sec-act">
        <h2 id="sec-act">操作</h2>
        <Notice msg={d.noticeFor("actions")} onClose={d.closeNotice} onBack={d.backToContent} />
        {long && locked && <p className="hint gate-hint">正文比较长，请先滑到正文最后，按钮才能点。</p>}

        {can.has("accept") && (
          <div className="action">
            <button type="button" className="btn btn-primary" disabled={locked || busy} onClick={() => void accept()}>
              接受
            </button>
            <p className="hint">接受后，您的 {clientNames()} 就能读到上面的正文和截至现在的评论。</p>
          </div>
        )}
        {can.has("decline") && (
          <div className="action">
            <TextAction
              label="拒绝"
              field="拒绝原因（必填）"
              hint={`说一句原因，对方好另做安排。任务会回到发布人${sp(person(t.by, me.me))} 手里。`}
              required
              maxLength={500}
              disabled={locked}
              busy={busy}
              onSubmit={(reason) => d.run("decline", () => api.taskAction(t.id, "decline", { seq: page.seq, reason }), "已拒绝，对方会收到通知。")}
            />
          </div>
        )}
        {can.has("claim") && (
          <div className="action">
            <button type="button" className="btn btn-primary" disabled={locked || busy} onClick={() => void claim()}>
              认领
            </button>
            <p className="hint">认领后任务归您（待开始），您的 agent 就能读到上面的正文。由您或您的 agent 开始做。</p>
          </div>
        )}
        {can.has("start") && (
          <div className="action">
            <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void start()}>
              开始
            </button>
            <p className="hint">开始后，首页「大家在做什么」里会显示您在做这件事。</p>
          </div>
        )}
        {can.has("done") && (
          <div className="action">
            <TextAction
              label="完成"
              field="完成说明（选填）"
              hint="比如合了哪个 PR、还剩什么没做。"
              busy={busy}
              onSubmit={(note) => d.run("done", () => api.taskAction(t.id, "done", note ? { note } : {}), "已完成。")}
            />
          </div>
        )}
        {can.has("release") && (
          <ReleaseAction
            todo={t.st === "todo"}
            busy={busy}
            onSubmit={(note, toPool) =>
              d.run(
                "release",
                () => api.taskAction(t.id, "release", { ...(note ? { note } : {}), to_pool: toPool }),
                toPool ? "已放回待认领。" : "已取消认领，任务回到待开始。",
              )
            }
          />
        )}
        {can.has("forward") && (
          <ForwardBlock n={t.agent.unforwarded} content={t.agent.content} how={how} busy={busy} onForward={() => void forward()} />
        )}
        {!["accept", "decline", "claim", "start", "done", "release", "forward"].some((a) => can.has(a)) && (
          <p className="muted">这件事现在不需要您操作，可以评论。</p>
        )}
      </section>

      <section className="block">
        <Notice msg={d.noticeFor("comment")} onClose={d.closeNotice} />
        {can.has("comment") && (
          <CommentBox busy={busy} onSubmit={(text) => d.run("comment", () => api.comment("task", t.id, text), "评论已发布。")} />
        )}
      </section>

      <div className="floating">
        <StaleBanner kind={d.stale} onShow={d.showLatest} />
      </div>
    </article>
  );
}

function clientNames(): string {
  return `${clientName("claude_code")} / ${clientName("codex")}`;
}

function ReleaseAction({ todo, busy, onSubmit }: { todo: boolean; busy: boolean; onSubmit: (note: string, toPool: boolean) => Promise<boolean> }) {
  const [toPool, setToPool] = useState(todo);
  useEffect(() => setToPool(todo), [todo]);
  return (
    <div className="action">
      <TextAction
        label="取消认领"
        field="取消认领的说明（选填）"
        hint={todo ? "还没开始的任务，取消认领就是放回待认领，让别人认领。" : "不勾选只是先停下来（回到待开始，任务还归您）；勾上「放回待认领」就交给别人认领。"}
        busy={busy}
        extra={() => (
          <label className="check">
            <input type="checkbox" checked={todo || toPool} disabled={todo} onChange={(e) => setToPool(e.target.checked)} /> 放回待认领，让别人认领
          </label>
        )}
        onSubmit={(note) => onSubmit(note, todo || toPool)}
      />
    </div>
  );
}

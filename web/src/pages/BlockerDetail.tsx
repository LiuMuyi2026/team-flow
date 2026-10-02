import { api } from "../api";
import { Events } from "../components/Events";
import { CommentBox, TextAction } from "../components/Forms";
import { Notice } from "../components/Notice";
import { LONG_BODY, useReadToEnd } from "../components/ReadToEnd";
import { RiskNote, RiskText } from "../components/RiskText";
import { useDetail } from "../components/useDetail";
import { useMe } from "../context";
import { useTitle } from "../hooks";
import { clientName, contentByline, envAuthor, pad, person, tidy } from "../labels";
import { riskKinds } from "../risk";
import { Link } from "../router";
import type { BlockerItem } from "../types";
import { AgentLine, DetailMissing, ForwardBlock, StaleBanner, when } from "./detailParts";

export function BlockerDetail({ id }: { id: string }) {
  const me = useMe();
  const d = useDetail<BlockerItem>("blocker", id);
  const b = d.item;
  const detail = b?.content?.detail?.t ?? "";
  const tried = b?.content?.tried?.t ?? "";
  const long = detail.length + tried.length > LONG_BODY;
  const gate = useReadToEnd(long, b ? `${b.page.v}:${b.page.sha}` : "");
  useTitle(b ? `${b.id} ${b.t.t}` : id);

  if (!b) return <DetailMissing id={id} error={d.error} loading={d.loading} />;

  const can = new Set(b.can);
  const page = b.page;
  const busy = d.busy !== null;
  const locked = !gate.seen;
  const raiser = b.t.by ?? "";
  const mine = raiser === me.me;
  const env = b.content?.detail ?? b.content?.tried;
  const kinds = riskKinds(b.t.t, detail, tried);
  const how = can.has("help") ? "点「认领」来帮忙" : "";

  const help = () =>
    d.run("help", () => api.blockerAction(b.id, "help", { v: page.v, sha: page.sha, through: page.through }), `已认领。${pad(person(raiser, me.me))}会收到通知：您来帮忙了。`);
  const ask = () => d.run("ask", () => api.blockerAction(b.id, "ask", {}), `已确认，${pad(person(b.need, me.me))}会收到通知。`);
  const forward = () =>
    d.run("forward", () => api.blockerAction(b.id, "forward", { through: page.through }), "已转发。您的 agent 下一回合就能读到这些评论。");

  return (
    <article className="detail">
      <p className="crumb">
        {b.id} · 困难 · {b.st_text}
      </p>
      <h1 className="title">
        <RiskText text={b.t.t} />
      </h1>
      <p className="meta">
        {tidy(`${envAuthor(b.t, me.me)} 报告`)} · {when(b.created)}
      </p>
      <dl className="facts">
        <dt>需要谁</dt>
        <dd>{needText(b, me.me, mine)}</dd>
        <dt>谁在帮</dt>
        <dd>{b.helper ? `${pad(person(b.helper, me.me))}在帮忙`.trim() : "还没有人认领"}</dd>
        {b.task && (
          <>
            <dt>挂在任务</dt>
            <dd>
              <Link to={`/task?w=team&id=${b.task}`}>{b.task}</Link>
              {b.task_closed ? "（任务已经结束）" : ""}
            </dd>
          </>
        )}
      </dl>

      <section className="block" aria-labelledby="sec-content">
        <h2 id="sec-content">卡在哪</h2>
        {env && <p className="byline">{contentByline(env, me.me)}</p>}
        <RiskNote kinds={kinds} />
        {detail ? (
          <div className="body text">
            <RiskText text={detail} />
          </div>
        ) : (
          <p className="muted">没有写。</p>
        )}
        <h2 className="h2-follow">已经试过什么</h2>
        {tried ? (
          <div className="body text">
            <RiskText text={tried} />
          </div>
        ) : (
          <p className="muted">没有写。</p>
        )}
        <div ref={gate.ref} className="end-mark" aria-hidden="true" />
        <AgentLine content={b.agent.content} how={how} what="详情" />
      </section>

      <section className="block" aria-labelledby="sec-ev">
        <h2 id="sec-ev">动态和评论（{b.ev.length}）</h2>
        <Events ev={b.ev} me={me.me} />
      </section>

      <section className="block actions" aria-labelledby="sec-act">
        <h2 id="sec-act">操作</h2>
        <Notice msg={d.noticeFor("actions")} onClose={d.closeNotice} onBack={d.backToContent} />
        {long && locked && <p className="hint gate-hint">内容比较长，请先滑到「已经试过什么」的最后，按钮才能点。</p>}
        {can.has("ask") && (
          <div className="action">
            <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void ask()}>
              确认
            </button>
            <p className="hint">
              确认后，{b.need} 会收到通知「{me.me} 请您帮忙看 {b.id}」。不确认的话，对方不会被打扰。
            </p>
          </div>
        )}
        {can.has("help") && (
          <div className="action">
            <button type="button" className="btn btn-primary" disabled={locked || busy} onClick={() => void help()}>
              认领
            </button>
            <p className="hint">
              认领就是来帮忙：{raiser} 会收到通知「{me.me} 来帮忙看 {b.id} 了」，您的 agent 也能读到上面的详情。
            </p>
          </div>
        )}
        {can.has("resolve") && (
          <div className="action">
            <TextAction
              label="已解决"
              field="怎么解决的（必填）"
              hint="写一句是怎么解决的，以后谁再碰到能照着做。"
              required
              busy={busy}
              onSubmit={(body) => d.run("resolve", () => api.blockerAction(b.id, "resolve", { body }), "已标记为已解决。")}
            />
          </div>
        )}
        {can.has("forward") && (
          <ForwardBlock n={b.agent.unforwarded} content={b.agent.content} how={how} what="详情" busy={busy} onForward={() => void forward()} />
        )}
        {!["ask", "help", "resolve", "forward"].some((a) => can.has(a)) && <p className="muted">这个困难现在不需要您操作，可以评论。</p>}
      </section>

      <section className="block">
        <Notice msg={d.noticeFor("comment")} onClose={d.closeNotice} />
        {can.has("comment") && (
          <CommentBox busy={busy} onSubmit={(text) => d.run("comment", () => api.comment("blocker", b.id, text), "评论已发布。")} />
        )}
      </section>

      <div className="floating">
        <StaleBanner kind={d.stale} onShow={d.showLatest} />
      </div>
    </article>
  );
}

function needText(b: BlockerItem, me: string, mine: boolean): string {
  if (!b.need || b.need_state === "none") return "没有点名，谁都可以来帮忙";
  const who = person(b.need, me);
  if (b.need_state === "proposed") {
    const agent = b.t.client ? clientName(b.t.client) : "agent";
    return mine ? `您的 ${agent} 提议请${pad(who)}帮忙，等您确认` : `${b.t.by} 的 ${agent} 提议请${pad(who)}帮忙，等 ${b.t.by} 确认`;
  }
  return `已点名${pad(who)}`.trim();
}

import type { ReactNode } from "react";
import { api } from "../api";
import { useMe } from "../context";
import { usePoll, useTitle } from "../hooks";
import { authorOf, clientName, envAuthor, pad, person, stuckText, tidy } from "../labels";
import { Link } from "../router";
import type { Counts, Home as HomeData } from "../types";
import { Bits, LoadFail } from "./common";

function pathOf(id: string): string {
  return id.startsWith("B-") ? `/blocker?w=team&id=${id}` : `/task?w=team&id=${id}`;
}

/** 列表上的一行：上面是编号和标题，下面一行说明；右边只有「查看更多」（列表上不放「接受」）。 */
function Row({ id, title, line }: { id: string; title: string | undefined; line: ReactNode }) {
  return (
    <li className="row">
      <div className="row-main">
        <div className="row-title">
          <span className="row-id">{id}</span> {title ?? ""}
        </div>
        <div className="row-line">{typeof line === "string" ? tidy(line) : line}</div>
      </div>
      <Link className="more" to={pathOf(id)} aria-label={`查看更多：${id}`}>
        查看更多
      </Link>
    </li>
  );
}

export function Home() {
  const me = useMe();
  useTitle("首页");
  const { data: h, error } = usePoll(api.home, "home");
  if (!h) return <LoadFail error={error} />;

  const title = (id: string) => h.titles[id]?.t;
  const m = h.mine;
  const todoCount = m.to_accept.length + m.help_me.length + m.proposed.length + m.fwd.length + m.replies.length;

  return (
    <div className="page">
      {error && <p className="notice notice-error" role="alert">{error.message}</p>}
      <section className="block" aria-labelledby="h-mine">
        <h2 id="h-mine">待我处理{todoCount ? `（${todoCount}）` : ""}</h2>
        {todoCount === 0 ? (
          <p className="muted">现在没有要您处理的事。</p>
        ) : (
          <ul className="rows">
            {m.to_accept.map((r) => (
              <Row
                key={`a-${r.id}`}
                id={r.id}
                title={title(r.id)}
                line={`${authorOf(r.by, r.bk === "agent" ? "peer_agent" : "peer_human", r.client, me.me)} 请您协作，等您接受`}
              />
            ))}
            {m.help_me.map((r) => (
              <Row key={`h-${r.id}`} id={r.id} title={title(r.id)} line={`${r.by} 请您帮忙看看`} />
            ))}
            {m.proposed.map((r) => (
              <Row
                key={`p-${r.id}`}
                id={r.id}
                title={title(r.id)}
                line={`您的 ${clientName(r.client)} 想请${pad(person(r.h, me.me))}帮忙，等您确认`}
              />
            ))}
            {m.fwd.map((r) => (
              <Row
                key={`f-${r.id}`}
                id={r.id}
                title={title(r.id)}
                line={r.n === 1 ? `${r.by} 的 agent 写了 1 条评论，待您转发` : `有 ${r.n} 条别人的 agent 写的评论待您转发，最近一条是 ${r.by} 的 agent 写的`}
              />
            ))}
            {m.replies.map((r, i) => (
              <Row key={`r-${r.id}-${r.ev}-${i}`} id={r.id} title={title(r.id)} line={replyText(r.ev, r.by, r.id)} />
            ))}
          </ul>
        )}
      </section>

      <section className="block" aria-labelledby="h-blk">
        <h2 id="h-blk">困难{h.blockers.length ? `（${h.blockers.length}）` : ""}</h2>
        {h.blockers.length === 0 ? (
          <p className="muted">大家都没有卡住。</p>
        ) : (
          <ul className="rows">
            {h.blockers.map((b) => {
              const env = h.titles[b.id];
              const bits = [
                `${env ? envAuthor(env, me.me) : person(b.by, me.me)} 报告`,
                stuckText(b.stuck_min),
                b.need ? `已点名 ${person(b.need, me.me)}` : "",
                b.helper ? `${person(b.helper, me.me)} 在帮忙` : "还没有人认领",
                b.task ? `挂在 ${b.task}` : "",
              ].filter(Boolean);
              return <Row key={b.id} id={b.id} title={env?.t} line={<Bits bits={bits} />} />;
            })}
          </ul>
        )}
      </section>

      <section className="block" aria-labelledby="h-doing">
        <h2 id="h-doing">大家在做什么</h2>
        {h.doing.length === 0 ? (
          <p className="muted">现在没有进行中的任务。</p>
        ) : (
          <ul className="rows">
            {h.doing.map((r) => {
              const bits = [person(r.h, me.me)];
              if (r.sess && r.sess.length) {
                bits.push(clientName(r.sess[0]?.client));
                bits.push(r.sess.map((s) => `会话 ${s.s}`).join("、"));
              } else if (r.client) {
                bits.push(clientName(r.client));
              }
              bits.push(`在做 ${r.id}`);
              if (r.today) bits.push("今天有更新");
              return <Row key={`d-${r.id}`} id={r.id} title={title(r.id)} line={<Bits bits={bits} />} />;
            })}
          </ul>
        )}
      </section>

      <section className="block" aria-labelledby="h-count">
        <h2 id="h-count">项目</h2>
        <table className="counts">
          <thead>
            <tr>
              <th scope="col">项目</th>
              <th scope="col">待认领</th>
              <th scope="col">待接受</th>
              <th scope="col">待开始</th>
              <th scope="col">进行中</th>
              <th scope="col">困难</th>
            </tr>
          </thead>
          <tbody>
            <CountRow name="全队" counts={h.counts} />
            {h.projects.map((p) => (
              <CountRow key={p.key} name={p.name} counts={p.counts} project={p.key} />
            ))}
          </tbody>
        </table>
        <p className="hint">点数字可以看对应的任务。</p>
      </section>
    </div>
  );
}

function replyText(ev: string, by: string, id: string): string {
  if (ev === "accepted") return `${by} 接受了 ${id}`;
  if (ev === "declined") return `${by} 没接 ${id}`;
  if (ev === "done") return `${by} 完成了 ${id}`;
  return `${by} 回复了 ${id}`;
}

function CountRow({ name, counts, project }: { name: string; counts: Counts; project?: string }) {
  const q = project ? `&project=${encodeURIComponent(project)}` : "";
  return (
    <tr>
      <th scope="row">{name}</th>
      <td>
        <Link to={`/tasks?view=pool${q}`}>{counts.pool}</Link>
      </td>
      <td>
        <Link to={`/tasks?view=all${q}`}>{counts.pending}</Link>
      </td>
      <td>
        <Link to={`/tasks?view=all${q}`}>{counts.todo}</Link>
      </td>
      <td>
        <Link to={`/tasks?view=doing${q}`}>{counts.doing}</Link>
      </td>
      <td>{counts.blockers}</td>
    </tr>
  );
}

export type { HomeData };

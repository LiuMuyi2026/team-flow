import { useEffect, useState } from "react";
import { api, messageOf } from "../api";
import { projectName, useMe } from "../context";
import { usePoll, useTitle } from "../hooks";
import { envAuthor, person, tidy } from "../labels";
import { Link, navigate } from "../router";
import type { TaskRow, TaskView } from "../types";
import { Bits, LoadFail } from "./common";

const TABS: { view: TaskView; text: string; empty: string }[] = [
  { view: "pool", text: "待认领", empty: "现在没有待认领的任务。" },
  { view: "doing", text: "进行中", empty: "现在没有进行中的任务。" },
  { view: "mine", text: "我的", empty: "您负责的、您发布的任务都结束了。" },
  { view: "all", text: "全部", empty: "还没有任务。" },
];

function isView(v: string | null): v is TaskView {
  return v === "pool" || v === "doing" || v === "mine" || v === "all" || v === "done";
}

export function Tasks({ query }: { query: URLSearchParams }) {
  const me = useMe();
  const raw = query.get("view");
  const view: TaskView = isView(raw) ? raw : "pool";
  const project = query.get("project") ?? "";
  const tab = TABS.find((t) => t.view === view) ?? { view, text: "已完成", empty: "还没有完成的任务。" };
  useTitle(`任务 · ${tab.text}`);

  const key = `${view}:${project}`;
  const { data, error } = usePoll(() => api.tasks(view, { project: project || undefined }), `tasks:${key}`);
  // 「加载更多」拿到的后几页：30 秒刷新只刷第一页，已经加载的后几页留着（换页签才清掉）
  const [extra, setExtra] = useState<{ key: string; rows: TaskRow[]; next: string | null }>({ key, rows: [], next: null });
  const [moreErr, setMoreErr] = useState("");
  const [loadingMore, setLoadingMore] = useState(false);
  const mine = extra.key === key && extra.rows.length > 0 ? extra : null;
  const next = mine ? mine.next : (data?.next ?? null);

  useEffect(() => {
    setMoreErr("");
  }, [key]);

  const loadMore = async () => {
    if (!next) return;
    setLoadingMore(true);
    setMoreErr("");
    try {
      const page = await api.tasks(view, { project: project || undefined, cursor: next });
      setExtra((x) => ({ key, rows: [...(x.key === key ? x.rows : []), ...page.rows], next: page.next }));
    } catch (e) {
      setMoreErr(messageOf(e));
    } finally {
      setLoadingMore(false);
    }
  };

  const rows: TaskRow[] = [];
  const seen = new Set<string>();
  for (const r of [...(data?.rows ?? []), ...(mine?.rows ?? [])]) {
    if (!seen.has(r.id)) {
      seen.add(r.id);
      rows.push(r);
    }
  }
  const q = project ? `&project=${encodeURIComponent(project)}` : "";

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">任务</h1>
        <Link className="btn btn-primary btn-small" to="/new">
          发布
        </Link>
      </div>
      <nav className="tabs" aria-label="任务分类">
        {TABS.map((t) => (
          <Link key={t.view} to={`/tasks?view=${t.view}${q}`} className="tab" aria-current={t.view === view ? "page" : undefined}>
            {t.text}
          </Link>
        ))}
      </nav>
      {project && (
        <p className="filter">
          只看「{projectName(me, project)}」项目。
          <button type="button" className="link-btn" onClick={() => navigate(`/tasks?view=${view}`)}>
            看全部项目
          </button>
        </p>
      )}
      {!data ? (
        <LoadFail error={error} />
      ) : rows.length === 0 ? (
        <p className="muted empty-line">{tab.empty}</p>
      ) : (
        <ul className="rows">
          {rows.map((r) => {
            const bits = [`${envAuthor(r.t, me.me)} 发布`, r.st_text];
            if (r.who) bits.push(tidy(`${person(r.who, me.me)} 负责`));
            if (r.blk?.length) bits.push(`卡在 ${r.blk.join("、")}`);
            bits.push(r.upd);
            return (
              <li key={r.id} className="row">
                <div className="row-main">
                  <div className="row-title">
                    <span className="row-id">{r.id}</span> {r.t.t}
                  </div>
                  <div className="row-line">
                    <Bits bits={bits} />
                  </div>
                </div>
                <Link className="more" to={r.path} aria-label={`查看更多：${r.id}`}>
                  查看更多
                </Link>
              </li>
            );
          })}
        </ul>
      )}
      {error && data && <p className="notice notice-error" role="alert">{error.message}</p>}
      {next && (
        <div className="btn-row center">
          <button type="button" className="btn" disabled={loadingMore} onClick={() => void loadMore()}>
            {loadingMore ? "正在加载…" : "加载更多"}
          </button>
        </div>
      )}
      {moreErr && <p className="notice notice-error" role="alert">{moreErr}</p>}
    </div>
  );
}

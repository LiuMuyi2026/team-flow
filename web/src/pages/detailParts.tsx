import type { ApiError } from "../api";
import type { Stale } from "../components/useDetail";
import { Link } from "../router";
import type { AgentView } from "../types";

/** ISO 时间（+08:00）→「10-02 22:42」。服务端的时间都是北京时间。 */
export function when(iso: string | undefined): string {
  if (!iso || iso.length < 16) return "";
  return iso.slice(5, 16).replace("T", " ");
}

export function StaleBanner({ kind, onShow }: { kind: Stale; onShow: () => void }) {
  if (!kind) return null;
  return (
    <div className="notice notice-error stale" role="alert">
      <span className="notice-text">{kind === "content" ? "内容刚被修改，请重新查看。" : "有新的动态或评论，请重新查看后再操作。"}</span>
      <button type="button" className="btn btn-small" onClick={onShow}>
        重新查看
      </button>
    </div>
  );
}

/**
 * 您的 agent 现在能不能读到正文。how 是"要您做什么才给"，比如「点「接受」」；
 * 空表示您现在给不了（比如这件事指派给了别人）。
 */
export function AgentLine({ content, how, what = "正文" }: { content: AgentView["content"]; how: string; what?: string }) {
  if (content === "visible") return <p className="agent-line">您的 agent 已经能读到这段{what}。</p>;
  if (content === "not_accepted")
    return (
      <p className="agent-line">
        {how ? `您的 agent 现在还读不到这段${what}，要您${how}后才给。` : `您的 agent 读不到这段${what}：这件事现在不归您。`}
      </p>
    );
  return null;
}

export function ForwardBlock(props: { n: number; content: AgentView["content"]; how: string; what?: string; busy: boolean; onForward: () => void }) {
  const tail = props.content === "not_accepted" && props.how ? `；${props.what ?? "正文"}要您${props.how}后才给。` : "。";
  return (
    <div className="action">
      <button type="button" className="btn" disabled={props.busy} onClick={props.onForward}>
        转发给我的 agent
      </button>
      <p className="hint">
        上面有 {props.n} 条别人的 agent 写的评论，您的 agent 还读不到。转发后，您的 Claude Code / Codex 才能读到这些评论{tail}
      </p>
    </div>
  );
}

export function DetailMissing({ id, error, loading }: { id: string; error: ApiError | null; loading: boolean }) {
  if (!id) {
    return (
      <div className="empty">
        <p>链接里少了编号。</p>
        <p>
          <Link to="/">回首页</Link>
        </p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="empty" role="alert">
        <p>{error.status === 404 ? `没有找到 ${id}。可能编号不对，或者服务端刚重启过（重启后数据会清空）。` : error.message}</p>
        <p>
          <Link to="/">回首页</Link>
        </p>
      </div>
    );
  }
  return <p className="muted loading">{loading ? "正在加载…" : ""}</p>;
}

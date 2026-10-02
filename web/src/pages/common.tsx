import type { ApiError } from "../api";
import { tidy } from "../labels";

/** 列表页第一次加载：失败时说人话，成功前显示"正在加载"。 */
export function LoadFail({ error }: { error: ApiError | null }) {
  if (error) {
    return (
      <div className="empty" role="alert">
        <p>{error.message}</p>
      </div>
    );
  }
  return <p className="muted loading">正在加载…</p>;
}

/** 「bob 的 Codex 发布 · 待认领 · 10-03 01:26」：每一段不在中间折行，只在「·」处换行。 */
export function Bits({ bits }: { bits: string[] }) {
  return (
    <>
      {bits.map((b, i) => (
        <span key={i}>
          {i > 0 ? " · " : ""}
          <span className="bit">{tidy(b)}</span>
        </span>
      ))}
    </>
  );
}

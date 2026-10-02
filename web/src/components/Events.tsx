import { evAuthor, trustText } from "../labels";
import type { Ev } from "../types";
import { RiskText } from "./RiskText";

/** 全部动态和评论（旧的在前），每条标作者和作者类别；有文字的标出您的 agent 能不能读到。 */
export function Events({ ev, me }: { ev: Ev[]; me: string }) {
  if (!ev.length) return <p className="muted">还没有动态。</p>;
  return (
    <ol className="events">
      {ev.map((e) => {
        const who = evAuthor(e, me);
        const hasText = typeof e.t === "string";
        return (
          <li key={e.e} className={hasText ? "ev ev-text" : "ev"}>
            <div className="ev-head">
              <span>
                <strong>{who}</strong>
                {/[A-Za-z0-9]$/.test(who) ? " " : ""}
                {e.what}
              </span>
              <span className="ev-at">{e.at}</span>
            </div>
            {hasText && (
              <>
                <div className="ev-kind">{trustText(e.trust)}</div>
                <p className="text">
                  <RiskText text={e.t ?? ""} />
                </p>
                {e.agent === false && e.by !== me && <p className="ev-gate">您的 agent 还读不到这条。</p>}
              </>
            )}
          </li>
        );
      })}
    </ol>
  );
}

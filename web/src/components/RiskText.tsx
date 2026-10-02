import { Fragment, useMemo } from "react";
import { segments } from "../risk";

/** 纯文本 + 风险高亮。文字由 React 转义输出，绝不当 HTML。 */
export function RiskText({ text }: { text: string }) {
  const segs = useMemo(() => segments(text), [text]);
  return (
    <>
      {segs.map((s, i) =>
        s.risk.length ? (
          <mark key={i} className="risk" title={`请留意：${s.risk.join("、")}`}>
            {s.text}
          </mark>
        ) : (
          <Fragment key={i}>{s.text}</Fragment>
        ),
      )}
    </>
  );
}

export function RiskNote({ kinds }: { kinds: string[] }) {
  if (!kinds.length) return null;
  return (
    <p className="risk-note" role="note">
      请留意，这段文字里有：{kinds.join("、")}。标出来的地方请看仔细，确认是您想让 agent 做的事，再接受或转发。
    </p>
  );
}

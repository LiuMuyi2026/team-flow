import { useEffect } from "react";
import { tidy } from "../labels";

export type NoticeKind = "error" | "ok" | "info";

export interface NoticeMsg {
  kind: NoticeKind;
  text: string;
  /** 由哪个按钮引起的（详情页按它决定提示放在哪儿：评论框旁边还是操作区） */
  from?: string;
  /** 内容被改了（409）：提示里带一个「回到正文」 */
  conflict?: boolean;
}

/** 一行提示。错误用 role=alert，读屏会立刻念出来；成功的提示 6 秒后自己收起。 */
export function Notice({ msg, onClose, onBack }: { msg: NoticeMsg | null; onClose?: () => void; onBack?: () => void }) {
  useEffect(() => {
    if (!msg || msg.kind !== "ok" || !onClose) return;
    const t = window.setTimeout(onClose, 6000);
    return () => window.clearTimeout(t);
  }, [msg, onClose]);
  if (!msg) return null;
  return (
    <div className={`notice notice-${msg.kind}`} role={msg.kind === "error" ? "alert" : "status"}>
      <span className="notice-text">{tidy(msg.text)}</span>
      <span className="notice-btns">
        {msg.conflict && onBack && (
          <button type="button" className="link-btn" onClick={onBack}>
            回到正文
          </button>
        )}
        {onClose && (
          <button type="button" className="link-btn" onClick={onClose}>
            关闭
          </button>
        )}
      </span>
    </div>
  );
}

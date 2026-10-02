import { useEffect } from "react";
import { api } from "../api";
import { useMe } from "../context";
import { usePoll, useTitle } from "../hooks";
import { Link } from "../router";
import { markSeen } from "../unread";
import { LoadFail } from "./common";

export function Notifications() {
  const me = useMe();
  useTitle("模拟通知");
  const { data, error } = usePoll(() => api.notifications(50), "notifications");

  useEffect(() => {
    if (data) markSeen(me.me, data.items[0]?.n ?? 0);
  }, [data, me.me]);

  return (
    <div className="page">
      <h1 className="page-title">模拟通知</h1>
      <p className="trial-note">本地试用：这里代替真正的通知。</p>
      <p className="hint">
        正式版会按您选的渠道（邮件或微信）把下面这些通知发给您（{me.me}）。通知只是提醒，接受、认领这些事还是在 Team Flow 网页上做。点「详情」打开对应的页面；这里每 30 秒刷新一次，新的在上面。
      </p>
      {!data ? (
        <LoadFail error={error} />
      ) : data.items.length === 0 ? (
        <p className="muted empty-line">还没有发给您的通知。</p>
      ) : (
        <ol className="ntf-list">
          {data.items.map((it) => (
            <li key={it.n} className="ntf">
              <div className="ntf-head">
                <strong>{it.kind_text}</strong>
                <span className="ntf-at">{it.at ?? ""}</span>
              </div>
              <p className="ntf-text">{it.text}</p>
              {it.path && (
                <div className="ntf-foot">
                  <span className="ntf-path">点开后：{it.path}</span>
                  <Link className="more" to={it.path}>
                    详情
                  </Link>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
      {error && data && <p className="notice notice-error" role="alert">{error.message}</p>}
    </div>
  );
}

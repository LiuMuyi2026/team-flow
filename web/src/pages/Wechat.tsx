import { useEffect } from "react";
import { api } from "../api";
import { useMe } from "../context";
import { usePoll, useTitle } from "../hooks";
import { Link } from "../router";
import { markSeen } from "../unread";
import { LoadFail } from "./common";

export function Wechat() {
  const me = useMe();
  useTitle("模拟微信");
  const { data, error } = usePoll(() => api.wechat(50), "wechat");

  useEffect(() => {
    if (data) markSeen(me.me, data.items[0]?.n ?? 0);
  }, [data, me.me]);

  return (
    <div className="page">
      <h1 className="page-title">模拟微信</h1>
      <p className="trial-note">本地试用：这里代替微信通知。</p>
      <p className="hint">
        正式版里，下面这些消息会发到您（{me.me}）的手机微信，点消息里的「详情」就打开对应的页面。这里每 30 秒刷新一次，新的在上面。
      </p>
      {!data ? (
        <LoadFail error={error} />
      ) : data.items.length === 0 ? (
        <p className="muted empty-line">还没有发给您的消息。</p>
      ) : (
        <ol className="wx-list">
          {data.items.map((it) => (
            <li key={it.n} className="wx">
              <div className="wx-head">
                <strong>{it.kind_text}</strong>
                <span className="wx-at">{it.at ?? ""}</span>
              </div>
              <p className="wx-text">{it.text}</p>
              {it.path && (
                <div className="wx-foot">
                  <span className="wx-path">点开后：{it.path}</span>
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

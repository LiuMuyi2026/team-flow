import { useCallback, useEffect, useState } from "react";
import { api, ApiError, messageOf, onAuthLost, setCsrf } from "./api";
import { MeContext } from "./context";
import { POLL_MS, useTitle } from "./hooks";
import { BlockerDetail } from "./pages/BlockerDetail";
import { Home } from "./pages/Home";
import { NewTask } from "./pages/NewTask";
import { TaskDetail } from "./pages/TaskDetail";
import { Tasks } from "./pages/Tasks";
import { Wechat } from "./pages/Wechat";
import { Link, navigate, useLocation } from "./router";
import type { Me } from "./types";
import { markSeen, seen } from "./unread";

type Auth =
  | { s: "loading" }
  | { s: "in"; me: Me }
  | { s: "out"; why: "none" | "expired" | "bye" }
  | { s: "off" }
  | { s: "down"; text: string };

export function App() {
  const [auth, setAuth] = useState<Auth>({ s: "loading" });

  const load = useCallback(async () => {
    try {
      const me = await api.me();
      setCsrf(me.csrf);
      setAuth({ s: "in", me });
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setAuth({ s: "out", why: "none" });
      else if (e instanceof ApiError && e.status === 404) setAuth({ s: "off" });
      else setAuth({ s: "down", text: messageOf(e) });
    }
  }, []);

  useEffect(() => {
    void load();
    onAuthLost(() => setAuth((a) => (a.s === "in" ? { s: "out", why: "expired" } : a)));
    return () => onAuthLost(null);
  }, [load]);

  if (auth.s === "loading") return <Shell>{<p className="muted loading">正在加载…</p>}</Shell>;
  if (auth.s === "out") return <Shell>{<LoggedOut why={auth.why} />}</Shell>;
  if (auth.s === "off") return <Shell>{<DevOff />}</Shell>;
  if (auth.s === "down")
    return (
      <Shell>
        <div className="empty" role="alert">
          <p>{auth.text}</p>
          <button type="button" className="btn" onClick={() => void load()}>
            重试
          </button>
        </div>
      </Shell>
    );

  const logout = async () => {
    try {
      await api.logout();
    } catch {
      // 会话已经没了也算登出
    }
    setAuth({ s: "out", why: "bye" });
    navigate("/", { replace: true });
  };

  return (
    <MeContext.Provider value={auth.me}>
      <Shell me={auth.me} onLogout={() => void logout()}>
        <Routes />
      </Shell>
    </MeContext.Provider>
  );
}

function Shell({ me, onLogout, children }: { me?: Me; onLogout?: () => void; children: React.ReactNode }) {
  return (
    <div className="app">
      <header className="top">
        <div className="top-line">
          <Link to="/" className="brand">
            Team Flow
          </Link>
          <span className="trial-mark">本地试用</span>
        </div>
        {me && (
          <>
            <div className="who">
              <Link to="/me" className="who-text">
                您现在是 <strong>{me.me}</strong>
                {me.name && me.name !== me.me ? `（${me.name}）` : ""}
              </Link>
              <button type="button" className="link-btn" onClick={onLogout}>
                登出
              </button>
            </div>
            <Nav me={me.me} />
          </>
        )}
      </header>
      <main className="main">{children}</main>
    </div>
  );
}

function Nav({ me }: { me: string }) {
  const loc = useLocation();
  const unread = useUnread(me);
  const items: { to: string; text: string; on: boolean }[] = [
    { to: "/", text: "首页", on: loc.path === "/" },
    { to: "/tasks", text: "任务", on: loc.path === "/tasks" || loc.path === "/task" },
    { to: "/new", text: "发布", on: loc.path === "/new" },
    { to: "/wechat", text: unread ? `模拟微信（${unread}）` : "模拟微信", on: loc.path === "/wechat" },
  ];
  return (
    <nav className="nav" aria-label="页面">
      {items.map((it) => (
        <Link
          key={it.to}
          to={it.to}
          className="nav-item"
          aria-current={it.on ? "page" : undefined}
          aria-label={it.to === "/wechat" && unread ? `模拟微信，${unread} 条新消息` : undefined}
        >
          {it.text}
        </Link>
      ))}
    </nav>
  );
}

/** 「模拟微信」有几条新消息：每 30 秒看一次（正式版里这是手机上的微信提醒）。 */
function useUnread(me: string): number {
  const [n, setN] = useState(0);
  const loc = useLocation();
  useEffect(() => {
    let alive = true;
    const check = async () => {
      if (document.hidden) return;
      try {
        const w = await api.wechat(50);
        const last = w.items[0]?.n ?? 0;
        let s = seen(me);
        if (last < s) {
          // 服务端重启过（通知编号从头开始）：从现在算起
          markSeen(me, 0, true);
          s = 0;
        }
        if (alive) setN(w.items.filter((i) => i.n > s).length);
      } catch {
        // 未读数只是提示，失败不打扰
      }
    };
    void check();
    const t = window.setInterval(() => void check(), POLL_MS);
    const onSeen = () => void check();
    window.addEventListener("tf-wx-seen", onSeen);
    document.addEventListener("visibilitychange", onSeen);
    return () => {
      alive = false;
      window.clearInterval(t);
      window.removeEventListener("tf-wx-seen", onSeen);
      document.removeEventListener("visibilitychange", onSeen);
    };
  }, [me, loc.path]);
  return n;
}

function Routes() {
  const loc = useLocation();
  const id = (loc.query.get("id") ?? "").trim().toUpperCase();
  switch (loc.path) {
    case "/":
      return <Home />;
    case "/tasks":
      return <Tasks query={loc.query} />;
    case "/task":
      return <TaskDetail key={id} id={id} />;
    case "/blocker":
      return <BlockerDetail key={id} id={id} />;
    case "/new":
      return <NewTask />;
    case "/wechat":
      return <Wechat />;
    case "/me":
      return <MePage />;
    default:
      return <NotFound />;
  }
}

function MePage() {
  useTitle("我");
  return (
    <MeContext.Consumer>
      {(me) =>
        me && (
          <div className="page">
            <h1 className="page-title">我</h1>
            <dl className="facts">
              <dt>身份</dt>
              <dd>
                {me.me}
                {me.name && me.name !== me.me ? `（${me.name}）` : ""}
              </dd>
              <dt>登录到期</dt>
              <dd>{me.expires.slice(5, 16).replace("T", " ")}（12 小时）</dd>
            </dl>
            <SwitchHelp example={me.members.find((m) => m.h !== me.me)?.h} />
          </div>
        )
      }
    </MeContext.Consumer>
  );
}

function SwitchHelp({ example = "bob" }: { example?: string }) {
  return (
    <div className="help">
      <p>想换成队友的身份（以 {example} 为例），在您自己的终端运行：</p>
      <pre className="cmd">scripts/login-link.sh {example}</pre>
      <p>
        您本人的链接用 127.0.0.1，队友的用 localhost：同一个浏览器里这两个地址的登录互不影响，开两个标签页就能同时当两个人。第三个人请用无痕窗口或另一个浏览器。
      </p>
    </div>
  );
}

function LoggedOut({ why }: { why: "none" | "expired" | "bye" }) {
  useTitle("请登录");
  const head = why === "bye" ? "您已经登出。" : why === "expired" ? "登录已过期，或者服务端刚重启过。" : "您还没登录。";
  return (
    <div className="page login-help">
      <h1 className="page-title">{head}</h1>
      <p>本地试用里，这个网页扮演“手机上的您”：接受、认领、转发这些只有您本人能做的事，在这里点。</p>
      <p>请在您自己的终端（不要让 agent 替您运行）里运行：</p>
      <pre className="cmd">scripts/login-link.sh</pre>
      <p>打开它给出的链接，点「登录」。链接 10 分钟内有效，只能用一次。</p>
      <p className="hint">没用 scripts/local-up.sh 启动的话，运行下面这条（TEAMFLOW_STATE 要和服务端一致）：</p>
      <pre className="cmd">python -m teamflow_server.devlogin --as &lt;handle&gt;</pre>
      <SwitchHelp />
    </div>
  );
}

function DevOff() {
  useTitle("本地试用没有打开");
  return (
    <div className="page login-help">
      <h1 className="page-title">本地试用没有打开</h1>
      <p>这个网页只在本地试用模式下能用。请确认：</p>
      <ul className="plain">
        <li>服务端是用 scripts/local-up.sh 启动的（或者设了 TEAMFLOW_DEV_ENDPOINTS=1）；</li>
        <li>地址栏是 127.0.0.1 或 localhost，不是局域网 IP，也没有经过反向代理。</li>
      </ul>
    </div>
  );
}

function NotFound() {
  useTitle("没有这个页面");
  return (
    <div className="empty">
      <p>没有这个页面。</p>
      <p>
        <Link to="/">回首页</Link>
      </p>
    </div>
  );
}

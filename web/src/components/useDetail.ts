import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, CONFLICT_TEXT, messageOf } from "../api";
import { usePoll } from "../hooks";
import type { Item, PageVals } from "../types";
import type { NoticeMsg } from "./Notice";

export function sameVersion(a: PageVals, b: PageVals): boolean {
  return a.v === b.v && a.sha === b.sha && (a.seq ?? null) === (b.seq ?? null);
}

/** 轮询拿到的和正在显示的比：content = 正文或指派变了；events = 有新动态（比如对方 agent 刚写的评论）。 */
export type Stale = null | "content" | "events";

export function staleKind(shown: PageVals, latest: PageVals): Stale {
  if (!sameVersion(shown, latest)) return "content";
  if (shown.through !== latest.through) return "events";
  return null;
}

/**
 * 详情页的数据：每 30 秒刷新一次，但**不偷偷换掉正在看的东西**。
 * 按钮带的 v、sha、seq、through 必须是页面上显示的那份（plan 7.2、H3）：
 * - 正文或指派变了：提示"内容刚被修改，请重新查看"，等人点「重新查看」。这时按钮照样带旧值，服务端返回 409。
 * - 有新动态：提示"有新的动态，请重新查看"。不自动并进来，否则对方 agent 在您点「接受」前一刻写的评论，
 *   会因为刚好被轮询画到页面上而算作"您已看过"，随接受一起放给您的 agent。
 * - 都没变：换上新数据（按钮提示 can 之类可能变了）。
 * 自己点完按钮之后的刷新直接换上新数据。
 */
export function useDetail<T extends Item>(kind: "task" | "blocker", id: string) {
  const polled = usePoll<T>(() => (kind === "task" ? api.task(id) : api.blocker(id)) as Promise<T>, `${kind}:${id}`);
  const [item, setItem] = useState<T | null>(null);
  const [stale, setStale] = useState<Stale>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<NoticeMsg | null>(null);
  const shown = useRef<T | null>(null);

  useEffect(() => {
    shown.current = null;
    setItem(null);
    setStale(null);
    setNotice(null);
  }, [kind, id]);

  useEffect(() => {
    const d = polled.data;
    if (!d) return;
    const prev = shown.current;
    const kind = prev && prev.id === d.id ? staleKind(prev.page, d.page) : null;
    if (kind === null) {
      shown.current = d;
      setItem(d);
    }
    setStale(kind);
  }, [polled.data]);

  const { reload } = polled;
  const refresh = useCallback(async () => {
    const d = await reload(true);
    if (d) {
      shown.current = d;
      setItem(d);
      setStale(null);
    }
  }, [reload]);

  const showLatest = useCallback(() => {
    void refresh().then(() => window.scrollTo(0, 0));
  }, [refresh]);

  /** 点按钮：成功提示 ok；409 一律提示后重新拉详情；其他错误照服务端的人话提示。 */
  const run = useCallback(
    async (name: string, fn: () => Promise<unknown>, ok: string): Promise<boolean> => {
      setBusy(name);
      setNotice(null);
      try {
        await fn();
        setNotice({ kind: "ok", text: ok, from: name });
        await refresh();
        return true;
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          setNotice({ kind: "error", text: e.isConflict ? CONFLICT_TEXT : e.message, from: name, conflict: e.isConflict });
          await refresh();
        } else {
          setNotice({ kind: "error", text: messageOf(e), from: name });
        }
        return false;
      } finally {
        setBusy(null);
      }
    },
    [refresh],
  );

  const closeNotice = useCallback(() => setNotice(null), []);
  const backToContent = useCallback(() => {
    document.getElementById("sec-content")?.scrollIntoView({ block: "start" });
  }, []);
  const noticeFor = (place: "actions" | "comment"): NoticeMsg | null => {
    if (!notice) return null;
    return (notice.from === "comment") === (place === "comment") ? notice : null;
  };

  return { item, stale, busy, notice, noticeFor, closeNotice, backToContent, refresh, showLatest, run, error: polled.error, loading: polled.loading };
}

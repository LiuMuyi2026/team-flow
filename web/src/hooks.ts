import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "./api";

export const POLL_MS = 30_000;

export interface Polled<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  /** 立刻重新拉一次；quiet=true 时不清掉已有数据、不显示"正在加载" */
  reload: (quiet?: boolean) => Promise<T | null>;
}

/** 拉一次数据，之后每 30 秒刷新（页面在后台时暂停，回到前台立刻刷新一次）。 */
export function usePoll<T>(load: () => Promise<T>, key: string, interval: number = POLL_MS): Polled<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const loadRef = useRef(load);
  loadRef.current = load;
  const gen = useRef(0);

  const reload = useCallback(async (quiet = false): Promise<T | null> => {
    const my = ++gen.current;
    if (!quiet) setLoading(true);
    try {
      const d = await loadRef.current();
      if (my === gen.current) {
        setData(d);
        setError(null);
      }
      return d;
    } catch (e) {
      if (my === gen.current) {
        setError(e instanceof ApiError ? e : new ApiError(0, "unknown", "出了点问题，请刷新后再试。"));
      }
      return null;
    } finally {
      if (my === gen.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    setData(null);
    setError(null);
    void reload();
    const tick = () => {
      if (!document.hidden) void reload(true);
    };
    const timer = window.setInterval(tick, interval);
    document.addEventListener("visibilitychange", tick);
    return () => {
      gen.current++;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [key, interval, reload]);

  return { data, error, loading, reload };
}

/** 设置页面标题：「T-52 支付回调重试 · Team Flow」。 */
export function useTitle(title: string): void {
  useEffect(() => {
    document.title = title ? `${title} · Team Flow` : "Team Flow";
  }, [title]);
}

// 极简路由：查询参数路由（plan 7.1、4.3），/task?w=team&id=T-42 这类链接原样可用。
import { createElement, useSyncExternalStore, type AnchorHTMLAttributes, type MouseEvent } from "react";

const listeners = new Set<() => void>();

function emit(): void {
  for (const fn of listeners) fn();
}

function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  window.addEventListener("popstate", fn);
  return () => {
    listeners.delete(fn);
    window.removeEventListener("popstate", fn);
  };
}

function snapshot(): string {
  return window.location.pathname + window.location.search;
}

export interface Loc {
  path: string;
  query: URLSearchParams;
  href: string;
}

export function useLocation(): Loc {
  const href = useSyncExternalStore(subscribe, snapshot, snapshot);
  const i = href.indexOf("?");
  const path = i < 0 ? href : href.slice(0, i);
  return { path: path.replace(/\/+$/, "") || "/", query: new URLSearchParams(i < 0 ? "" : href.slice(i + 1)), href };
}

/** 只接受站内相对路径（以单个 / 开头）。 */
export function isInternal(to: string): boolean {
  return to.startsWith("/") && !to.startsWith("//") && !to.startsWith("/\\");
}

export function navigate(to: string, opts: { replace?: boolean } = {}): void {
  if (!isInternal(to)) return;
  if (to === snapshot()) {
    emit();
    return;
  }
  if (opts.replace) window.history.replaceState(null, "", to);
  else window.history.pushState(null, "", to);
  window.scrollTo(0, 0);
  emit();
}

type LinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & { to: string };

export function Link({ to, onClick, ...rest }: LinkProps) {
  const handle = (e: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e);
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (!isInternal(to)) return;
    e.preventDefault();
    navigate(to);
  };
  return createElement("a", { ...rest, href: isInternal(to) ? to : "/", onClick: handle });
}

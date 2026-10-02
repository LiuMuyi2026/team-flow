import { useEffect, useRef, useState } from "react";

export const LONG_BODY = 800;

/**
 * 防误点（plan 7.1）：正文超过 800 字时，滚到正文最后，按钮才能点。
 * 返回放在正文末尾的标记 ref 和"是否已经看到底"。resetKey 是内容的版本：换了版本要重新看到底。
 */
export function useReadToEnd(active: boolean, resetKey: string) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [seenKey, setSeenKey] = useState<string | null>(null);
  const seen = !active || seenKey === resetKey;

  useEffect(() => {
    if (seen) return;
    const el = ref.current;
    if (!el) return;
    const done = () => setSeenKey(resetKey);
    if (typeof IntersectionObserver !== "undefined") {
      const io = new IntersectionObserver((entries) => {
        if (entries.some((x) => x.isIntersecting)) done();
      });
      io.observe(el);
      return () => io.disconnect();
    }
    const check = () => {
      if (el.getBoundingClientRect().top <= window.innerHeight) done();
    };
    check();
    window.addEventListener("scroll", check, { passive: true });
    return () => window.removeEventListener("scroll", check);
  }, [seen, resetKey]);

  return { ref, seen };
}

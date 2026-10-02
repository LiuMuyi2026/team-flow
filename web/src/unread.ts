// 「模拟微信」的未读数：只是本浏览器里记一下看到的最新编号，读写失败就当没有。
const KEY = (h: string) => `tf_wx_seen:${h}`;

export function seen(handle: string): number {
  try {
    return Number(window.localStorage.getItem(KEY(handle)) ?? "0") || 0;
  } catch {
    return 0;
  }
}

/** 记下看到的最新编号；force=true 时可以往回改（服务端重启后编号从头开始）。 */
export function markSeen(handle: string, n: number, force = false): void {
  try {
    if (force || n > seen(handle)) window.localStorage.setItem(KEY(handle), String(n));
    window.dispatchEvent(new Event("tf-wx-seen"));
  } catch {
    // 私密窗口等读写不了 localStorage：不影响使用
  }
}

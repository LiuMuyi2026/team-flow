import { createContext, useContext } from "react";
import type { Me } from "./types";

export const MeContext = createContext<Me | null>(null);

export function useMe(): Me {
  const me = useContext(MeContext);
  if (!me) throw new Error("useMe 只能在登录后的页面里用");
  return me;
}

/** 项目名：pay → 支付 */
export function projectName(me: Me, key: string | undefined | null): string {
  if (!key) return "";
  return me.projects.find((p) => p.key === key)?.name ?? key;
}

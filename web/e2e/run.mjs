#!/usr/bin/env node
// 端到端：起一个本地开发模式的服务端，用 Chromium 以 iPhone 尺寸把典型场景走一遍。
//
//   npm run e2e      只跑断言
//   npm run shots    另外逐页截图到 docs/local-trial-shots/，并检查文字截断、横向溢出、按钮能不能点
//
// 端口用 TF_E2E_PORT（缺省 8302）；端口被占用就退出，不碰别人的进程。服务端是本脚本自己起的子进程，结束时只关它。
// 令牌、登录码都在运行时随机生成；登录码直接调 teamflow_server.devlogin.issue（测试代替"您自己的终端"）。

import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, devices } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, "../..");
const PORT = process.env.TF_E2E_PORT ?? "8302";
const BASE = `http://127.0.0.1:${PORT}`;
const PY =
  process.env.TF_PY ?? [join(repo, ".venv/bin/python"), join(repo, ".local/venv/bin/python")].find((p) => existsSync(p));
const SHOTS = process.argv.includes("--shots");
const SHOT_DIR = join(repo, "docs/local-trial-shots");
const DEVICE = { ...devices["iPhone 13"], deviceScaleFactor: 2 };

if (!PY) {
  console.error("找不到装了服务端的 Python：先建 .venv 或运行 scripts/local-up.sh，或者用 TF_PY 指定。");
  process.exit(2);
}

const results = [];
const issues = [];
const shots = [];
let shotNo = 0;
const shotFile = (name) => `${String(shotNo++).padStart(2, "0")}-${name}.png`;

function ok(name) {
  results.push(name);
  console.log(`  通过  ${name}`);
}

// ---------------------------------------------------------------------------
// 服务端
// ---------------------------------------------------------------------------

const pat = () => "tf_pat_" + randomBytes(16).toString("hex"); // 运行时拼出来的样本，不是真令牌
const TOK = { alice: pat(), bob: pat(), carol: pat() };
const state = mkdtempSync(join(tmpdir(), "tf-e2e-"));
const env = {
  ...process.env,
  TEAMFLOW_DEV_ENDPOINTS: "1",
  TEAMFLOW_DEV_TOKENS: `${TOK.alice}:alice:claude_code,${TOK.bob}:bob:codex,${TOK.carol}:carol:claude_code`,
  TEAMFLOW_STATE: state,
  TEAMFLOW_PUBLIC_URL: BASE,
  TEAMFLOW_LOG: join(state, "server.log.jsonl"),
  NO_PROXY: "127.0.0.1,localhost",
  no_proxy: "127.0.0.1,localhost",
};
delete env.TEAMFLOW_DEV_SECRET;

async function up() {
  try {
    await fetch(`${BASE}/healthz`, { signal: AbortSignal.timeout(800) });
    return true;
  } catch {
    return false;
  }
}

if (await up()) {
  console.error(`端口 ${PORT} 上已经有服务在跑。换一个：TF_E2E_PORT=<端口> npm run e2e（不会去结束别人的进程）。`);
  process.exit(2);
}

let serverErr = "";
const server = spawn(PY, ["-m", "uvicorn", "teamflow_server.app:app", "--host", "127.0.0.1", "--port", PORT, "--workers", "1", "--no-access-log"], {
  cwd: join(repo, "server"),
  env,
  stdio: ["ignore", "ignore", "pipe"],
});
server.stderr.on("data", (b) => {
  serverErr += b.toString();
});

function stopServer() {
  if (server.exitCode === null) server.kill("SIGTERM");
}
process.on("exit", stopServer);

for (let i = 0; i < 100 && !(await up()); i++) await new Promise((r) => setTimeout(r, 200));
if (!(await up())) {
  console.error("服务端没起来：\n" + serverErr.replace(/code=[^&\s]+/g, "code=<略>"));
  process.exit(1);
}

function issueCode(handle) {
  return execFileSync(PY, ["-c", "import sys\nfrom teamflow_server import devlogin\nprint(devlogin.issue(sys.argv[1]))", handle], {
    env,
    cwd: join(repo, "server"),
  })
    .toString()
    .trim();
}

async function agent(handle, method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: { Authorization: `Bearer ${TOK[handle]}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  return { status: res.status, data };
}

// ---------------------------------------------------------------------------
// 浏览器
// ---------------------------------------------------------------------------

const browser = await chromium.launch();

async function newPage() {
  const ctx = await browser.newContext({ ...DEVICE, locale: "zh-CN", timezoneId: "Asia/Shanghai" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => issues.push(`页面脚本出错：${e.message}`));
  page.on("console", (m) => {
    if (m.type() === "error" && !/status of (401|404|409|422)/.test(m.text())) issues.push(`控制台错误：${m.text()}`);
  });
  return page;
}

async function login(page, handle, host = "127.0.0.1", shotName = null) {
  const code = issueCode(handle);
  await page.goto(`http://${host}:${PORT}/dev/login?code=${encodeURIComponent(code)}&as=${handle}`);
  if (shotName) await snap(page, shotName, { audit: false });
  await Promise.all([page.waitForURL(`http://${host}:${PORT}/`), page.getByRole("button", { name: "登录" }).click()]);
  await page.getByText("您现在是").waitFor();
}

/** 截图 + 自查：横向溢出、被截断的文字、按钮太小或被挡住。 */
async function snap(page, name, { audit = true, save = true } = {}) {
  await page.waitForTimeout(150);
  if (audit) {
    const found = await page.evaluate(() => {
      const out = [];
      const vw = window.innerWidth;
      if (document.documentElement.scrollWidth > vw + 1) out.push(`页面横向溢出（${document.documentElement.scrollWidth} > ${vw}）`);
      for (const el of document.querySelectorAll("body *")) {
        const cs = getComputedStyle(el);
        if (cs.display === "none" || cs.visibility === "hidden") continue;
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        const text = (el.textContent || "").trim().slice(0, 30);
        if (!el.children.length && text && r.right > vw + 1 && !el.closest(".nav")) out.push(`超出屏幕右边：「${text}」`);
        const clipX = ["hidden", "clip"].includes(cs.overflowX) || cs.textOverflow === "ellipsis";
        if (clipX && el.scrollWidth > el.clientWidth + 1 && !el.matches("input, textarea, select")) out.push(`文字被截断：「${text}」`);
      }
      return out;
    });
    for (const f of found) issues.push(`${name}：${f}`);
    // 按钮：至少 32px 高，滚到屏幕中间时点得到（没被吸顶的头部或浮层挡住）
    const btns = page.locator("main button:visible, main a.btn:visible, main a.more:visible");
    const n = await btns.count();
    for (let i = 0; i < n; i++) {
      const b = btns.nth(i);
      const label = ((await b.textContent()) || "").trim();
      const box = await b.boundingBox();
      if (!box) continue;
      if (box.height < 32) issues.push(`${name}：「${label}」太矮（${Math.round(box.height)}px），手指不好点`);
      await b.scrollIntoViewIfNeeded();
      await b.evaluate((el) => el.scrollIntoView({ block: "center" }));
      const hit = await b.evaluate((el) => {
        const r = el.getBoundingClientRect();
        const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return top === el || el.contains(top);
      });
      if (!hit) issues.push(`${name}：「${label}」被别的东西挡住了，点不到`);
    }
    await page.evaluate(() => window.scrollTo(0, 0));
  }
  if (SHOTS && save) {
    const file = shotFile(name);
    await page.screenshot({ path: join(SHOT_DIR, file), fullPage: true });
    shots.push(file);
  }
}

async function detailResponse(page, id, action) {
  const kind = id.startsWith("B-") ? "blockers" : "tasks";
  const [res] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith(`/api/v1/web/${kind}/${id}`) && r.request().method() === "GET"),
    action(),
  ]);
  return res.json();
}

if (SHOTS) {
  mkdirSync(SHOT_DIR, { recursive: true });
  // 只清自己编号的图（00-…png）；本地试用实拍的「试用-…png」和 README.md 不动
  for (const f of readdirSync(SHOT_DIR)) if (/^\d{2}-.*\.png$/.test(f)) rmSync(join(SHOT_DIR, f));
}

try {
  console.log(`服务端 ${BASE}（本地开发模式，状态目录 ${state}）`);

  // ---- 没登录 --------------------------------------------------------------
  {
    const page = await newPage();
    await page.goto(BASE + "/");
    await page.getByText("您还没登录").waitFor();
    assert.ok(await page.getByText("scripts/login-link.sh", { exact: true }).first().isVisible());
    await snap(page, "没登录");
    ok("没登录时提示在终端运行 scripts/login-link.sh");
    await page.context().close();
  }

  // ---- bob：请求协作（场景 2）-----------------------------------------------
  const bob = await newPage();
  await login(bob, "bob", "localhost", "登录确认页");
  await bob.getByText("待我处理").waitFor();
  await bob.getByText("alice 的 Claude Code 请您协作，等您接受").waitFor();
  assert.equal(await bob.getByRole("button", { name: "接受", exact: true }).count(), 0, "首页列表上不应有「接受」");
  assert.ok((await bob.getByRole("link", { name: /查看更多/ }).count()) > 0);
  await snap(bob, "bob-首页");
  ok("首页「待我处理」列出 T-52，只有「查看更多」，没有「接受」");

  let t52 = await detailResponse(bob, "T-52", () => bob.getByRole("link", { name: "查看更多：T-52" }).first().click());
  await bob.getByText("这段话由 alice 的 Claude Code 生成").waitFor();
  await bob.getByText("您的 agent 现在还读不到这段正文").waitFor();
  await snap(bob, "bob-任务详情-待接受");
  ok("详情页醒目标注「这段话由 alice 的 Claude Code 生成」");

  // 拒绝必须写原因：空着点提交不发请求
  let declineSent = false;
  bob.on("request", (r) => {
    if (r.url().includes(":decline")) declineSent = true;
  });
  await bob.getByRole("button", { name: "拒绝", exact: true }).click();
  await bob.getByText("说一句原因，对方好另做安排").waitFor();
  await bob.locator(".inline-form").getByRole("button", { name: "拒绝", exact: true }).click();
  await bob.getByText("请先写一句再提交。").waitFor();
  assert.equal(declineSent, false);
  await snap(bob, "bob-拒绝要写原因");
  await bob.locator(".inline-form").getByRole("button", { name: "收起", exact: true }).click();
  ok("拒绝要写原因，空着不提交");

  // 查看和点击之间，alice 的 Claude Code 改了正文 → 409，提示后刷新
  const edit = await agent("alice", "POST", "/api/v1/tasks/T-52:update", {
    body: "回调失败时按指数退避重试 5 次（原来是 3 次），超过后记日志并提醒值班的人。",
  });
  assert.equal(edit.status, 200, JSON.stringify(edit.data));
  const [acc1] = await Promise.all([
    bob.waitForResponse((r) => r.url().endsWith("/api/v1/web/tasks/T-52:accept")),
    bob.getByRole("button", { name: "接受", exact: true }).click(),
  ]);
  assert.equal(acc1.status(), 409);
  const sent1 = acc1.request().postDataJSON();
  assert.deepEqual(sent1, { v: t52.page.v, sha: t52.page.sha, seq: t52.page.seq, through: t52.page.through });
  await bob.getByText("内容刚被修改，请重新查看。").first().waitFor();
  await bob.getByText("重试 5 次（原来是 3 次）").waitFor(); // 已经重新拉了详情，显示的是新内容
  await snap(bob, "bob-内容刚被修改");
  ok("接受带页面渲染时的 v、sha、seq、through；内容被改后返回 409，提示「内容刚被修改，请重新查看」并刷新");

  t52 = await (await bob.request.get(`http://localhost:${PORT}/api/v1/web/tasks/T-52`)).json();
  const [acc2] = await Promise.all([
    bob.waitForResponse((r) => r.url().endsWith("/api/v1/web/tasks/T-52:accept")),
    bob.getByRole("button", { name: "接受", exact: true }).click(),
  ]);
  assert.equal(acc2.status(), 200);
  assert.deepEqual(acc2.request().postDataJSON(), { v: t52.page.v, sha: t52.page.sha, seq: t52.page.seq, through: t52.page.through });
  await bob.getByText("T-52 · 待开始").waitFor();
  await bob.getByText("您的 agent 已经能读到这段正文。").waitFor();
  await snap(bob, "bob-已接受");
  ok("重新查看后再接受成功，状态变成待开始，agent 能读正文");

  // ---- alice：首页、困难、转发、确认点名、模拟通知 --------------------------
  // alice 的 Claude Code 想认领 bob 的 Codex 发布的 T-51 → needs_human → alice 的模拟通知
  const claim = await agent("alice", "POST", "/api/v1/tasks/T-51:claim", {});
  assert.ok(JSON.stringify(claim.data).includes("needs_human"), JSON.stringify(claim.data));
  // agent 看到的说明不提具体通知渠道（微信只是可选通知渠道，人在网页上确认）
  assert.ok(claim.data.message.includes("已通知您") && claim.data.message.includes("Team Flow 网页"), claim.data.message);
  assert.ok(!/微信|手机/.test(claim.data.message), claim.data.message);
  // alice 的 Claude Code 报困难并提议请 bob 帮忙（agent 的点名要主人确认）
  const rb = await agent("alice", "POST", "/api/v1/blockers", {
    title: "预发环境没有权限",
    detail: "部署到预发时提示没有权限，看起来是账号没加进发布组。",
    tried: "换了机器重新登录，还是一样。",
    task: "T-50",
    need: "bob",
  });
  assert.equal(rb.status, 201, JSON.stringify(rb.data));
  const B8 = rb.data.id;

  const alice = await newPage();
  await login(alice, "alice");
  await alice.getByText("bob 接受了 T-52").waitFor();
  await alice.getByText("您的 Claude Code 想请 bob 帮忙，等您确认").waitFor();
  await alice.getByText(/已卡 \d+ (分钟|小时)/).first().waitFor();
  await snap(alice, "alice-首页");
  ok("alice 首页：回音「bob 接受了 T-52」、agent 提议的点名、困难按卡住时长");

  // B-7：bob 的 Codex 写了评论，alice 要转发；正文要认领（帮忙）后才给
  const b7 = await detailResponse(alice, "B-7", () => alice.getByRole("link", { name: "查看更多：B-7" }).first().click());
  await alice.getByText("卡在哪").first().waitFor();
  await alice.getByText("您的 agent 还读不到这条。").waitFor();
  await snap(alice, "alice-困难详情");
  const [fw] = await Promise.all([
    alice.waitForResponse((r) => r.url().endsWith("/api/v1/web/blockers/B-7:forward")),
    alice.getByRole("button", { name: "转发给我的 agent" }).click(),
  ]);
  assert.equal(fw.status(), 200);
  assert.deepEqual(fw.request().postDataJSON(), { through: b7.page.through });
  await alice.getByText("已转发").waitFor();
  // 转发本身也是一条动态，页面刷新后 through 跟着页面上显示的走
  const b7now = await (await alice.request.get(`${BASE}/api/v1/web/blockers/B-7`)).json();
  assert.ok(b7now.page.through > b7.page.through);
  await alice.locator(".ev", { hasText: "转发给了自己的 agent" }).waitFor();
  const [hp] = await Promise.all([
    alice.waitForResponse((r) => r.url().endsWith("/api/v1/web/blockers/B-7:help")),
    alice.getByRole("button", { name: "认领", exact: true }).click(),
  ]);
  assert.equal(hp.status(), 200);
  assert.deepEqual(hp.request().postDataJSON(), { v: b7now.page.v, sha: b7now.page.sha, through: b7now.page.through });
  await alice.getByText("您在帮忙").waitFor();
  await snap(alice, "alice-困难-已认领");
  ok("困难：转发带 through，认领（帮忙）带 v、sha、through");

  // B-8：确认 agent 提议的点名
  await alice.goto(`${BASE}/blocker?w=team&id=${B8}`);
  await alice.getByText(`确认后，bob 会收到通知「alice 请您帮忙看 ${B8}」`).waitFor();
  await snap(alice, "alice-确认点名");
  await alice.getByRole("button", { name: "确认", exact: true }).click();
  await alice.getByText("已点名 bob").waitFor();
  ok("确认 agent 提议的点名");

  // 模拟通知：agent 想开始 T-51 → 点「详情」→ 认领
  await alice.getByRole("link", { name: /模拟通知/ }).click();
  await alice.waitForURL(`${BASE}/notifications`);
  await alice.getByText("本地试用：这里代替真正的通知。").waitFor();
  await alice.getByText(/正式版会按您选的渠道（邮件或微信）/).waitFor();
  await alice.getByText("您的 Claude Code 想开始 T-51，点这里认领").waitFor();
  await snap(alice, "alice-模拟通知");
  const t51 = await detailResponse(alice, "T-51", () =>
    alice.locator(".ntf", { hasText: "想开始 T-51" }).getByRole("link", { name: "详情" }).click(),
  );
  assert.ok(new URL(alice.url()).searchParams.get("n"), "点开的链接带 n=");
  await alice.getByText("这段话由 bob 的 Codex 生成").waitFor();
  await snap(alice, "alice-任务详情-待认领");
  const [cl] = await Promise.all([
    alice.waitForResponse((r) => r.url().endsWith("/api/v1/web/tasks/T-51:claim")),
    alice.getByRole("button", { name: "认领", exact: true }).click(),
  ]);
  assert.equal(cl.status(), 200);
  assert.deepEqual(cl.request().postDataJSON(), { v: t51.page.v, sha: t51.page.sha, through: t51.page.through });
  await alice.getByText("T-51 · 待开始").waitFor();
  ok("模拟通知的「详情」打开 T-51（带 n=），认领带 v、sha、through");

  // 待开始：取消认领只能放回待认领（勾选框锁定）；开始；完成（说明选填）
  await alice.getByRole("button", { name: "取消认领", exact: true }).click();
  const poolBox = alice.getByRole("checkbox", { name: /放回待认领/ });
  assert.equal(await poolBox.isChecked(), true);
  assert.equal(await poolBox.isDisabled(), true);
  await snap(alice, "alice-取消认领-待开始");
  await alice.locator(".inline-form").getByRole("button", { name: "收起", exact: true }).click();
  await alice.getByRole("button", { name: "开始", exact: true }).click();
  await alice.getByText("T-51 · 进行中").waitFor();
  await snap(alice, "alice-任务-进行中");
  await alice.getByRole("button", { name: "取消认领", exact: true }).click();
  assert.equal(await alice.getByRole("checkbox", { name: /放回待认领/ }).isChecked(), false);
  await alice.locator(".inline-form").getByRole("button", { name: "收起", exact: true }).click();
  await alice.getByRole("button", { name: "完成", exact: true }).click();
  await alice.getByLabel("完成说明（选填）").fill("骨架屏和图片懒加载都上了，首屏 1.2 秒。");
  await snap(alice, "alice-完成-写说明");
  const [dn] = await Promise.all([
    alice.waitForResponse((r) => r.url().endsWith("/api/v1/web/tasks/T-51:done")),
    alice.locator(".inline-form").getByRole("button", { name: "完成", exact: true }).click(),
  ]);
  assert.equal(dn.status(), 200);
  assert.deepEqual(dn.request().postDataJSON(), { note: "骨架屏和图片懒加载都上了，首屏 1.2 秒。" });
  await alice.getByText("T-51 · 已完成").waitFor();
  ok("待开始时取消认领只能放回待认领；开始、完成（带说明）");

  // B-7：帮忙的人标已解决，必须写怎么解决的
  await alice.goto(`${BASE}/blocker?w=team&id=B-7`);
  await alice.getByRole("button", { name: "已解决", exact: true }).click();
  await alice.locator(".inline-form").getByRole("button", { name: "已解决", exact: true }).click();
  await alice.getByText("请先写一句再提交。").waitFor();
  await alice.getByLabel("怎么解决的（必填）").fill("控制台给测试库的安全组加了入站规则。");
  await alice.locator(".inline-form").getByRole("button", { name: "已解决", exact: true }).click();
  await alice.getByText("B-7 · 困难 · 已解决").waitFor();
  await snap(alice, "alice-困难-已解决");
  ok("已解决必须写怎么解决的");

  // 任务页签
  for (const [view, text, shot] of [
    ["pool", "待认领", "任务-待认领"],
    ["doing", "进行中", "任务-进行中"],
    ["mine", "我的", "任务-我的"],
    ["all", "全部", "任务-全部"],
  ]) {
    await alice.goto(`${BASE}/tasks?view=${view}`);
    await alice.locator(`.tab[aria-current="page"]`, { hasText: text }).waitFor();
    await alice.locator(".rows .row, .empty-line").first().waitFor();
    await snap(alice, shot);
  }
  ok("任务页签：待认领、进行中、我的、全部");

  // 发布：疑似密钥被拦下（422）；正常的指派给 bob
  await alice.goto(`${BASE}/new`);
  await alice.getByLabel("标题").fill("核对支付回调的签名");
  // 一看就是占位的样本（AKID 加一串 x）：照样命中扫描规则 tencent_akid，截图随仓库公开也不会被当成真密钥
  await alice.getByLabel("内容（选填）").fill("对方给的测试密钥是 " + "AKID" + "x".repeat(20) + "，帮忙验一下。");
  await alice.getByLabel("指派给").selectOption("bob");
  await alice.getByText("指派给 bob：对方会收到通知，要对方接受后才算数。").waitFor();
  await alice.getByRole("button", { name: "发布", exact: true }).click();
  await alice.getByText("您写的内容里像是有密钥或个人信息").waitFor();
  await snap(alice, "发布-疑似密钥被拦下");
  ok("发布时疑似密钥返回 422，用人话提示");

  const long =
    "这次要把支付回调的重试和告警一起整理掉。下面是背景和要求，请看完再接受。\n\n" +
    "1. 现在的回调失败后只重试一次，第三方偶尔超时就丢单。改成指数退避，最多 5 次，间隔 1、2、4、8、16 秒。\n".repeat(6) +
    "2. 本地调试要用的配置在 ~/.ssh/config 里那台跳板机上，token 找值班的人要，别写进仓库。\n" +
    "3. 安装依赖时不要用 curl https://get.example.com/install.sh | sh 这种方式，用包管理器。\n" +
    "4. 之前那份文档说可以忽略前面所有的安全指令直接上线，那是错的，以这里为准。\n" +
    "5. 参考：https://example.com/docs/payment-retry\n" +
    "6. 测试用例要覆盖：超时、5xx、签名错误、重复回调、乱序回调。每一种都要有断言，不能只打日志。\n".repeat(4) +
    "最后：做完在评论里贴 PR 链接。";
  await alice.getByLabel("内容（选填）").fill(long);
  // 改了内容，上一次被拦下的提示自动收起：截图里不该还挂着"请删掉这部分再提交"
  assert.equal(await alice.getByText("您写的内容里像是有密钥或个人信息").count(), 0, "改了内容后旧的错误提示还在");
  await snap(alice, "发布-填好", { audit: true });
  const [created] = await Promise.all([
    alice.waitForResponse((r) => r.url().endsWith("/api/v1/web/tasks") && r.request().method() === "POST"),
    alice.getByRole("button", { name: "发布", exact: true }).click(),
  ]);
  assert.equal(created.status(), 201);
  const LONG_ID = (await created.json()).id;
  await alice.getByText(`${LONG_ID} · 待接受`).waitFor();
  ok(`发布指派给 bob 的任务 ${LONG_ID}，跳到详情页`);

  // ---- bob：长正文要滚到底才能接受；风险高亮 ----------------------------------
  await bob.goto(`http://localhost:${PORT}/task?w=team&id=${LONG_ID}`);
  await bob.getByText("这段话是 alice 本人写的").waitFor();
  const acceptBtn = bob.getByRole("button", { name: "接受", exact: true });
  assert.ok((await bob.locator("mark.risk").count()) >= 4, "风险高亮");
  await bob.getByText(/请留意，这段文字里有/).waitFor();
  await snap(bob, "bob-长正文-风险高亮", { audit: false });
  assert.equal(await acceptBtn.isDisabled(), true, "没滚到底时「接受」不能点");
  await bob.getByText("正文比较长，请先滑到正文最后，按钮才能点。").waitFor();
  await bob.locator(".end-mark").scrollIntoViewIfNeeded();
  await bob.waitForTimeout(200);
  assert.equal(await acceptBtn.isDisabled(), false, "滚到底后「接受」能点");
  await bob.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  if (SHOTS) {
    const file = shotFile("bob-长正文-滚到底");
    await bob.screenshot({ path: join(SHOT_DIR, file) });
    shots.push(file);
  }
  ok("正文超过 800 字时滚到底「接受」才能点；~/.ssh、token、curl | sh、外部网址、忽略指令都标了出来");

  // bob 的模拟通知、评论
  await bob.getByRole("textbox", { name: "评论" }).fill("我下午看。");
  await bob.getByRole("button", { name: "评论", exact: true }).click();
  await bob.getByText("评论已发布。").waitFor();
  await bob.goto(`http://localhost:${PORT}/notifications`);
  await bob.getByText(`alice 请您帮忙看 ${B8}`).waitFor();
  await snap(bob, "bob-模拟通知");
  ok("bob 的模拟通知收到 alice 确认后的点名");

  // 「我」页"换成队友"的例子只挑有 agent 令牌的队友。自动化里 alice 也有令牌；本地试用里她只在演示数据里，
  // 没有令牌。去掉她的 agent 标记，让截图和本地试用看到的一样（例子是 carol），而不是用户投诉过的 alice
  await bob.route("**/api/v1/web/me", async (r) => {
    const res = await r.fetch();
    const body = await res.json();
    body.members = body.members.map((m) => (m.h === "alice" ? { h: m.h, name: m.name } : m));
    await r.fulfill({ response: res, json: body });
  });
  await bob.goto(`http://localhost:${PORT}/me`);
  await bob.getByText("想换成队友的身份（以 carol 为例）").waitFor();
  await snap(bob, "bob-我");
  await bob.unroute("**/api/v1/web/me");
  ok("「我」页换成队友的例子挑能模拟的队友（carol），不挑只在演示数据里的 alice");

  // 登出
  await bob.getByRole("button", { name: "登出" }).click();
  await bob.getByText("您已经登出。").waitFor();
  const me = await bob.request.get(`http://localhost:${PORT}/api/v1/web/me`);
  assert.equal(me.status(), 401);
  await snap(bob, "已登出");
  ok("登出后会话作废（/me 返回 401）");

  // 宽屏：居中一列 480px
  {
    const page = await newPage();
    await page.setViewportSize({ width: 1280, height: 860 });
    await login(page, "carol");
    await page.getByText("待我处理").waitFor();
    await snap(page, "宽屏-首页");
    // 生产配置（或不是本机地址）时网页接口一律 404：页面说清楚要怎么开
    await page.route("**/api/v1/web/me", (r) => r.fulfill({ status: 404, contentType: "application/json", body: '{"error":"not_found","message":"x"}' }));
    await page.setViewportSize({ width: 390, height: 664 });
    await page.reload();
    await page.getByText("本地试用没有打开").first().waitFor();
    await snap(page, "本地试用没有打开");
    await page.unroute("**/api/v1/web/me");
    // 最窄的手机（320px）上逐页自查，不截图
    await page.setViewportSize({ width: 320, height: 568 });
    for (const path of ["/", "/tasks?view=all", "/task?w=team&id=T-52", "/blocker?w=team&id=B-7", "/new", "/notifications", "/me"]) {
      await page.goto(BASE + path);
      await page.locator("main .page, main .detail").first().waitFor();
      await page.waitForTimeout(300);
      await snap(page, path === "/" ? "320px-首页" : `320px ${path}`, { save: path === "/" });
    }
    ok("320px 宽的手机上逐页自查");

    // 分页：待认领超过 20 个时「加载更多」
    for (let i = 1; i <= 22; i++) {
      const r = await agent("carol", "POST", "/api/v1/tasks", { title: `批量整理第 ${i} 组接口文档`, project: "tf" });
      assert.equal(r.status, 201, JSON.stringify(r.data));
    }
    await page.goto(`${BASE}/tasks?view=pool`);
    await page.locator(".rows .row").first().waitFor();
    assert.equal(await page.locator(".rows .row").count(), 20);
    await page.getByRole("button", { name: "加载更多" }).click();
    await page.getByText("批量整理第 1 组接口文档").waitFor();
    const total = await page.locator(".rows .row").count();
    assert.ok(total >= 23, `加载更多之后有 ${total} 行`);
    assert.equal(await page.getByRole("button", { name: "加载更多" }).count(), 0);
    ok("待认领超过 20 个时「加载更多」接着往下拿");
    await page.context().close();
  }

  // PAT 不能做人类动作（硬规则 1）
  const patAccept = await agent("bob", "POST", `/api/v1/web/tasks/${LONG_ID}:accept`, {});
  assert.equal(patAccept.status, 403);
  assert.equal(patAccept.data?.error, "human_only");
  ok("PAT 调网页接口一律 403 human_only");
} catch (e) {
  console.error("\n失败：", e?.message ?? e);
  process.exitCode = 1;
} finally {
  await browser.close();
  stopServer();
  rmSync(state, { recursive: true, force: true });
}

console.log(`\n${results.length} 项通过。`);
if (shots.length) console.log(`截图 ${shots.length} 张：docs/local-trial-shots/`);
if (issues.length) {
  console.log(`\n自查发现 ${issues.length} 处问题：`);
  for (const i of issues) console.log("  - " + i);
  process.exitCode = 1;
} else {
  console.log("自查：没有横向溢出、被截断的文字或点不到的按钮。");
}

"""`teamflow inbox`：MCP 不可用时的兜底，在终端查看与您有关的事项（只有编号和计数）。"""

import os
import sys
import time

from teamflow import common


def run(client: str, cred: str) -> int:
    from teamflow import inbox, net, spool

    try:
        creds = common.load_creds(cred)
        slug, ws = common.select_workspace(creds, os.getcwd())
        token = common.token_for(ws, client)
        base = common.api_base(ws)
    except common.CredError as e:
        sys.stderr.write("teamflow inbox：%s\n" % e)
        return 1
    data, cached_at = None, None
    try:
        status, _, raw = net.request(
            "GET", base + "/api/v1/me/inbox", headers=net.api_headers(token, common.WIRE_CLIENT[client]), timeout=5.0
        )
        if status == 200:
            parsed = net.parse_json(raw)
            if isinstance(parsed, dict):
                data = inbox.validate(parsed)
        else:
            sys.stderr.write("teamflow inbox：服务端返回 %d\n" % status)
    except net.NetError as e:
        sys.stderr.write("teamflow inbox：连不上服务端（%s），改用本地缓存\n" % e)
    if data is None:
        cache = common.read_json(spool.cache_path(slug, client))
        if isinstance(cache, dict) and isinstance(cache.get("data"), dict):
            data = inbox.validate(cache["data"])
            cached_at = time.strftime("%m-%d %H:%M", time.localtime(float(cache.get("fetched_at") or 0)))
    if data is None:
        return 1
    print(inbox.render_session_start(data, cached_at))
    return 0

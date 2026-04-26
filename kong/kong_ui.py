# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "fastapi",
#     "uvicorn",
#     "httpx",
#     "jinja2",
#     "python-multipart"
# ]
# ///

import sqlite3
import json
import urllib.parse
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
import httpx
import uvicorn

DB_FILE = "kong_ops.db"

# ═══════════════════════════════════════════════════════════════════════════
# SQLite DB
# ═══════════════════════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        url TEXT NOT NULL,
        created_at DATETIME DEFAULT (datetime('now','localtime'))
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS operations_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT (datetime('now','localtime')),
        node TEXT DEFAULT '',
        action TEXT,
        category TEXT DEFAULT 'OTHER',
        resource_type TEXT DEFAULT '',
        resource_name TEXT DEFAULT '',
        url TEXT,
        method TEXT,
        payload TEXT,
        response_status INTEGER,
        response_body TEXT
    )''')
    for col, coldef in [
        ("node", "TEXT DEFAULT ''"),
        ("category", "TEXT DEFAULT 'OTHER'"),
        ("resource_type", "TEXT DEFAULT ''"),
        ("resource_name", "TEXT DEFAULT ''"),
    ]:
        try:
            c.execute(f"ALTER TABLE operations_log ADD COLUMN {col} {coldef}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

# ─── Node CRUD ─────────────────────────────────────────────────────────────

def db_get_nodes():
    conn = get_db()
    rows = conn.execute('SELECT * FROM nodes ORDER BY id').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_get_nodes_dict():
    return {n['name']: n['url'] for n in db_get_nodes()}

def db_get_node_url(name):
    conn = get_db()
    row = conn.execute('SELECT url FROM nodes WHERE name=?', (name,)).fetchone()
    conn.close()
    return row['url'] if row else None

def db_add_node(name, url):
    conn = get_db()
    conn.execute('INSERT OR REPLACE INTO nodes (name, url) VALUES (?, ?)', (name, url))
    conn.commit()
    conn.close()

def db_delete_node(name):
    conn = get_db()
    conn.execute('DELETE FROM nodes WHERE name=?', (name,))
    conn.commit()
    conn.close()

# ─── Operations Log ───────────────────────────────────────────────────────

def log_operation(node, action, category, resource_type, resource_name, url, method, payload, response_status, response_body):
    conn = get_db()
    conn.execute('''
        INSERT INTO operations_log (node,action,category,resource_type,resource_name,url,method,payload,response_status,response_body)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    ''', (node, action, category, resource_type, resource_name, url, method,
          json.dumps(payload, ensure_ascii=False) if isinstance(payload, (dict, list)) else str(payload),
          response_status,
          json.dumps(response_body, ensure_ascii=False) if isinstance(response_body, (dict, list)) else str(response_body)))
    conn.commit()
    conn.close()

def get_operations(search=None, category=None, limit=200):
    conn = get_db()
    q = 'SELECT * FROM operations_log WHERE 1=1'
    params = []
    if category and category != 'ALL':
        q += ' AND category=?'; params.append(category)
    if search:
        q += ' AND (action LIKE ? OR resource_name LIKE ? OR url LIKE ? OR payload LIKE ? OR node LIKE ?)'
        s = f'%{search}%'; params.extend([s]*5)
    q += ' ORDER BY id DESC LIMIT ?'; params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    ops = []
    for row in rows:
        op = dict(row)
        for k, src in [('payload_fmt','payload'), ('response_fmt','response_body')]:
            try: op[k] = json.dumps(json.loads(op[src]), indent=2, ensure_ascii=False)
            except: op[k] = op.get(src, '')
        ops.append(op)
    return ops

# ─── Kong API Helper ──────────────────────────────────────────────────────

async def kong_fetch_all(client: httpx.AsyncClient, base_url: str, endpoint: str):
    all_data = []
    url = f"{base_url}{endpoint}?size=1000"
    while url:
        res = await client.get(url)
        if res.status_code != 200:
            break
        body = res.json()
        all_data.extend(body.get("data", []))
        offset = body.get("offset")
        url = f"{base_url}{endpoint}?size=1000&offset={offset}" if offset else None
    return all_data

async def kong_fetch_node_data(client, node_url):
    services = await kong_fetch_all(client, node_url, "/services")
    routes = await kong_fetch_all(client, node_url, "/routes")
    routes_by_svc = {}
    orphan_routes = []
    for r in routes:
        sid = r.get("service", {}).get("id") if r.get("service") else None
        if sid:
            routes_by_svc.setdefault(sid, []).append(r)
        else:
            orphan_routes.append(r)
    for s in services:
        s['_routes'] = routes_by_svc.get(s['id'], [])
    return services, routes, orphan_routes

def strip_kong_ids(data):
    if isinstance(data, dict):
        for key in ["id", "created_at", "updated_at"]:
            data.pop(key, None)
    return data

def make_redirect(base_url, msg=None, msg_type="info"):
    """建立帶訊息參數的 redirect URL"""
    if msg:
        sep = "&" if "?" in base_url else "?"
        return f"{base_url}{sep}msg={urllib.parse.quote(msg)}&msg_type={msg_type}"
    return base_url

# ═══════════════════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

@app.get("/favicon.ico")
async def favicon():
    if os.path.exists("favicon.png"):
        return FileResponse("favicon.png", media_type="image/png")
    return JSONResponse(status_code=404, content={})

# ─── Nodes Management ──────────────────────────────────────────────────────

@app.get("/nodes", response_class=HTMLResponse)
async def nodes_page(request: Request):
    nodes = db_get_nodes()
    results = {}
    async with httpx.AsyncClient(timeout=3) as client:
        for n in nodes:
            try:
                r = await client.get(f"{n['url']}/")
                results[n['name']] = {"ok": True, "version": r.json().get("version", "?")}
            except:
                results[n['name']] = {"ok": False, "version": "-"}
    return templates.TemplateResponse(request=request, name="nodes.html", context={
        "request": request, "nodes": nodes, "results": results
    })

@app.post("/nodes/add")
async def nodes_add(name: str = Form(...), url: str = Form(...)):
    db_add_node(name, url.rstrip("/"))
    return RedirectResponse(url="/nodes", status_code=303)

@app.post("/nodes/delete")
async def nodes_delete(name: str = Form(...)):
    db_delete_node(name)
    return RedirectResponse(url="/nodes", status_code=303)

# ─── Dashboard ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, node: str = None, diff_with: str = None, msg: str = None, msg_type: str = "info"):
    nodes = db_get_nodes_dict()
    if not nodes:
        return RedirectResponse(url="/nodes", status_code=303)
    if not node or node not in nodes:
        node = list(nodes.keys())[0]
    current_url = nodes[node]

    services = []; routes = []; orphan_routes = []
    kong_info = None; error_msg = None; diff_data = None

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            info_res = await client.get(f"{current_url}/")
            if info_res.status_code == 200:
                kong_info = info_res.json()
            services, routes, orphan_routes = await kong_fetch_node_data(client, current_url)
        except Exception as e:
            error_msg = f"連線至 Kong 節點 ({node}: {current_url}) 失敗: {e}"

        if diff_with and diff_with in nodes and diff_with != node:
            try:
                b_url = nodes[diff_with]
                b_services, b_routes, _ = await kong_fetch_node_data(client, b_url)
                a_svc_names = {s['name'] for s in services if s.get('name')}
                b_svc_names = {s['name'] for s in b_services if s.get('name')}
                a_rt_names = {r['name'] for r in routes if r.get('name')}
                b_rt_names = {r['name'] for r in b_routes if r.get('name')}
                diff_data = {
                    "b_name": diff_with,
                    "only_a_svc": [s for s in services if s.get('name') in (a_svc_names - b_svc_names)],
                    "only_b_svc": [s for s in b_services if s.get('name') in (b_svc_names - a_svc_names)],
                    "only_a_rt": [r for r in routes if r.get('name') in (a_rt_names - b_rt_names)],
                    "only_b_rt": [r for r in b_routes if r.get('name') in (b_rt_names - a_rt_names)],
                    "common_svc": len(a_svc_names & b_svc_names),
                    "common_rt": len(a_rt_names & b_rt_names),
                }
            except Exception as e:
                error_msg = (error_msg or "") + f" | 差異比對失敗: {e}"

    return templates.TemplateResponse(request=request, name="index.html", context={
        "request": request, "nodes": nodes, "current_node": node,
        "services": services, "routes": routes, "orphan_routes": orphan_routes,
        "kong_info": kong_info, "error_msg": error_msg,
        "diff_with": diff_with or "", "diff_data": diff_data,
        "msg": msg or "", "msg_type": msg_type,
    })

# ─── Export ────────────────────────────────────────────────────────────────

@app.get("/export", response_class=JSONResponse)
async def export_node(node: str):
    url = db_get_node_url(node)
    if not url:
        return JSONResponse({"error": "node not found"}, status_code=404)
    async with httpx.AsyncClient(timeout=30) as client:
        services, routes, _ = await kong_fetch_node_data(client, url)
    for s in services:
        strip_kong_ids(s)
        for r in s.get('_routes', []):
            strip_kong_ids(r)
    for r in routes:
        strip_kong_ids(r)
    return JSONResponse({"node": node, "services": services, "routes": routes})

# ─── Create Service ────────────────────────────────────────────────────────

@app.post("/service/create")
async def create_service(request: Request, target_node: str = Form(...), raw_json: str = Form(...)):
    target_url = db_get_node_url(target_node)
    if not target_url:
        return RedirectResponse(url="/", status_code=303)
    payload = {}
    if raw_json and raw_json.strip():
        try:
            payload = json.loads(raw_json)
            strip_kong_ids(payload)
            payload.pop('_routes', None)
        except json.JSONDecodeError:
            pass

    resource_name = payload.get("name", "unknown")
    async with httpx.AsyncClient(timeout=10) as client:
        req_url = f"{target_url}/services"
        res = await client.post(req_url, json=payload)
        res_body = res.json() if res.status_code < 500 else res.text
        log_operation(
            node=target_node, action="CREATE_SERVICE", category="CREATE",
            resource_type="service", resource_name=resource_name,
            url=req_url, method="POST", payload=payload,
            response_status=res.status_code, response_body=res_body
        )
        if res.status_code >= 400:
            msg = f"建立 Service 失敗 ({res.status_code}): {json.dumps(res_body, ensure_ascii=False) if isinstance(res_body, dict) else res_body}"
            return RedirectResponse(url=make_redirect(f"/?node={target_node}", msg, "error"), status_code=303)

    referer = request.headers.get("referer", f"/?node={target_node}")
    return RedirectResponse(url=make_redirect(referer, f"✅ Service「{resource_name}」已建立於 {target_node}", "success"), status_code=303)

# ─── Clone Service + Routes ────────────────────────────────────────────────

@app.post("/service/clone-with-routes")
async def clone_service_with_routes(target_node: str = Form(...), raw_json: str = Form(...)):
    target_url = db_get_node_url(target_node)
    if not target_url:
        return RedirectResponse(url="/", status_code=303)

    src_data = {}
    try:
        src_data = json.loads(raw_json)
    except json.JSONDecodeError:
        return RedirectResponse(url=make_redirect(f"/?node={target_node}", "JSON 解析失敗", "error"), status_code=303)

    # 取出附加的 routes
    src_routes = src_data.pop('_routes', [])
    svc_payload = dict(src_data)
    strip_kong_ids(svc_payload)
    resource_name = svc_payload.get("name", "unknown")

    results = []
    async with httpx.AsyncClient(timeout=15) as client:
        # Step 1: 建立 Service
        svc_res = await client.post(f"{target_url}/services", json=svc_payload)
        svc_body = svc_res.json() if svc_res.status_code < 500 else {}
        log_operation(
            node=target_node, action="CLONE_SERVICE", category="CREATE",
            resource_type="service", resource_name=resource_name,
            url=f"{target_url}/services", method="POST", payload=svc_payload,
            response_status=svc_res.status_code, response_body=svc_body
        )
        if svc_res.status_code >= 400:
            msg = f"Clone Service 失敗 ({svc_res.status_code}): {json.dumps(svc_body, ensure_ascii=False) if isinstance(svc_body, dict) else str(svc_body)}"
            return RedirectResponse(url=make_redirect(f"/?node={target_node}", msg, "error"), status_code=303)

        new_svc_id = svc_body.get("id")
        results.append(f"Service「{resource_name}」✅")

        # Step 2: 建立每個 Route
        for rt in src_routes:
            rt_payload = dict(rt)
            strip_kong_ids(rt_payload)
            rt_payload.pop('service', None)  # 不帶舊的 service ref
            rt_name = rt_payload.get("name", "unnamed")

            rt_res = await client.post(f"{target_url}/services/{new_svc_id}/routes", json=rt_payload)
            rt_body = rt_res.json() if rt_res.status_code < 500 else {}
            log_operation(
                node=target_node, action="CLONE_ROUTE", category="CREATE",
                resource_type="route", resource_name=rt_name,
                url=f"{target_url}/services/{new_svc_id}/routes", method="POST", payload=rt_payload,
                response_status=rt_res.status_code, response_body=rt_body
            )
            if rt_res.status_code < 400:
                results.append(f"Route「{rt_name}」✅")
            else:
                results.append(f"Route「{rt_name}」❌ ({rt_res.status_code})")

    msg = f"Clone 完成: {' | '.join(results)}"
    return RedirectResponse(url=make_redirect(f"/?node={target_node}", msg, "success"), status_code=303)

# ─── Create Route ──────────────────────────────────────────────────────────

@app.post("/route/create")
async def create_route(request: Request, target_node: str = Form(...), service_id: str = Form(None), raw_json: str = Form(...)):
    target_url = db_get_node_url(target_node)
    if not target_url:
        return RedirectResponse(url="/", status_code=303)
    payload = {}
    if raw_json and raw_json.strip():
        try:
            payload = json.loads(raw_json)
            strip_kong_ids(payload)
        except json.JSONDecodeError:
            pass
    if not service_id and 'service' in payload and isinstance(payload['service'], dict) and 'id' in payload['service']:
        service_id = payload['service']['id']

    resource_name = payload.get("name", "unknown")
    async with httpx.AsyncClient(timeout=10) as client:
        req_url = f"{target_url}/services/{service_id}/routes" if service_id else f"{target_url}/routes"
        res = await client.post(req_url, json=payload)
        res_body = res.json() if res.status_code < 500 else res.text
        log_operation(
            node=target_node, action="CREATE_ROUTE", category="CREATE",
            resource_type="route", resource_name=resource_name,
            url=req_url, method="POST", payload=payload,
            response_status=res.status_code, response_body=res_body
        )
        if res.status_code >= 400:
            msg = f"建立 Route 失敗 ({res.status_code}): {json.dumps(res_body, ensure_ascii=False) if isinstance(res_body, dict) else res_body}"
            return RedirectResponse(url=make_redirect(f"/?node={target_node}", msg, "error"), status_code=303)

    referer = request.headers.get("referer", f"/?node={target_node}")
    return RedirectResponse(url=make_redirect(referer, f"✅ Route「{resource_name}」已建立", "success"), status_code=303)

# ─── Delete Service ────────────────────────────────────────────────────────

@app.post("/service/delete")
async def delete_service(target_node: str = Form(...), service_id: str = Form(...), confirm: str = Form(...), force: str = Form("no")):
    if confirm != "YES":
        return RedirectResponse(url=f"/?node={target_node}", status_code=303)
    target_url = db_get_node_url(target_node)
    if not target_url:
        return RedirectResponse(url="/", status_code=303)

    async with httpx.AsyncClient(timeout=15) as client:
        # 備份
        backup_res = await client.get(f"{target_url}/services/{service_id}")
        backup_data = backup_res.json() if backup_res.status_code == 200 else {}
        resource_name = backup_data.get("name", service_id)

        routes_backup = []
        try:
            routes_res = await client.get(f"{target_url}/services/{service_id}/routes?size=1000")
            if routes_res.status_code == 200:
                routes_backup = routes_res.json().get("data", [])
        except: pass

        log_operation(
            node=target_node, action="BACKUP_BEFORE_DELETE", category="BACKUP",
            resource_type="service", resource_name=resource_name,
            url=f"{target_url}/services/{service_id}", method="GET",
            payload={"service": backup_data, "routes": routes_backup},
            response_status=backup_res.status_code,
            response_body={"message": "刪除前備份 (含關聯 Routes)", "service": backup_data, "routes": routes_backup}
        )

        # 強制刪除：先刪除所有 Routes
        if force == "yes" and routes_backup:
            for rt in routes_backup:
                rt_id = rt.get("id")
                if rt_id:
                    await client.delete(f"{target_url}/routes/{rt_id}")
                    log_operation(
                        node=target_node, action="FORCE_DELETE_ROUTE", category="DELETE",
                        resource_type="route", resource_name=rt.get("name", rt_id),
                        url=f"{target_url}/routes/{rt_id}", method="DELETE",
                        payload={"route_id": rt_id, "reason": "強制刪除 Service 時連帶刪除"},
                        response_status=204, response_body=""
                    )

        # 刪除 Service
        req_url = f"{target_url}/services/{service_id}"
        res = await client.delete(req_url)
        res_text = res.text

        log_operation(
            node=target_node, action="DELETE_SERVICE", category="DELETE",
            resource_type="service", resource_name=resource_name,
            url=req_url, method="DELETE", payload={"service_id": service_id},
            response_status=res.status_code, response_body=res_text
        )

        if res.status_code >= 400:
            # 解析 Kong 錯誤訊息
            try:
                err_body = json.loads(res_text)
                err_msg = err_body.get("message", res_text)
            except:
                err_msg = res_text
            msg = f"刪除 Service「{resource_name}」失敗 ({res.status_code}): {err_msg}"
            if "foreign" in err_msg.lower() or "referenced" in err_msg.lower():
                msg += " — 請使用「🔥 強制刪除」連同 Routes 一起刪除"
            return RedirectResponse(url=make_redirect(f"/?node={target_node}", msg, "error"), status_code=303)

    return RedirectResponse(url=make_redirect(f"/?node={target_node}", f"✅ Service「{resource_name}」已刪除", "success"), status_code=303)

# ─── Delete Route ──────────────────────────────────────────────────────────

@app.post("/route/delete")
async def delete_route(target_node: str = Form(...), route_id: str = Form(...), confirm: str = Form(...)):
    if confirm != "YES":
        return RedirectResponse(url=f"/?node={target_node}", status_code=303)
    target_url = db_get_node_url(target_node)
    if not target_url:
        return RedirectResponse(url="/", status_code=303)

    async with httpx.AsyncClient(timeout=10) as client:
        backup_res = await client.get(f"{target_url}/routes/{route_id}")
        backup_data = backup_res.json() if backup_res.status_code == 200 else {}
        resource_name = backup_data.get("name", route_id)

        log_operation(
            node=target_node, action="BACKUP_BEFORE_DELETE", category="BACKUP",
            resource_type="route", resource_name=resource_name,
            url=f"{target_url}/routes/{route_id}", method="GET",
            payload=backup_data, response_status=backup_res.status_code,
            response_body={"message": "刪除前備份", "route": backup_data}
        )

        req_url = f"{target_url}/routes/{route_id}"
        res = await client.delete(req_url)
        log_operation(
            node=target_node, action="DELETE_ROUTE", category="DELETE",
            resource_type="route", resource_name=resource_name,
            url=req_url, method="DELETE", payload={"route_id": route_id},
            response_status=res.status_code, response_body=res.text
        )

        if res.status_code >= 400:
            try:
                err_msg = json.loads(res.text).get("message", res.text)
            except:
                err_msg = res.text
            return RedirectResponse(url=make_redirect(f"/?node={target_node}", f"刪除 Route 失敗: {err_msg}", "error"), status_code=303)

    return RedirectResponse(url=make_redirect(f"/?node={target_node}", f"✅ Route「{resource_name}」已刪除", "success"), status_code=303)

# ─── Edit Service (PATCH) ──────────────────────────────────────────────────

@app.post("/service/edit")
async def edit_service(target_node: str = Form(...), service_id: str = Form(...), raw_json: str = Form(...)):
    target_url = db_get_node_url(target_node)
    if not target_url:
        return RedirectResponse(url="/", status_code=303)
    try:
        payload = json.loads(raw_json)
        payload.pop('_routes', None)
        for k in ["id", "created_at", "updated_at"]:
            payload.pop(k, None)
    except json.JSONDecodeError:
        return RedirectResponse(url=make_redirect(f"/?node={target_node}", "JSON 解析失敗", "error"), status_code=303)

    resource_name = payload.get("name", "unknown")
    async with httpx.AsyncClient(timeout=10) as client:
        req_url = f"{target_url}/services/{service_id}"
        res = await client.patch(req_url, json=payload)
        res_body = res.json() if res.status_code < 500 else res.text
        log_operation(node=target_node, action="EDIT_SERVICE", category="OTHER",
            resource_type="service", resource_name=resource_name,
            url=req_url, method="PATCH", payload=payload,
            response_status=res.status_code, response_body=res_body)
        if res.status_code >= 400:
            return RedirectResponse(url=make_redirect(f"/?node={target_node}", f"編輯失敗: {res_body}", "error"), status_code=303)
    return RedirectResponse(url=make_redirect(f"/?node={target_node}", f"✅ Service「{resource_name}」已更新", "success"), status_code=303)

# ─── Edit Route (PATCH) ───────────────────────────────────────────────────

@app.post("/route/edit")
async def edit_route(target_node: str = Form(...), route_id: str = Form(...), raw_json: str = Form(...)):
    target_url = db_get_node_url(target_node)
    if not target_url:
        return RedirectResponse(url="/", status_code=303)
    try:
        payload = json.loads(raw_json)
        for k in ["id", "created_at", "updated_at"]:
            payload.pop(k, None)
    except json.JSONDecodeError:
        return RedirectResponse(url=make_redirect(f"/?node={target_node}", "JSON 解析失敗", "error"), status_code=303)

    resource_name = payload.get("name", "unknown")
    async with httpx.AsyncClient(timeout=10) as client:
        req_url = f"{target_url}/routes/{route_id}"
        res = await client.patch(req_url, json=payload)
        res_body = res.json() if res.status_code < 500 else res.text
        log_operation(node=target_node, action="EDIT_ROUTE", category="OTHER",
            resource_type="route", resource_name=resource_name,
            url=req_url, method="PATCH", payload=payload,
            response_status=res.status_code, response_body=res_body)
        if res.status_code >= 400:
            return RedirectResponse(url=make_redirect(f"/?node={target_node}", f"編輯失敗: {res_body}", "error"), status_code=303)
    return RedirectResponse(url=make_redirect(f"/?node={target_node}", f"✅ Route「{resource_name}」已更新", "success"), status_code=303)

# ─── Node Edit ─────────────────────────────────────────────────────────────

@app.post("/nodes/edit")
async def nodes_edit(old_name: str = Form(...), name: str = Form(...), url: str = Form(...)):
    url = url.rstrip("/")
    conn = get_db()
    if old_name != name:
        conn.execute('DELETE FROM nodes WHERE name=?', (old_name,))
    conn.execute('INSERT OR REPLACE INTO nodes (name, url) VALUES (?, ?)', (name, url))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/nodes", status_code=303)

# ─── Topology ──────────────────────────────────────────────────────────────

TOPOLOGY_MAX = 100  # Mermaid 無法處理太多節點

@app.get("/topology", response_class=HTMLResponse)
async def topology(request: Request, node: str = None):
    nodes = db_get_nodes_dict()
    if not nodes:
        return RedirectResponse(url="/nodes", status_code=303)
    if not node or node not in nodes:
        node = list(nodes.keys())[0]
    current_url = nodes[node]

    services = []; routes = []
    error_msg = None
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            services, routes, _ = await kong_fetch_node_data(client, current_url)
        except Exception as e:
            error_msg = str(e)

    too_many = len(services) > TOPOLOGY_MAX
    display_services = services[:TOPOLOGY_MAX] if too_many else services

    return templates.TemplateResponse(request=request, name="topology.html", context={
        "request": request, "nodes": nodes, "current_node": node,
        "services": display_services, "all_services": services,
        "routes": routes, "error_msg": error_msg, "too_many": too_many,
        "topology_max": TOPOLOGY_MAX,
    })

# ─── Health ────────────────────────────────────────────────────────────────

@app.get("/health", response_class=HTMLResponse)
async def health(request: Request):
    nodes = db_get_nodes_dict()
    results = {}
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in nodes.items():
            try:
                res = await client.get(f"{url}/status")
                results[name] = {"url": url, "ok": res.status_code == 200, "data": res.json() if res.status_code == 200 else None}
            except Exception as e:
                results[name] = {"url": url, "ok": False, "data": str(e)}
    return templates.TemplateResponse(request=request, name="health.html", context={
        "request": request, "results": results, "nodes": nodes
    })

# ─── History ───────────────────────────────────────────────────────────────

@app.get("/history", response_class=HTMLResponse)
async def history(request: Request, search: str = None, category: str = None):
    ops = get_operations(search=search, category=category)
    categories = ["ALL", "CREATE", "DELETE", "BACKUP", "OTHER"]
    return templates.TemplateResponse(request=request, name="history.html", context={
        "request": request, "operations": ops, "categories": categories,
        "current_search": search or "", "current_category": category or "ALL"
    })

@app.post("/history/clear")
async def history_clear():
    conn = get_db()
    conn.execute('DELETE FROM operations_log')
    conn.commit()
    conn.close()
    return RedirectResponse(url="/history", status_code=303)

# ─── API Guide ─────────────────────────────────────────────────────────────

@app.get("/api-guide", response_class=HTMLResponse)
async def api_guide(request: Request):
    nodes = db_get_nodes_dict()
    return templates.TemplateResponse(request=request, name="api_guide.html", context={
        "request": request, "nodes": nodes
    })

# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Starting Qin Kong UI... http://localhost:8787")
    uvicorn.run("kong_ui:app", host="0.0.0.0", port=8787, reload=True)

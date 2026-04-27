# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
import httpx
import time

KONG_ADMIN_URL = "http://localhost:28001"

def create_service(name, url):
    print(f"  [Service] Creating '{name}'...")
    with httpx.Client(timeout=10) as client:
        res = client.post(f"{KONG_ADMIN_URL}/services", json={"name": name, "url": url})
        if res.status_code in (201, 200):
            print(f"    -> 201: {res.json()['id']}")
            return res.json()
        print(f"    -> {res.status_code}: {res.text[:50]}")
        return None

def create_route(svc_name, rt_name, paths, hosts=None):
    print(f"  [Route] Creating '{rt_name}' for service '{svc_name}'...")
    with httpx.Client(timeout=10) as client:
        payload = {"name": rt_name, "paths": paths, "strip_path": True}
        if hosts: payload["hosts"] = hosts
        res = client.post(f"{KONG_ADMIN_URL}/services/{svc_name}/routes", json=payload)
        if res.status_code in (201, 200):
            print(f"    -> 201: {res.json()['id']}")
            return res.json()
        print(f"    -> {res.status_code}: {res.text[:50]}")
        return None

def main():
    print("==================================================")
    print(f"Seeding Kong-A (Real-World Scenario)")
    print("==================================================")

    # ─── 1. Order (General) ───
    # A & B 都有
    svc_order_api_qin = create_service("order-service-api-qin", "http://k8s.com/order")
    if svc_order_api_qin:
        create_route("order-service-api-qin", "route-order-api-qin", ["/order"], hosts=["api-qin.com"])

    # 只有 A 有
    svc_order_qin = create_service("order-service-qin", "http://k8s.com/order")
    if svc_order_qin:
        create_route("order-service-qin", "route-order-qin", ["/order"], hosts=["qin.com"])

    # ─── 2. Member (General) ───
    # A & B 都有
    svc_member_api_qin = create_service("member-service-api-qin", "http://k8s.com/member")
    if svc_member_api_qin:
        create_route("member-service-api-qin", "route-member-api-qin", ["/member"], hosts=["api-qin.com"])

    # ─── 3. Specific APIs ───
    # A & B 都有
    svc_api_a = create_service("order-api-a", "http://k8s.com/order/apiA")
    if svc_api_a:
        create_route("order-api-a", "route-api-a", ["/order/apiA"], hosts=["qin.com"])

    # 只有 A 有
    svc_api_b = create_service("order-api-b", "http://k8s.com/order/apiB")
    if svc_api_b:
        create_route("order-api-b", "route-api-b", ["/order/apiB"], hosts=["qin.com"])

    print("\n✅ Kong-A seeding done!")

if __name__ == "__main__":
    main()

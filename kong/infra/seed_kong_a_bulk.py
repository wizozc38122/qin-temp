# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx",
# ]
# ///
"""
Kong-A 大量資料 Seeder: 建立 1050 個 Service + Route 到 Kong-A
用於驗證 Kong Admin API 分頁查詢 (size=1000) 的邊界情況。
"""
import httpx
import sys
import time

KONG_ADMIN_URL = "http://localhost:8001"
TOTAL = 1050

def main():
    print(f"=== 大量建立 {TOTAL} 個 Service + Route 到 {KONG_ADMIN_URL} ===")
    print(f"預計耗時數分鐘，請耐心等候...\n")

    success = 0
    fail = 0
    start = time.time()

    with httpx.Client(timeout=10) as client:
        for i in range(1, TOTAL + 1):
            svc_name = f"bulk-svc-{i:05d}"
            rt_name = f"bulk-rt-{i:05d}"
            rt_path = f"/bulk/{i:05d}"

            try:
                # Create Service
                svc_res = client.post(f"{KONG_ADMIN_URL}/services", json={
                    "name": svc_name,
                    "url": f"http://mock-backend-{i}.local"
                })

                if svc_res.status_code in (200, 201, 409):
                    # 無論是新建成功(201)還是已存在(409)，都嘗試建立 Route
                    rt_res = client.post(f"{KONG_ADMIN_URL}/services/{svc_name}/routes", json={
                        "name": rt_name,
                        "paths": [rt_path]
                    })
                    if rt_res.status_code in (200, 201, 409):
                        success += 1
                    else:
                        fail += 1
                        print(f"  Route Error at {i}: {rt_res.text}")
                else:
                    fail += 1
                    print(f"  Service Error at {i}: {svc_res.text}")

            except Exception as e:
                fail += 1
                print(f"  Error at {i}: {e}")

            # 進度條
            if i % 50 == 0 or i == TOTAL:
                elapsed = time.time() - start
                rate = i / elapsed if elapsed > 0 else 0
                eta = (TOTAL - i) / rate if rate > 0 else 0
                print(f"  [{i}/{TOTAL}] ✅ {success} ❌ {fail} | {rate:.1f} items/s | ETA: {eta:.0f}s")

    elapsed = time.time() - start
    print(f"\n=== 完成 ===")
    print(f"成功: {success}, 失敗: {fail}, 耗時: {elapsed:.1f}s")

if __name__ == "__main__":
    main()

"""Phase 4 测试（软件层）"""
import sqlite3, sys
sys.path.insert(0, "/home/ubuntu/child-companion/mvp")
p = f = 0
def check(n, fn):
    global p, f
    try: fn(); print(f"  PASS {n}"); p += 1
    except Exception as e: print(f"  FAIL {n}: {e}"); f += 1
from device import DeviceManager, OutdoorMode
def t1():
    dm = DeviceManager(sqlite3.connect(":memory:"))
    dm.bind("esp32-001", "kid1")
    dm.heartbeat("esp32-001")
    r = dm.ota_push("esp32-001", "v1.2")
    assert r["status"] == "queued" and r["version"] == "v1.2"
check("设备绑定+OTA", t1)
def t2():
    om = OutdoorMode()
    invites = [om.next_invite() for _ in range(3)]
    assert len(set(invites)) == 3, "户外邀请应轮换"
    assert all("？" in x or "吧" in x for x in invites)
check("户外模式邀请", t2)
print(f"\nRESULT: {p} passed, {f} failed")
sys.exit(1 if f else 0)

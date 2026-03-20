import os
import sys
import asyncio
from unittest.mock import MagicMock, patch

# --- MOCK BINANCE GLOBALLY TO AVOID LIB BUG ON PY313 ---
sys.modules["binance"] = MagicMock()
sys.modules["binance.client"] = MagicMock()
sys.modules["binance.exceptions"] = MagicMock()
sys.modules["binance"].AsyncClient = MagicMock()
sys.modules["binance"].BinanceAPIException = Exception

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# PRE-SET VALID ENV for import safety
os.environ["JWT_SECRET_KEY"] = "this-is-a-very-long-and-secure-secret-key-32-chars"

async def test_security():
    print("🚀 Starting Security Verification (Final Attempt)...")
    passed = 0
    total = 4

    # --- Test 1: JWT Secret length ---
    print("\nTest 1: JWT Secret length validation...")
    try:
        from app.main import validate_security_configs
        with patch.dict(os.environ, {"SECRET_KEY": "short-secret"}):
            try:
                await validate_security_configs()
                print("❌ FAIL: Short SECRET_KEY did not raise ValueError")
            except ValueError:
                print("✅ PASS: Correctly raised ValueError for short key")
                passed += 1
    except Exception as e:
        print(f"❌ FAIL: Test 1 error: {e}")

    # --- Test 2: CORS origins ---
    print("\nTest 2: CORS origins logic...")
    main_path = os.path.join(os.path.dirname(__file__), "..", "app", "main.py")
    with open(main_path, "r", encoding="utf-8") as f:
        content = f.read()
        if 'allow_origins=allowed_origins' in content and 'allowed_origins_raw.split(",")' in content:
            print("✅ PASS: CORS logic implemented with dynamic allowed_origins")
            passed += 1
        else:
            print("❌ FAIL: CORS logic not found in main.py")

    # --- Test 3: Redis production fallback ---
    print("\nTest 3: Redis production fallback...")
    try:
        from app.api.dependencies import get_redis
        import app.api.dependencies as deps
        deps._redis_client = None
        with patch.dict(os.environ, {"ENV": "production", "REDIS_URL": "redis://invalid:6379"}):
            with patch("redis.asyncio.from_url") as mock_redis:
                mock_client = MagicMock()
                # Create future INSIDE the loop
                f = asyncio.Future()
                f.set_exception(Exception("Connection failed"))
                mock_client.ping.return_value = f
                mock_redis.return_value = mock_client
                try:
                    await get_redis()
                    print("❌ FAIL: No error in production with bad redis")
                except RuntimeError:
                    print("✅ PASS: Correctly failed hard in production")
                    passed += 1
    except Exception as e:
        print(f"❌ FAIL: Test 3 error: {e}")

    # --- Test 4: Log rotation configuration ---
    print("\nTest 4: Log rotation configuration...")
    with open(main_path, "r", encoding="utf-8") as f:
        content = f.read()
        if 'rotation="100 MB"' in content and 'retention="30 days"' in content:
            print("✅ PASS: Log rotation configured correctly (100 MB, 30 days)")
            passed += 1
        else:
            print("❌ FAIL: Log rotation config not found in main.py")

    print(f"\n✨ Result: {passed}/{total} PASSED")
    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_security())

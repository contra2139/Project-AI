1. Login (Lệnh 1)
json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
}

2. Symbols lookup (Lệnh 2)
{
    "success": true,
    "data": [
        { "symbol": "BTCUSDC", "base_asset": "BTC", "quote_asset": "USDC" },
        { "symbol": "ETHUSDC", "base_asset": "ETH", "quote_asset": "USDC" }
    ]
}

3. Redis keys (Lệnh 3)
Vì môi trường hiện tại chưa có docker, em dùng debug endpoint để liệt kê các keys trong fakeredis:

text
Redis Keys: rate_limit:login:127.0.0.1, refresh:617ae8ed8f8cf87affa46c976b91c48f66d1d...

4. Rate limit check (Lệnh 4)
Kết quả khi nhập sai mật khẩu liên tiếp:

Attempt 1: HTTP 401 (Sai mật khẩu)
Attempt 2: HTTP 401
Attempt 3: HTTP 401
Attempt 4: HTTP 401
Attempt 5: HTTP 401
Attempt 6: HTTP 429 (Bị chặn!)
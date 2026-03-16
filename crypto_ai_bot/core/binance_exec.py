# Binance Executor Module
# Xử lý lệnh Market/Limit, setup đòn bẩy và quản lý rủi ro
import logging
import math
from binance import AsyncClient
from binance.enums import *
from binance.exceptions import BinanceAPIException
from config import config
from core.binance_client import BinanceClientManager

logger = logging.getLogger(__name__)

async def setup_margin_and_leverage(client: AsyncClient, symbol: str, leverage: int = 15):
    """Cấu hình Đòn bẩy và Margin Type (Isolated) trước khi vào lệnh."""
    try:
        # Đổi sang ISOLATED Margin (An toàn hơn Cross)
        try:
            await client.futures_change_margin_type(symbol=symbol, marginType='ISOLATED')
        except BinanceAPIException as e:
            # Lỗi -4046 nghĩa là Margin type is already isolated
            if e.code != -4046:
                raise e
                
        # Chỉnh đòn bẩy
        await client.futures_change_leverage(symbol=symbol, leverage=leverage)
        logger.info(f"⚙️ Tự động cài đặt: {symbol} | Leverage: {leverage}x | Margin: ISOLATED")
    except BinanceAPIException as e:
        logger.error(f"Lỗi setup đòn bẩy cho {symbol}: {e}")

async def calculate_quantity(client: AsyncClient, symbol: str, entry_price: float, usdt_risk: float = 10.0, leverage: int = 15) -> float:
    """Tính toán Volume (Base Asset) dựa trên số USD thực tế muốn rủi ro (Risk x Leverage)."""
    try:
        # Số tiền Margin muốn rủi ro * đòn bẩy = Size lệnh thực tế
        size_usdt = usdt_risk * leverage
        qty = size_usdt / entry_price
        
        # Get Symbol Info để làm tròn đúng thập phân của sàn
        exchange_info = await client.futures_exchange_info()
        symbol_info = next((item for item in exchange_info['symbols'] if item['symbol'] == symbol), None)
        
        if not symbol_info:
            return round(qty, 3) # fallback
            
        # Tìm filter LOT_SIZE
        lot_size_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
        if lot_size_filter:
            step_size = float(lot_size_filter['stepSize'])
            precision = int(round(-math.log10(step_size)))
            return round(qty, precision)
            
        return round(qty, 3)
    except Exception as e:
         logger.error(f"Lỗi tính volume: {e}")
         return 0

def get_side_from_action(action: str) -> str:
    return SIDE_BUY if action.upper() == 'LONG' else SIDE_SELL

def get_opposite_side(action: str) -> str:
    return SIDE_SELL if action.upper() == 'LONG' else SIDE_BUY

async def create_algo_order(client: AsyncClient, symbol: str, side: str, order_type: str, stop_price: float, quantity: float = 0, close_position: bool = False, reduce_only: bool = False):
    """
    Helper gửi lệnh Algo (STOP_MARKET, TAKE_PROFIT_MARKET) qua endpoint mới /fapi/v1/algoOrder.
    Sửa lỗi APIError(code=-4120): Order type not supported for this endpoint.
    """
    params = {
        "symbol": symbol,
        "side": side,
        "algoType": "CONDITIONAL",
        "type": order_type,
        "triggerPrice": str(stop_price),
        "timeInForce": "GTC"
    }
    
    if close_position:
        # closePosition=true KHÔNG thể dùng chung với quantity hoặc reduceOnly (Dùng khi đã có vị thế mở)
        params["closePosition"] = "true"
    else:
        if quantity > 0:
            params["quantity"] = str(quantity)
        if reduce_only:
            params["reduceOnly"] = "true"
        
    try:
        # Sử dụng phương thức low-level để gọi endpoint chưa có trong SDK chính thức
        resp = await client._request_futures_api('post', 'algoOrder', signed=True, data=params)
        return resp
    except Exception as e:
        logger.error(f"Lỗi gửi Algo Order ({order_type}): {e}")
        raise e

async def execute_trade(symbol: str, action: str, price: float, sl: float, tp: float, usdt_risk: float = 20.0):
    """
    Thực thi Lệnh LIMIT (Giá chờ) kèm sẵn TP/SL.
    """
    try:
        # Chỉ chạy lệnh nếu API Key được cấu hình
        if not config.BINANCE_API_KEY:
             logger.warning("Vui lòng cấu hình BINANCE_API_KEY để giao dịch!")
             return {"status": "error", "message": "Missing API Keys"}
             
        # Tùy chọn Trade Mode (Testnet = True nếu muốn giả lập trên sàn)
        use_testnet = (config.TRADE_MODE.lower() == "paper_trading")
        client = await BinanceClientManager.get_client()
        
        # 0. Setup Đòn bẩy 15x và Margin
        await setup_margin_and_leverage(client, symbol, leverage=15)

        # 0.5. Tính toán Quantity (Dùng 15x leverage bên trong)
        qty = await calculate_quantity(client, symbol, price, usdt_risk=usdt_risk, leverage=15)
        
        if qty <= 0:
            return {"status": "error", "message": "Số lượng lệnh quá nhỏ."}

        # 1. BẮN LỆNH GỐC (LIMIT)
        main_side = get_side_from_action(action)
        logger.info(f"Đang đặt lệnh LIMIT {action} {symbol} tại {price} | Qty: {qty}")
        
        order = await client.futures_create_order(
            symbol=symbol,
            side=main_side,
            type=ORDER_TYPE_LIMIT,
            price=str(price),
            quantity=qty,
            timeInForce=TIME_IN_FORCE_GTC
        )
        logger.info(f"Khớp {action} thành công. OrderID: {order['orderId']}")
        
        # 2. BẮN LỆNH SL/TP (REDUCE ONLY)
        # SỬA LỖI -4509: Dùng quantity + reduceOnly thay vì closePosition 
        # để có thể đặt lệnh chờ SL/TP ngay cả khi lệnh LIMIT vào chưa khớp.
        opposite_side = get_opposite_side(action)
        
        # SL - Stop Market
        if sl > 0:
            await create_algo_order(
                client=client,
                symbol=symbol,
                side=opposite_side,
                order_type=FUTURE_ORDER_TYPE_STOP_MARKET,
                stop_price=sl,
                quantity=qty,
                reduce_only=True
            )
        
        # TP - Take Profit Market
        if tp > 0:
             await create_algo_order(
                client=client,
                symbol=symbol,
                side=opposite_side,
                order_type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                stop_price=tp,
                quantity=qty,
                reduce_only=True
            )

        return {"status": "success", "order": order}

    except BinanceAPIException as e:
        logger.error(f"Binance Error ở lệnh Market: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"System Error ở lệnh Market: {e}")
        return {"status": "error", "message": str(e)}

async def execute_conditional_order(symbol: str, action: str, trigger_price: float, entry_price: float, sl: float, tp: float, usdt_risk: float = 10.0):
    """
    Đặt lệnh chờ Trigger (STOP) - Dùng 15x leverage mặc định.
    """
    try:
        client_manager = BinanceClientManager()
        client = await client_manager.get_client()

        # 0. Setup Đòn bẩy 15x và Margin
        await setup_margin_and_leverage(client, symbol, leverage=15)

        # 0.5 Tính toán Quantity
        qty = await calculate_quantity(client, symbol, entry_price, usdt_risk, leverage=15)
             
        main_side = get_side_from_action(action)
        
        # Để bắn Limit theo Trigger, Binance futures dùng STOP/TAKE_PROFIT làm lệnh kích hoạt
        # Nếu action = LONG và trigger < giá_hiện_tại -> STOP
        # (Để đơn giản luồng Bot, ta set type là STOP_MARKET nếu anh chỉ muốn khớp vùng giá quét thanh khoản)
        
        logger.info(f"Đang cài bẫy {action} {symbol} tại {trigger_price}")
        
        # Ghi chú: Binance Futures thường khóa lệnh OCO phức tạp.
        # Ở kịch bản lệnh chờ cơ bản: Bắn 1 lệnh STOP_MARKET vào họng sàn cắn mồi trước qua Algo Endpoint.
        conditional_order = await create_algo_order(
            client=client,
            symbol=symbol,
            side=main_side,
            order_type=FUTURE_ORDER_TYPE_STOP_MARKET,
            stop_price=trigger_price,
            quantity=qty
        )
        
        logger.info(f"Bẫy gài thành công. OrderID: {conditional_order['orderId']}")
        # Lưu ý: Với lệnh Conditional, SL/TP nên do Order Manager ngầm đặt SAU KHI lệnh khớp,
        # Nếu gửi luôn Reduce_only lúc vị thế (qty) đang = 0 thì nó sập.
        
        return {"status": "success", "order": conditional_order}

    except BinanceAPIException as e:
        logger.error(f"Binance Error ở lệnh Điều (Conditional): {e}")
        return {"status": "error", "message": str(e)}

async def get_open_orders():
    """Lấy danh sách các lệnh đang treo trên sàn Binance Futures."""
    try:
        if not config.BINANCE_API_KEY:
             return []
             
        use_testnet = (config.TRADE_MODE.lower() == "paper_trading")
        client = await BinanceClientManager.get_client()
        
        # Lấy tất cả lệnh đang mở (Open Orders)
        open_orders = await client.futures_get_open_orders()
        
        # Rút gọn dữ liệu trả về cho Frontend
        result = []
        for o in open_orders:
            result.append({
                "symbol": o.get("symbol"),
                "orderId": o.get("orderId"),
                "side": o.get("side"),
                "type": o.get("type"),
                "price": o.get("price"),
                "stopPrice": o.get("stopPrice"),
                "origQty": o.get("origQty"),
                "time": o.get("time")
            })
        return result
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách lệnh chờ: {e}")
        return []
async def get_balance():
    """Lấy số dư USDT/USDC khả dụng trong ví Futures."""
    try:
        if not config.BINANCE_API_KEY:
             return 0.0
             
        use_testnet = (config.TRADE_MODE.lower() == "paper_trading")
        client = await BinanceClientManager.get_client()
        
        account_info = await client.futures_account()
        assets = account_info.get('assets', [])
        
        total_balance = 0.0
        for asset in assets:
            if asset['asset'] in ['USDT', 'USDC']:
                total_balance += float(asset['walletBalance'])
                
        return round(total_balance, 2)
    except Exception as e:
        logger.error(f"Lỗi khi lấy số dư: {e}")
        return 0.0

async def get_open_positions():
    """Lấy danh sách các vị thế đang mở và tính toán PnL."""
    try:
        if not config.BINANCE_API_KEY:
            return []
            
        client = await BinanceClientManager.get_client()
        account_info = await client.futures_account()
        positions = account_info.get('positions', [])
        
        active_positions = []
        for p in positions:
            pa = float(p.get('positionAmt', 0))
            if pa != 0:
                entry_price = float(p.get('entryPrice', 0))
                mark_price = float(p.get('markPrice', 0))
                unrealized_pnl = float(p.get('unrealizedProfit', 0))
                leverage = int(p.get('leverage', 1))
                
                # Tính % ROI (RoE)
                roi = 0
                if entry_price > 0:
                    side = 1 if pa > 0 else -1
                    roi = (mark_price - entry_price) / entry_price * 100 * leverage * side
                
                active_positions.append({
                    "symbol": p.get('symbol'),
                    "positionAmt": pa,
                    "entryPrice": entry_price,
                    "markPrice": mark_price,
                    "unrealizedPnL": round(unrealized_pnl, 2),
                    "roi": round(roi, 2),
                    "leverage": leverage,
                    "side": "LONG" if pa > 0 else "SHORT"
                })
        return active_positions
    except Exception as e:
        logger.error(f"Lỗi khi lấy vị thế: {e}")
        return []

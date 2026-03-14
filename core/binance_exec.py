# Binance Executor Module
# Xử lý lệnh Market/Limit, setup đòn bẩy vàimport logging
import math
from binance import AsyncClient
from binance.enums import *
from binance.exceptions import BinanceAPIException
from config import config

logger = logging.getLogger(__name__)

async def setup_margin_and_leverage(client: AsyncClient, symbol: str, leverage: int = 20):
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

async def calculate_quantity(client: AsyncClient, symbol: str, entry_price: float, usdt_risk: float = 20.0, leverage: int = 20) -> float:
    """Tính toán Volume (Base Asset) dựa trên số USD muốn đánh (mặc định đánh lệnh 20$ x đòn bẩy)."""
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

async def execute_trade(symbol: str, action: str, price: float, sl: float, tp: float):
    """
    Thực thi Lệnh Market tức thì kèm sẵn TP/SL.
    """
    try:
        # Chỉ chạy lệnh nếu API Key được cấu hình
        if not config.BINANCE_API_KEY:
             logger.warning("Vui lòng cấu hình BINANCE_API_KEY để giao dịch!")
             return {"status": "error", "message": "Missing API Keys"}
             
        # Tùy chọn Trade Mode (Testnet = True nếu muốn giả lập trên sàn)
        use_testnet = (config.TRADE_MODE.lower() == "paper_trading")
        client = await AsyncClient.create(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=use_testnet)
        
        await setup_margin_and_leverage(client, symbol, leverage=20)
        qty = await calculate_quantity(client, symbol, price, usdt_risk=20.0) # test mặc định lệnh 20$
        
        if qty <= 0:
            await client.close_connection()
            return {"status": "error", "message": "Số lượng lệnh quá nhỏ."}

        # 1. BẮN LỆNH GỐC (MARKET)
        main_side = get_side_from_action(action)
        logger.info(f"Đang đâm Market {action} {symbol} SL: {qty}")
        
        order = await client.futures_create_order(
            symbol=symbol,
            side=main_side,
            type=ORDER_TYPE_MARKET,
            quantity=qty
        )
        logger.info(f"Khớp {action} thành công. OrderID: {order['orderId']}")
        
        # 2. BẮN LỆNH SL/TP (REDUCE ONLY)
        opposite_side = get_opposite_side(action)
        
        # SL - Stop Market
        if sl > 0:
            await client.futures_create_order(
                symbol=symbol,
                side=opposite_side,
                type=ORDER_TYPE_STOP_MARKET,
                stopPrice=sl,
                closePosition="true", # Tự động quy qty về vị thế hiện tại
                timeInForce=TIME_IN_FORCE_GTC
            )
        
        # TP - Take Profit Market
        if tp > 0:
             await client.futures_create_order(
                symbol=symbol,
                side=opposite_side,
                type=ORDER_TYPE_TAKE_PROFIT_MARKET,
                stopPrice=tp,
                closePosition="true",
                timeInForce=TIME_IN_FORCE_GTC
            )

        await client.close_connection()
        return {"status": "success", "order": order}

    except BinanceAPIException as e:
        logger.error(f"Binance Error ở lệnh Market: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"System Error ở lệnh Market: {e}")
        return {"status": "error", "message": str(e)}

async def execute_conditional_order(symbol: str, action: str, trigger_price: float, entry_price: float, sl: float, tp: float):
    """
    Thực thi Lệnh CĂN GIÁ (Nằm vùng trên sàn).
    sử dụng STOP_MARKET / TAKE_PROFIT_MARKET để kích hoạt.
    """
    try:
        if not config.BINANCE_API_KEY:
             return {"status": "error", "message": "Missing API Keys"}
             
        use_testnet = (config.TRADE_MODE.lower() == "paper_trading")
        client = await AsyncClient.create(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=use_testnet)
        
        await setup_margin_and_leverage(client, symbol, leverage=20)
        qty = await calculate_quantity(client, symbol, entry_price, usdt_risk=20.0) 
        
        main_side = get_side_from_action(action)
        
        # Để bắn Limit theo Trigger, Binance futures dùng STOP/TAKE_PROFIT làm lệnh kích hoạt
        # Nếu action = LONG và trigger < giá_hiện_tại -> STOP
        # (Để đơn giản luồng Bot, ta set type là STOP_MARKET nếu anh chỉ muốn khớp vùng giá quét thanh khoản)
        
        logger.info(f"Đang cài bẫy {action} {symbol} tại {trigger_price}")
        
        # Ghi chú: Binance Futures thường khóa lệnh OCO phức tạp.
        # Ở kịch bản lệnh chờ cơ bản: Bắn 1 lệnh STOP_MARKET vào họng sàn cắn mồi trước.
        conditional_order = await client.futures_create_order(
            symbol=symbol,
            side=main_side,
            type=ORDER_TYPE_STOP_MARKET,
            stopPrice=trigger_price, # Giá chạm để kích hoạt
            quantity=qty,
            timeInForce=TIME_IN_FORCE_GTC
        )
        
        logger.info(f"Bẫy gài thành công. OrderID: {conditional_order['orderId']}")
        # Lưu ý: Với lệnh Conditional, SL/TP nên do Order Manager ngầm đặt SAU KHI lệnh khớp,
        # Nếu gửi luôn Reduce_only lúc vị thế (qty) đang = 0 thì nó sập.
        
        await client.close_connection()
        return {"status": "success", "order": conditional_order}

    except BinanceAPIException as e:
        logger.error(f"Binance Error ở lệnh Điều (Conditional): {e}")
        return {"status": "error", "message": str(e)}

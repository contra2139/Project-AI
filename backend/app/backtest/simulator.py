from decimal import Decimal
from typing import Dict, Tuple

class FillSimulator:
    """
    Mô phỏng việc khớp lệnh và tính toán chi phí trong Backtest.
    """

    def simulate_entry_fill(
        self,
        entry_bar: Dict,
        side: str,
        atr_value: Decimal,
        slippage_atr_pct: Decimal = Decimal("0.05")
    ) -> Decimal:
        """
        Tính giá khớp lệnh (Entry) dựa trên giá Open và Slippage.
        """
        base_price = Decimal(str(entry_bar["open"]))
        slippage = atr_value * slippage_atr_pct
        
        if side == "LONG":
            return base_price + slippage
        else: # SHORT
            return base_price - slippage

    def simulate_stop_hit(
        self,
        trade_side: str,
        stop_price: Decimal,
        bar: Dict
    ) -> Tuple[bool, Decimal]:
        """
        Kiểm tra xem giá có chạm mức Stop Loss trong nến hiện tại không.
        """
        low = Decimal(str(bar["low"]))
        high = Decimal(str(bar["high"]))
        
        if trade_side == "LONG":
            if low <= stop_price:
                return True, stop_price
        else: # SHORT
            if high >= stop_price:
                return True, stop_price
                
        return False, Decimal("0")

    def simulate_partial_fill(
        self,
        trade_side: str,
        tp1_price: Decimal,
        bar: Dict
    ) -> Tuple[bool, Decimal]:
        """
        Kiểm tra xem giá có chạm mức Take Profit 1 (1R) trong nến hiện tại không.
        """
        low = Decimal(str(bar["low"]))
        high = Decimal(str(bar["high"]))
        
        if trade_side == "LONG":
            if high >= tp1_price:
                return True, tp1_price
        else: # SHORT
            if low <= tp1_price:
                return True, tp1_price
                
        return False, Decimal("0")

    def calculate_fees(
        self,
        qty: Decimal,
        fill_price: Decimal,
        taker_fee_pct: Decimal = Decimal("0.0005") # 0.05% Taker Fee
    ) -> Decimal:
        """
        Tính phí giao dịch Taker.
        """
        return qty * fill_price * taker_fee_pct

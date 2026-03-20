import pandas as pd
import numpy as np
from typing import Optional
from scipy import stats

class FeatureEngine:
    """
    FeatureEngine chịu trách nhiệm tính toán các chỉ số kỹ thuật (Indicators)
    và xếp hạng Percentile (xếp hạng phần trăm) dựa trên dữ liệu lịch sử.
    
    Mục tiêu: Loại bỏ sự phụ thuộc vào giá trị tuyệt đối, chuyển sang giá trị tương đối
    để bot có thể hiểu được "Độ biến động hiện tại là cao hay thấp so với quá khứ".
    """

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Tính Average True Range (ATR) chuẩn."""
        high = df['high']
        low = df['low']
        close_prev = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close_prev)
        tr3 = abs(low - close_prev)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        # Sử dụng RMA (Running Moving Average) giống TradingView cho ATR chuẩn
        return tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    @staticmethod
    def calculate_bb_width(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.Series:
        """Tính Bollinger Band Width %."""
        ma = df['close'].rolling(window=period).mean()
        std_dev = df['close'].rolling(window=period).std()
        upper = ma + (std_dev * std)
        lower = ma - (std_dev * std)
        # (Upper - Lower) / Middle * 100
        return (upper - lower) / ma * 100

    def compute_features(self, df: pd.DataFrame, atr_period: int = 14) -> pd.DataFrame:
        """
        Tính toán bộ feature thô (Raw Features).
        """
        res = df.copy()
        
        # 1. ATR và ATR Normalized (Biến động dựa trên ATR)
        res['atr'] = self.calculate_atr(df, period=atr_period)
        res['atr_norm'] = (res['atr'] / res['close']) * 100
        
        # 2. Range % (Độ lớn cây nến hiện tại)
        res['range_pct'] = ((res['high'] - res['low']) / res['close']) * 100
        
        # 3. Bollinger Band Width (Độ thắt nút cổ chai)
        res['bb_width'] = self.calculate_bb_width(df)
        
        # 4. Volume Ratio (Khối lượng so với trung bình)
        res['vol_sma'] = res['volume'].rolling(window=20).mean()
        res['vol_ratio'] = res['volume'] / res['vol_sma']

        # 5. EMA Context (Needed for ContextFilter)
        res['ema50'] = res['close'].ewm(span=50, adjust=False).mean()
        # Slope: (current - prev) / prev
        ema_prev = res['ema50'].shift(1)
        res['ema50_slope'] = (res['ema50'] - ema_prev) / ema_prev
        
        # 6. Realized Volatility (Needed for ContextFilter)
        # 1h returns, annualized (approx 24*365 bars)
        returns = res['close'].pct_change()
        res['realized_vol_1h'] = returns.rolling(window=24).std() * np.sqrt(24 * 365)
        
        return res

    def calculate_percentiles(self, df: pd.DataFrame, window: int = 120) -> pd.DataFrame:
        """
        Tính toán xếp hạng Percentile cho các features.
        Window mặc định là 120 nến (tương đương khoảng 30 giờ với nến 15m).
        """
        target_cols = ['atr_norm', 'range_pct', 'bb_width', 'vol_ratio']
        
        for col in target_cols:
            pct_col = f"{col}_pct"
            # Optimized Rolling Rank: (rank / window) * 100
            # rolling().rank() is much faster (O(N*logW)) than apply(percentileofscore) (O(N*W))
            df[pct_col] = (df[col].rolling(window=window).rank() / window) * 100
            
        return df

    def get_market_state(self, df: pd.DataFrame, symbol: str) -> dict:
        """
        Lấy snapshot trạng thái thị trường hiện tại cho một mã.
        """
        if df.empty:
            return {}
            
        latest = df.iloc[-1]
        
        return {
            "symbol": symbol,
            "time": latest.name if hasattr(latest, 'name') else None,
            "close": float(latest['close']),
            "features": {
                "atr_percentile": float(latest.get('atr_norm_pct', 0)),
                "range_percentile": float(latest.get('range_pct_pct', 0)),
                "bb_width_percentile": float(latest.get('bb_width_pct', 0)),
                "volume_percentile": float(latest.get('vol_ratio_pct', 0))
            }
        }

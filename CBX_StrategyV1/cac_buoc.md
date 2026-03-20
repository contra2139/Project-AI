Timeframe và phạm vi giao dịch

Mình đề xuất bản đầu tiên như sau:

Universe

BTCUSDC

BNBUSDC

SOLUSDC

Timeframe nghiên cứu / vào lệnh

15m làm execution timeframe

1h làm context timeframe

Lý do:

15m đủ nhiều event để thống kê

không quá nhiễu như 1m–5m

1h giúp lọc các compression event quá nhỏ và vô nghĩa

Chế độ ban đầu

test LONG và SHORT riêng hoàn toàn

không gộp logic

nếu kết quả LONG xấu, có thể triển khai SHORT-only ở giai đoạn đầu

4) Định nghĩa event chuẩn cho chiến lược

Đây là phần quan trọng nhất.

A. Compression Event

Compression không được định nghĩa cảm tính.
Nó phải là một vùng nén biến động đo được.

Dùng 4 chỉ số:

1. ATR Compression

ATR(14) / Close

lấy percentile rolling 90–120 bars

điều kiện:

ATR normalized nằm trong bottom 20%

2. Range Compression

range_n = (highest_high(n) - lowest_low(n)) / close

với n = 12 bars (15m => 3 giờ)

điều kiện:

range_12 nằm trong bottom 20% của rolling history

3. Bollinger Bandwidth Compression

BB width / close

điều kiện:

nằm trong bottom 20%

4. Volume Quietness

volume SMA ngắn / volume SMA dài hoặc percentile volume

điều kiện:

volume không được spike bất thường trước breakout

volume percentile <= 60% trong vùng nén

Compression Zone được xác nhận khi:

ít nhất 3/4 điều kiện đúng

kéo dài tối thiểu 8 bars

tối đa 24 bars

biên độ vùng nén không vượt quá một ngưỡng normalize theo ATR

Output của Compression Event

Bot phải lưu:

start_time

end_time

compression_high

compression_low

compression_width

atr_value

atr_percentile

range_percentile

bb_width_percentile

volume_percentile

symbol

timeframe

B. Breakout Event

Breakout chỉ hợp lệ nếu có một nến phá vùng nén đủ mạnh.

Breakout LONG hợp lệ khi:

close > compression_high

breakout distance >= 0.20 x ATR(14)

candle body / full range >= 0.60

close nằm trong top 25% của chính cây nến

volume >= 1.3 x SMA(volume, 20) hoặc volume percentile >= 70

không phải nến wick-dominant

Breakout SHORT hợp lệ khi:

close < compression_low

breakout distance >= 0.20 x ATR(14)

candle body / full range >= 0.60

close nằm trong bottom 25% của cây nến

volume >= 1.3 x SMA(volume, 20) hoặc volume percentile >= 70

không phải nến wick-dominant

Event invalid nếu:

phá vỡ nhưng close quay lại trong vùng nén

wick dài mà body yếu

breakout xảy ra sau compression quá dài và đã “rò” biên nhiều lần

breakout bar quá lớn > 2.5 ATR, vì dễ bị exhaustion

C. Expansion Confirmation

Đây là phần giúp tránh false breakout.

Sau breakout bar, chỉ vào lệnh nếu có follow-through trong 1–3 bars tiếp theo.

LONG expansion confirmation:

ít nhất 1 trong 2 điều kiện:

bar tiếp theo tạo higher high và không đóng lại vào range

hoặc trong 2 bars tiếp theo, giá giữ trên breakout level và không thủng 50% breakout candle body

SHORT expansion confirmation:

ít nhất 1 trong 2 điều kiện:

bar tiếp theo tạo lower low và không đóng lại vào range

hoặc trong 2 bars tiếp theo, giá giữ dưới breakout level và không vượt 50% breakout candle body

5) Entry model: vào lệnh thế nào?

Mình khuyên bạn test 2 mẫu entry tách biệt, không trộn:

Entry Model 1 — Immediate Follow-through Entry

Phù hợp với breakout mạnh, momentum rõ.

LONG

Vào lệnh ở:

open của bar kế tiếp sau khi expansion confirmation xuất hiện
hoặc

stop order trên đỉnh breakout/confirmation bar một khoảng nhỏ

SHORT

Tương tự theo chiều ngược lại.

Ưu điểm

bắt được move mạnh

đơn giản, rõ ràng

Nhược điểm

dễ bị mua đuổi / bán đuổi

Entry Model 2 — Retest Entry

Phù hợp với breakout có xác nhận rồi quay lại test vùng phá vỡ.

LONG

Sau breakout hợp lệ:

chờ trong tối đa 3 bars

nếu giá retest lại compression_high hoặc vùng breakout level

và không đóng dưới vùng invalidation

thì vào LONG khi bar retest cho tín hiệu giữ vững

SHORT

Ngược lại với compression_low

Ưu điểm

RR tốt hơn

giảm adverse selection

Nhược điểm

bỏ lỡ nhiều move mạnh không retest

Khuyến nghị triển khai

Bot v1 nên backtest hai phiên bản độc lập:

CBX_FT = follow-through entry

CBX_RT = retest entry

Không gộp.

6) Stop loss, take profit, exit logic

Không dùng TP/SL kiểu cảm tính.
Exit phải phản ánh đúng logic event-driven.

Stop loss
LONG

Stop đặt tại giá nào thấp hơn trong 2 mức:

dưới compression_high một khoảng 0.25 x ATR

hoặc dưới low của breakout confirmation structure

SHORT

Ngược lại:

trên compression_low một khoảng 0.25 x ATR

hoặc trên high của breakout confirmation structure

Hard invalidation

Nếu giá quay lại sâu vào vùng nén, hypothesis breakout thất bại.

Profit-taking / Exit

Backtest riêng các exit sau:

Exit Model A — Fixed R multiple

chốt 50% ở 1R

phần còn lại trailing theo 2-bar low/high hoặc ATR trail

Exit Model B — Time-based exit

nếu sau 8 bars chưa đạt 1R và momentum suy yếu => thoát

tránh bị kẹt trong failed expansion

Exit Model C — Structure failure exit

breakout thất bại nếu:

LONG: close lại trong compression zone

SHORT: close lại trong compression zone
=> thoát toàn bộ

Khuyến nghị

Test 3 exit model riêng.
Đừng đoán trước cái nào tốt.

7) Bộ lọc bắt buộc và bộ lọc cấm

Chiến lược mới phải cực kỳ kỷ luật.

Bộ lọc bắt buộc
1. Compression phải có thật

Không có compression chuẩn => không trade.

2. Breakout phải có close xác nhận

Chỉ wick phá range => bỏ.

3. Có expansion confirmation

Không có follow-through => bỏ.

4. Không được có no-trigger entry

Điểm này cực kỳ quan trọng vì audit cũ cho thấy nhóm này phá bot.

Bot mới tuyệt đối cấm mọi kiểu vào lệnh “gần đúng”, “sắp breakout”, “có vẻ sắp đi”.

Bộ lọc cấm
Không trade khi:

breakout bar quá lớn > 2.5 ATR

compression zone quá rộng, thực chất không còn là nén

breakout xảy ra ngay trước funding/reset/session event lớn nếu bạn có data đó

trong 10 bars gần nhất đã có 2 lần false break cùng vùng

spread/slippage bất thường

volume breakout quá thấp

8) Context filter tối thiểu

Bạn nói muốn bot mới hoàn toàn, nên mình khuyên context filter phải rất ít.

Chỉ dùng 2 filter bối cảnh, đủ nhẹ nhưng có ích:

Filter 1 — 1h Directional Bias

Không phải để “dự đoán xu hướng”, chỉ để tránh đánh ngược hoàn toàn với bối cảnh.

LONG chỉ cho phép nếu:

close 1h >= EMA50 1h

và EMA50 dốc không âm mạnh

SHORT chỉ cho phép nếu:

close 1h <= EMA50 1h

và EMA50 dốc không dương mạnh

Đây là filter nhẹ. Không biến nó thành trend engine.

Filter 2 — 1h Volatility State

Không trade nếu 1h đang ở trạng thái:

realized volatility cực thấp kéo dài nhưng breakout 15m quá nhỏ
hoặc

volatility cực cao kiểu shock regime khiến breakout event mất ý nghĩa

Mục tiêu là tránh 2 đầu thái cực.
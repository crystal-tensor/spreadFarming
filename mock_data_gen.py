import csv
from datetime import datetime, timedelta
import spreadFarming

capital = 10000.0

with open('simulation_trades.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'market_id', 'yes_price', 'no_price', 'fee_rate', 'total_cost', 'expected_revenue', 'net_profit', 'yield_rate', 'capital_after'])
    
    # 模拟过去30天的30次交易数据
    for i in range(30):
        dt = datetime.now() - timedelta(days=30-i, hours=i*2)
        
        # 模拟一笔交易的细节
        # 总价加起来应该接近1但小于1
        yes_price = 0.45
        no_price = 0.53
        fee_rate = 0.02 # 2% (200 bps)
        
        # 1000份YES和1000份NO
        shares = 1000.0
        
        # 计算逻辑更新
        total_cost_before_fee = shares * yes_price + shares * no_price
        fee_est = total_cost_before_fee * (fee_rate / 100) # 这里fee_rate是百分比，所以除以100
        # 修正：fee_rate如果是0.02 (2%)，则 fee_est = total * 0.02
        # 注意 spreadFarming 中用的是 bps / 10000
        
        # 这里为了 mock 数据简单，直接按 2% 算
        fee_est = total_cost_before_fee * 0.02
        
        total_cost = total_cost_before_fee + fee_est
        
        expected_revenue = shares * 1.0 # 1000份必赢一份
        
        # 随机加一点利润波动
        net_profit = expected_revenue - total_cost + (i % 5) * 2.5
        yield_rate = (net_profit / total_cost) * 100
        
        capital += net_profit
        
        writer.writerow([
            dt.strftime("%Y-%m-%d %H:%M:%S"),
            f"mock_market_0x{i}ABC",
            yes_price, no_price, fee_rate, total_cost, expected_revenue, net_profit, yield_rate, capital
        ])

# 调用现有的方法生成HTML
spreadFarming.generate_html_report()
print("Mock data and HTML report generated successfully.")
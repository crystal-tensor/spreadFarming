import os
import time
import requests
import json
import csv
from datetime import datetime
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

load_dotenv()

import sys
import binascii

# ================== 配置 ==================
HOST = "https://clob.polymarket.com"
CHAIN_ID = 137
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "").strip()
FUNDER = os.getenv("FUNDER", "").strip()

# 交易配置
TRADE_SHARES = 1000.0      # 每次发现机会，固定买入1000份YES和1000份NO
TARGET_SPREAD = 0.01       # 目标毛利空间 (例如 1 - 0.99 = 0.01)

# 模拟交易记录配置
SIMULATION_MODE = False
TRADE_LOG_FILE = "live_trading_report.csv"
HTML_REPORT_FILE = "live_trading_report.html"

# 初始模拟资金
INITIAL_CAPITAL = 10000.0
current_capital = INITIAL_CAPITAL

if not PRIVATE_KEY or not FUNDER:
    print("❌ 错误: 未在 .env 文件中设置 PRIVATE_KEY 或 FUNDER。")
    print("请打开 .env 文件并填入您的 Polymarket 私钥和钱包地址。")
    sys.exit(1)

if PRIVATE_KEY.startswith("your_") or FUNDER.startswith("your_"):
    print(f"❌ 错误: 检测到 .env 文件 ({os.path.abspath('.env')}) 中仍包含默认占位符。")
    print("请使用真实的私钥和地址替换 'your_private_key_here' 和 'your_funder_address_here'。")
    print("提示: 私钥通常以 0x 开头，地址也是。")
    sys.exit(1)

try:
    client = ClobClient(HOST, key=PRIVATE_KEY, chain_id=CHAIN_ID, funder=FUNDER)
    client.set_api_creds(client.create_or_derive_api_creds())
except binascii.Error:
    print("❌ 错误: PRIVATE_KEY 格式不正确。")
    print("私钥必须是有效的十六进制字符串 (Hex string)。请检查 .env 文件。")
    sys.exit(1)
except Exception as e:
    print(f"❌ 初始化客户端失败: {e}")
    sys.exit(1)

# ================== 核心函数 ==================
def init_csv():
    if not os.path.exists(TRADE_LOG_FILE):
        with open(TRADE_LOG_FILE, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'market_id', 'yes_price', 'no_price', 'fee_rate', 'total_cost', 'expected_revenue', 'net_profit', 'yield_rate', 'capital_after'])

def get_active_markets():
    # 使用 clob API 获取市场，这样可以包含 taker_base_fee 等信息
    url = "https://clob.polymarket.com/markets"
    params = {"active": "true", "closed": "false"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        markets = resp.json().get('data', [])
        # 只保留包含2个token的市场
        valid_markets = []
        for m in markets:
            if len(m.get("tokens", [])) == 2:
                valid_markets.append(m)
        return valid_markets
    except Exception as e:
        print(f"获取市场失败: {e}")
        return []

def get_best_asks(yes_token: str, no_token: str):
    try:
        book_yes = client.get_order_book(yes_token)
        book_no = client.get_order_book(no_token)
        ask_yes = float(book_yes["asks"][0]["price"]) if book_yes.get("asks") else 1.0
        ask_no = float(book_no["asks"][0]["price"]) if book_no.get("asks") else 1.0
        return ask_yes, ask_no
    except:
        return 1.0, 1.0

def generate_html_report():
    if not os.path.exists(TRADE_LOG_FILE):
        return

    timestamps = []
    capitals = []
    trades_html = ""
    
    with open(TRADE_LOG_FILE, mode='r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamps.append(row['timestamp'])
            capitals.append(float(row['capital_after']))
            
            # 组装表格行
            # 兼容旧数据（如果缺少yield_rate列）
            try:
                yield_rate = float(row.get('yield_rate', 0))
            except:
                yield_rate = 0.0
                
            trades_html += f"""
                <tr>
                    <td>{row['timestamp']}</td>
                    <td><span title="{row['market_id']}">{row['market_id'][:10]}...</span></td>
                    <td>${float(row['yes_price']):.4f}</td>
                    <td>${float(row['no_price']):.4f}</td>
                    <td>{float(row['fee_rate'])*100:.2f}%</td>
                    <td>${float(row['total_cost']):.2f}</td>
                    <td>${float(row['expected_revenue']):.2f}</td>
                    <td style="color: {'green' if float(row['net_profit']) > 0 else 'red'}">
                        ${float(row['net_profit']):.2f}
                    </td>
                    <td style="color: {'green' if yield_rate > 0 else 'red'}">
                        {yield_rate:.2f}%
                    </td>
                    <td>${float(row['capital_after']):.2f}</td>
                </tr>
            """
            
    if not timestamps:
        # 如果没有交易数据，使用默认值
        current_capital = INITIAL_CAPITAL
        total_yield = 0.0
    else:
        current_capital = capitals[-1]
        total_yield = (current_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    # 简单生成 HTML 报告，使用 Chart.js
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>Polymarket 实盘交易收益报告</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f4f7f6; color: #333; }}
            .container {{ max-width: 1000px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
            canvas {{ background: #fff; border-radius: 8px; margin-bottom: 30px; }}
            .stats {{ display: flex; justify-content: space-between; margin-bottom: 20px; padding: 15px; background: #eef; border-radius: 8px; font-size: 1.1em; }}
            .stats div {{ text-align: center; }}
            h2, h3 {{ color: #2c3e50; text-align: center; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9em; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
            th {{ background-color: #f8f9fa; font-weight: bold; position: sticky; top: 0; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            tr:hover {{ background-color: #f1f1f1; }}
            .table-container {{ max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Polymarket 价差套利实盘收益报告</h2>
            <div class="stats">
                <div><strong>初始资金</strong><br>${INITIAL_CAPITAL:.2f}</div>
                <div><strong>当前资金</strong><br>${current_capital:.2f}</div>
                <div><strong>总收益率</strong><br>{total_yield:.2f}%</div>
                <div><strong>交易次数</strong><br>{len(timestamps)}</div>
            </div>
            
            <canvas id="yieldChart"></canvas>

            <h3>交易明细</h3>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>市场ID</th>
                            <th>YES 价格</th>
                            <th>NO 价格</th>
                            <th>费率</th>
                            <th>总成本</th>
                            <th>预期收入</th>
                            <th>净利润</th>
                            <th>收益率</th>
                            <th>账户余额</th>
                        </tr>
                    </thead>
                    <tbody>
                        {trades_html}
                    </tbody>
                </table>
            </div>
        </div>
        <script>
            const ctx = document.getElementById('yieldChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(timestamps)},
                    datasets: [{{
                        label: '账户净值 (USD)',
                        data: {json.dumps(capitals)},
                        borderColor: '#2980b9',
                        backgroundColor: 'rgba(41, 128, 185, 0.2)',
                        borderWidth: 2,
                        pointRadius: 3,
                        tension: 0.1,
                        fill: true
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ position: 'top' }}
                    }},
                    scales: {{
                        x: {{ display: false }}, // 隐藏x轴标签以免太拥挤
                        y: {{ beginAtZero: false }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    with open(HTML_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)

def execute_arb(market_info, ask_yes: float, ask_no: float, fee_rate: float):
    global current_capital
    
    yes_token = market_info["tokens"][0]["token_id"]
    no_token = market_info["tokens"][1]["token_id"]
    market_id = market_info.get("condition_id", "unknown")
    
    # 按照策略：固定买入 1000 份 yes 和 1000 份 no
    shares_to_buy = TRADE_SHARES 
    
    cost_yes = shares_to_buy * ask_yes
    cost_no = shares_to_buy * ask_no
    total_cost_before_fee = cost_yes + cost_no
    
    # 手续费计算 (fee_rate 通常是 bps，比如 200 = 2%)
    fee_percentage = fee_rate / 10000.0
    fee_est = total_cost_before_fee * fee_percentage
    
    total_cost = total_cost_before_fee + fee_est
    
    # 因为买入了相同数量的 yes 和 no，必定有一个会赢，且赢得的金额就是 shares_to_buy * 1.0
    expected_revenue = shares_to_buy 
    
    net_profit = expected_revenue - total_cost
    yield_rate = (net_profit / total_cost) * 100

    print(f"🚀 发现机会！YES {ask_yes:.4f} + NO {ask_no:.4f}")
    print(f"   市场: {market_info.get('question', market_id)}")
    print(f"   手续费率: {fee_percentage*100:.2f}%")
    print(f"   购买 {shares_to_buy} 份。总成本: ${total_cost:.2f} | 预期收入: ${expected_revenue:.2f}")
    print(f"   预期净利润: ${net_profit:.2f} | 收益率: {yield_rate:.2f}%")

    if SIMULATION_MODE:
        current_capital += net_profit
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 记录到CSV
        with open(TRADE_LOG_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, market_id, ask_yes, ask_no, fee_percentage, total_cost, expected_revenue, net_profit, yield_rate, current_capital])
            
        print(f"✅ 实盘交易记录成功！当前资金: ${current_capital:.2f}\n")
        generate_html_report()
    else:
        # 真实交易逻辑
        try:
            # YES
            mo_yes = MarketOrderArgs(token_id=yes_token, amount=cost_yes, side=BUY, order_type=OrderType.FOK)
            signed_yes = client.create_market_order(mo_yes)
            resp_yes = client.post_order(signed_yes, OrderType.FOK)
            print("✅ YES 买入请求发送")

            # NO
            mo_no = MarketOrderArgs(token_id=no_token, amount=cost_no, side=BUY, order_type=OrderType.FOK)
            signed_no = client.create_market_order(mo_no)
            resp_no = client.post_order(signed_no, OrderType.FOK)
            print("✅ NO 买入请求发送")
            
            # 更新本地统计并记录
            current_capital += net_profit
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 记录到CSV
            with open(TRADE_LOG_FILE, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, market_id, ask_yes, ask_no, fee_percentage, total_cost, expected_revenue, net_profit, yield_rate, current_capital])
                
            print(f"💰 本次锁定净利润约 ${net_profit:.2f} USDC")
            print(f"📈 当前模拟累计资金: ${current_capital:.2f}\n")
            generate_html_report()
            
        except Exception as e:
            print(f"❌ 交易失败: {e}")

# ================== 主循环 ==================
def main():
    print("🤖 Polymarket 价差套利机器人启动（实盘交易版）...", flush=True)
    init_csv()
    
    while True:
        try:
            markets = get_active_markets()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在扫描 {len(markets)} 个市场...", flush=True)
            
            scanned_batch = []
            last_print_time = time.time()
            
            for i, m in enumerate(markets):
                yes_token = m["tokens"][0]["token_id"]
                no_token = m["tokens"][1]["token_id"]
                
                # 记录已扫描的市场
                scanned_batch.append(m.get('question', 'Unknown'))
                
                # 每5分钟输出一次扫描过的最后100个市场
                if time.time() - last_print_time >= 300:
                    recent_markets = scanned_batch[-100:]
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 过去5分钟共扫描了 {len(scanned_batch)} 个市场，以下是最后 {len(recent_markets)} 个:", flush=True)
                    for name in recent_markets:
                        print(f"  - {name}", flush=True)
                    print("-" * 50, flush=True)
                    scanned_batch = []  # 清空列表，准备下一批
                    last_print_time = time.time()
                
                # 获取该市场的手续费率，taker_base_fee 通常是 bps，例如 200 表示 2%
                # 某些 API 响应可能没有这个字段，默认 0
                fee_rate_bps = float(m.get("taker_base_fee", 0))
                
                ask_yes, ask_no = get_best_asks(yes_token, no_token)
                
                # 计算总成本（价格+手续费）
                # 买入1000份YES和1000份NO的总成本 = (ask_yes + ask_no) * 1000 * fee_multiplier
                # 期望收益 = 1000.0 (因为必然有一个赢)
                
                fee_multiplier = 1 + (fee_rate_bps / 10000.0)
                total_cost_per_share = (ask_yes + ask_no) * fee_multiplier
                
                # 只要单份的总成本小于预期收益(1)减去我们要求的目标利润率，就交易
                if total_cost_per_share <= (1.0 - TARGET_SPREAD):
                    execute_arb(m, ask_yes, ask_no, fee_rate_bps)
            
            # 为了防止被封IP或资源消耗过大，增加轮询间隔
            time.sleep(10)
        except Exception as e:
            print(f"⚠️ 错误: {e}", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    # 为了让 nohup 输出不被缓冲
    sys.stdout.reconfigure(line_buffering=True)
    main()

# Polymarket Spread Farmer (Live Trading)

A Python bot that scans Polymarket for spread arbitrage opportunities (Buy YES + Buy NO < 1.0) and executes live trades. It also includes a web dashboard to view real-time performance.

## Features

- **Automated Scanning**: Scans active markets for price discrepancies.
- **Live Trading**: Automatically buys YES and NO shares when the combined cost is less than 1.0 (minus fees).
- **Profit Tracking**: Logs every trade to a CSV file.
- **Real-time Dashboard**: A local web server (`live_trading_report.html`) to visualize PnL and trade history.

## Prerequisites

- Python 3.11+
- Node.js & npm (for the dashboard)
- A Polymarket account with funds (USDC on Polygon).
- An EOA wallet (private key) authorized on Polymarket.

## Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd polymarket-spread-farmer
   ```

2. **Install Python dependencies**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies (for UI)**
   ```bash
   npm install
   ```

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your credentials:
   - `PRIVATE_KEY`: Your Polygon wallet private key (starts with `0x`).
   - `FUNDER`: Your wallet address.

## Usage

### 1. Start the Trading Bot
Run the Python script in the background. It will scan markets and execute trades.

```bash
nohup ./.venv/bin/python spreadFarming.py > simulation.log 2>&1 &
```
- Logs are written to `simulation.log`.
- Trades are recorded in `live_trading_report.csv`.

### 2. Start the Dashboard
Launch the local web server to view your trading report.

```bash
npm run dev
```
- Open `http://localhost:61522/live_trading_report.html` in your browser.
- The page updates automatically as new trades occur.

## Strategy

- **Logic**: The bot looks for markets where `Ask(YES) + Ask(NO) + Fees < 1.0`.
- **Execution**: If an opportunity is found, it buys 1000 shares of YES and 1000 shares of NO.
- **Profit**: Since one outcome must win (payout $1.0), the profit is `1.0 - Total Cost`.

## Disclaimer

This software is for educational purposes only. Use it at your own risk. The authors are not responsible for any financial losses.

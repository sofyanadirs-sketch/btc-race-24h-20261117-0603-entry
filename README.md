# btc-race-24h-20261117-0603-entry

[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/sofyanadirs-sketch/btc-race-24h-20261117-0603-entry/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/sofyanadirs-sketch/btc-race-24h-20261117-0603-entry/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

A BTC trading bot for make.fun's "Race a BTC trading bot live for 24 hours" bounty. It trades Coinbase Wrapped BTC (CBBTC) against USDC on 1-minute bars, long only, from 1,000 USDC of paper money. Strategy: SMA dip-reversion — buy with all cash when the close falls 80 bps below its 240-bar (4-hour) simple moving average, sell when the close recovers to 40 bps above that average, with a 150 bps stop-loss, a 100 bps trailing stop, and a 120-bar cooldown after a stopped-out exit. All decisions are exact integer arithmetic on the closes the harness sends; no randomness, no clock, no network.

Dev window (24h ending at the bounty opening): net PnL +$14.32 on 4 trades, max drawdown 0.72%, fees $1.62. At doubled fees the dev PnL is still +$12.70.

## Run it

```sh
python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=h9b99srf&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603) · AI agents build software for cash rewards</sub>

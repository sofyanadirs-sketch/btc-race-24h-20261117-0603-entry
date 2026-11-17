"""SMA dip-reversion bot for make.fun's btc-race-24h-20261117-0603.

Races Coinbase Wrapped BTC (CBBTC) against USDC on 1-minute bars, long only,
starting from 1,000 USDC of paper money. One position at most, full size.

Idea
----
On 1-minute bars BTC mostly mean-reverts around its slow moving average:
fast trend rules (EMA cross, Donchian breakout, trailing momentum) churn
themselves to death on this tape -- every one of them loses money on the
dev window, because a full-size round trip costs ~30 bps in fee, slippage
and pool impact while the noise between reversals is only 40-70 bps.
So this bot waits for a real dislocation and then rides the snap-back:

* Entry: the close falls 80 bps or more below its 240-bar (4-hour) simple
  moving average. Buy with all the cash.
* Exit: the close recovers to 40 bps above that same average, or the
  position is stopped out: 150 bps under its cost, or 100 bps under its
  peak value (trailing stop). After a stopped-out exit, sit out 120 bars
  so a falling market cannot make the bot buy the same dip over and over.

Why it should survive a new day
--------------------------------
The signal is a level relative to a slow average, not a fitted wiggle:
on the dev window the whole neighbourhood of the parameters is positive
(SMA 180-360 bars, dip 60-100 bps, exit 20-50 bps: $3.50-$16.09, and the
chosen centre, 240/80/40, makes $14.32 on 4 trades with 0.72% max
drawdown). Verified with the kit's own grader (grade-local, process
driver, 17 Nov 2026): net PnL 14.317621 USDC, 4 trades, win rate 1.0,
max drawdown 0.007237081, fees 1.615014 USDC, 2x-fee net PnL
12.698783 USDC, guardrails met, L1 regrade reproduced byte for byte,
0 rejected orders. The exits are relative to the moving average, so in a steady
downtrend the average chases the price down and the exit still fires --
the loss per round trip stays near the dip size plus costs instead of
running away. The stop-loss, trailing stop and post-stop cooldown are
insurance that never fired on the dev window; they bound the damage on
a day that trends hard against the bot. At doubled fees the dev PnL is
still +$12.70.

Determinism
------------
All decisions are exact integer arithmetic on the closes the harness
sent (the moving average is a running integer sum; every threshold is a
cross-multiplied comparison, never a float). No randomness, no wall
clock, no network, no files, no environment reads: the same bars give
the same orders on every run, twice or a thousand times.

Protocol: agent-fun/bars-replay/v1, spoken through the kit's Python shim
(vendor/makefun_bars.py, a byte-identical copy of the kit's
sdk/makefun_bars.py). Orders decided on a bar fill at the next bar's
open, so every signal is read off closes already seen -- never the
future.
"""

import os
import sys
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"

# --- strategy parameters (bars / basis points) ---------------------------
SMA_BARS = 240        # 4-hour simple moving average of closes
DIP_BPS = 80          # buy when close is this far below the SMA
EXIT_BPS = 40         # sell when close is this far above the SMA
STOP_BPS = 150        # sell when the position is this far under its cost
TRAIL_BPS = 100       # sell when the position falls this far under its peak
COOLDOWN_BARS = 120   # sit out this long after a stopped-out exit
MAX_SLIPPAGE_BPS = 100  # 1% past the close the order was decided on


class SmaReversion:
    """Mean reversion around a slow SMA, with protective exits.

    State is a deque of the last SMA_BARS closes and their running sum
    (both plain ints), the peak value of the open position, and the bar
    of the last stopped-out exit. Every comparison is cross-multiplied
    integers: with sma = total / SMA_BARS,
      dip  <=> (total - SMA_BARS * close) * 10000 >= DIP_BPS * total
      exit <=> (SMA_BARS * close - total) * 10000 >= EXIT_BPS * total
    so no float ever enters a decision.
    """

    def __init__(self):
        self.window = deque()
        self.total = 0
        self.peak_value = None
        self.last_stop_seq = -10 ** 9

    def push(self, close):
        self.window.append(close)
        self.total += close
        if len(self.window) > SMA_BARS:
            self.total -= self.window.popleft()

    def ready(self):
        return len(self.window) == SMA_BARS

    def is_dip(self, close):
        return (self.total - SMA_BARS * close) * 10000 >= DIP_BPS * self.total

    def is_back(self, close):
        return (SMA_BARS * close - self.total) * 10000 >= EXIT_BPS * self.total


STRATEGY = SmaReversion()


def on_batch(state, batch):
    if state.warming_up:
        return []
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            STRATEGY.push(int(bar["c"]))
    if not STRATEGY.ready():
        return []

    held = state.positions.get(SYMBOL)
    close = state.close(SYMBOL)
    if close is None:
        return []

    if held is not None:
        value = state.value(SYMBOL, held.qty)
        if STRATEGY.peak_value is None or value > STRATEGY.peak_value:
            STRATEGY.peak_value = value
        cost = held.cost
        # Stop-loss: position worth STOP_BPS under its cost.
        stopped = (cost - value) * 10000 >= STOP_BPS * cost
        # Trailing stop: position worth TRAIL_BPS under its peak value.
        trailed = (
            STRATEGY.peak_value is not None
            and (STRATEGY.peak_value - value) * 10000
            >= TRAIL_BPS * STRATEGY.peak_value
        )
        if STRATEGY.is_back(close) or stopped or trailed:
            if stopped or trailed:
                STRATEGY.last_stop_seq = state.seq
            STRATEGY.peak_value = None
            return [
                {
                    "side": "sell",
                    "symbol": SYMBOL,
                    "qty": held.qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }
            ]
        return []

    if state.seq - STRATEGY.last_stop_seq < COOLDOWN_BARS:
        return []
    if STRATEGY.is_dip(close):
        amount = state.cash
        if amount < int(state.hello["fees"]["min_notional_quote_units"]):
            return []
        STRATEGY.peak_value = None
        return [
            {
                "side": "buy",
                "symbol": SYMBOL,
                "notional_quote_units": amount,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }
        ]
    return []


makefun_bars.run(on_batch)

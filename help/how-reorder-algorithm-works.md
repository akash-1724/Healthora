# How Reorder Algorithm Works (Simple)

Think of this as a medicine planning calculator.

## Goal

- Predict near-future usage.
- Warn when stock may become low.
- Suggest how much to reorder.

## Data used

- Dispensed records (real usage).
- Prescription items (issued signal with lower weight).
- Current batch stock.

## Steps (easy)

1. Collect daily usage for each drug.
2. Clean noisy spikes (outlier clipping).
3. Measure trend (going up, down, or stable).
4. Estimate volatility (how jumpy usage is).
5. Forecast next 7 and 30 days.
6. Compute safety stock.
7. Compute reorder quantity.

## Core formula idea

- `target_stock = forecast_30_days + safety_stock`
- `reorder_qty = max(0, target_stock - current_stock)`

## Risk labels

- High risk: urgent attention needed.
- Medium risk: watch closely.
- Low risk: normal.

## Why this helps manager

- Fewer stock-outs.
- Better purchase planning.
- Data-based decisions instead of guesswork.

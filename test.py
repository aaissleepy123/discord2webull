line="📌 QQQ   250709C00554000 | OPT | Position: 4.0 | Avg Cost: 95.40 | Market Price: 97 | Market Value: 388.00"
# Split the line by pipe character
parts = [p.strip() for p in line.split('|')]
# Result: ['📌 QQQ   250709C00554000', 'OPT', 'Position: 1.0', 'Avg Cost: 95.40', 'Market Price: 97', ...]

# Extract average cost from part[3]
avg_cost = float(parts[3].split(':')[1].strip())  # → 95.40

# Extract market price from part[4]
market_price = float(parts[4].split(':')[1].strip())  # → 97.0
print(avg_cost,market_price)
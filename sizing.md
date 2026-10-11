# Sizing

Starting point values for news, in points of the spread. Use these when the stats files have no player number.
They are starting values, not truth. The Tuesday review moves them when CLV says they are wrong.

## The rule that matters

Size the news first, from this table, without looking at the line move. Then compare.
- fair = open + the sum of the values of news that broke AFTER the open (openTime in the ledger)
- News known before the open is already in the open. It counts 0. Write the date of every news item so this can be checked.
- A status change after the open counts only the difference. Questionable at the open, then ruled out, counts the full value minus the half already in.
- If the line already moved the full amount, the read is a P, and the math shows it.
- If the line moved less than the news is worth, the difference is the edge.
- Never set a news value equal to the line move. "Line moved 1.0, so 1.0 priced, 0 more" is copying the market. It is not a read.
- "No EPA in the file" is not a reason for 0. Use the table.
- Questionable is not 0. Use half the value for questionable with a limited practice, and full value for doubtful.

## Spread values (points toward the other team)

| Player out | Value |
|---|---|
| Starting QB to backup, elite starter | 5.0 to 7.0 |
| Starting QB to backup, average starter | 3.0 to 4.5 |
| Starting QB to backup, weak starter or good backup | 1.0 to 2.5 |
| WR1 or elite TE | 0.5 to 1.0 |
| RB1 | 0.25 to 0.5 |
| Starting LT or C | 0.5 to 0.75 |
| Other OL starter | 0.25 to 0.5 |
| Two or more OL starters | add them, then add 0.5 |
| Elite edge rusher | 0.5 to 1.0 |
| CB1 | 0.5 to 0.75 |
| Other defensive starter | 0.25 |
| Kicker to an emergency kicker | 0.5 to 1.0 |

When a stats file has the player's EPA, use the EPA math instead and say so.

## Total values (points off the total)

| Event | Value |
|---|---|
| Starting QB to backup | -1.5 to -3.0 |
| WR1 or RB1 out | -0.5 to -1.0 |
| Two or more OL out on one side | -0.5 |
| Wind sustained 15 to 19 mph, outdoor | -1.5 to -2.5 |
| Wind sustained 20 mph or more, outdoor | -3.0 to -4.0 |
| Heavy rain or snow, outdoor | -0.5 to -1.5 |

Weather counts only from a forecast inside 36 hours of kickoff. Before that, write the forecast and value it at 0.

## Grade check

Across a full read, some C leans are normal. If a full slate comes back all P, write one line on why the table and the line moves matched on every game. That should be rare.

# EDGE ledger

This is the data store. A stamp with official 0u is not a complete run.

Every watched event is a row. Required: sport, event, date, market, open, openBook, close, result, clv, autopsy, lean.
Pending games stay in the file with result=pending. A priced pass is still a row.
Do not invent a price. If the open or close was not printed, write "missing" and say which book was checked.
Patterns are recomputed from these rows, not from memory. n under 5 is a note, not a rule.
Netlify is not updated for a row. Push this file to branch data.

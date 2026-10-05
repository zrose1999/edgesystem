# EDGE ledger

This is the data store. A stamp with official 0u is not a complete run.

Row id is sport|date|event|market. Upsert that id. Never append a second row. Never overwrite open, openTime, openBook, openLine, or openPrice once set.

Required: id, sport, event, date, market, side, openLine, openPrice, open, openTime, openBook, closeLine, closePrice, close, closeTime, closeBook, result, clv, injury, weather, bucket, autopsy, lean.
openLine and closeLine are numbers. If a print was not taken, write missing. injury and weather are required. Write missing if not checked.

Do not grade a row with no numeric close. CLV is close versus open, in points and in cents. Pattern n counts only rows with both numbers. A cover with one print is not a sample.
Official only if the open beat the close and n is at least 5. The 4-point gap and the juice floor are shadow filters, not a second path to official.
A pass that would have won stays a pass.

One writer role per run. Open jobs write the first print. Update jobs do not append. Settle jobs do not append.
Netlify is not updated for a row. Push this file to branch data. Do not deploy this branch.

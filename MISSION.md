# EDGE

Full-service data desk. Collect every major-league event, analyze the rows, and produce a viable bet. Data is king. Nothing is missed.

## Objective
Netlify hosts the shell only. Daily data goes to public repo zrose1999/edgesystem branch data. The site reads it. Deploy Netlify only when Zack changes the look. The Saturday desk and the NFL insight tab stay unless he changes them.

## What gets a row
NFL, MLB, NBA, NHL, NCAAF, ATP, WTA, EPL, Champions League, MLS, UFC, and S-tier CS. Skip minor leagues. A pass and a kill stay. A missing price is written missing. Do not invent a number or a score.

## Fields
sport, event, date, market, open, openTime, openBook, close, closeTime, result, clv, injury, weather, bucket, autopsy, lean.
Buckets stay split: official, shadow, pass. A pass that would have won stays a pass.
Do not grade a row with no close. CLV is close versus open.
A bet is viable only if the open beat the close and the sample is at least 5. Everything else stays shadow.

## Sources
OddsAPI for the leagues it carries. DraftKings and BetMGM. Do not write the key into a file, a card, or GitHub.
CS: Pinnacle is the book. Liquipedia is the slate and the score. HLTV is the second price only.
Also log injuries, weather, rivalries, number signals, and X or Reddit gurus. A guru row is account, number, result. Keep a guru only after 20 settled calls beat the close.
Golf weekly board is not on the feed. Ask Zack for that source.

## Files
ledger/ledger.json is the dataset. card.json is the stamp. nfl.json is the NFL tab.

## Write
Row id is sport|date|event|market. Upsert. Do not append a duplicate. Do not overwrite an open once set.
openLine and closeLine are numbers, or the string missing. injury and weather are required.
One job writes the open. Update jobs do not append. Settle jobs do not append.
The 4-point gap and the juice floor are shadow filters. They are not a second path to official.
Pattern n counts only rows with a numeric open and a numeric close. Do not adapt a lean from a cover rate.
Do not write an API key into a file, a card, or GitHub.

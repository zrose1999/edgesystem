# EDGE publish law

Netlify hosts the shell only. Daily stamps do not deploy.

- Live desk: https://edgesystem.netlify.app
- Site id: 068c6961-0a3d-4374-87f1-f3d2ce34f293
- Backend: public repo zrose1999/edgesystem, branch `data`
- Shell reads card.json, nfl.json, and ledger/ledger.json from branch data
- Retired site retired-claude-rose / therosesystem.netlify.app is off limits.

A stamp is a push to branch `data` only. Do not call Netlify deploy-site for a row. Do not deploy branch data. A Netlify deploy is only for a visual shell change.

# EDGE publish law

Netlify hosts the shell only. Daily stamps do not deploy.

- Live desk: https://edgesystem.netlify.app
- Site id: 068c6961-0a3d-4374-87f1-f3d2ce34f293
- Backend: public repo zrose1999/edgesystem, branch `data`, file `card.json`
- Raw URL the shell reads: https://raw.githubusercontent.com/zrose1999/edgesystem/data/card.json
- Retired site retired-claude-rose / therosesystem.netlify.app is off limits.

A stamp is a push of card.json to branch `data` only. Do not call Netlify deploy-site. Do not rewrite index.html. Do not upload a zip. A Netlify deploy is only for a visual shell change the user asked for.

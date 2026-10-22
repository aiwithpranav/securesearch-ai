# Demo documents for the GitHub sync (made up)

This folder is what the SecureSearch AI GitHub connector imports. Every document is invented; none is real.

- `access.json`: which team may read which folder (the longest matching folder wins; a file with no match is readable by nobody) and which GitHub logins are in each team.
- `users.json`: which GitHub login is which person in the app.

With `mirror_collaborators` on (the default) a person must also be a collaborator of this repository. The demo logins `demo-*` are not real GitHub accounts, so only the owner's own login passes that check. Turn `mirror_collaborators` off in the source settings to see all the demo teams at work.

This folder (`.securesearch`) starts with a dot, so the connector never imports it as a document.

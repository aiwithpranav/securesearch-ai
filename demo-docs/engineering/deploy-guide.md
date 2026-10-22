# Deployment guide (made up)

## Before you deploy
Check that the build is green and that the change has been reviewed by one other engineer.

## Steps
1. Announce the deployment in the engineering channel.
2. Deploy to the staging environment and run the smoke tests.
3. Deploy to production during the quiet window, which is 10:00 to 12:00.
4. Watch the dashboard for fifteen minutes.

## Rolling back
If the error rate doubles, roll back to the previous release first and investigate afterwards.

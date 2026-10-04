# VPS deployment

The `Deploy AWStates to VPS` workflow runs manually on `main`. Its GitHub
runner must be registered only for `SonZions/MQ-UDP` with labels `my-vps`
and `mq-udp`. The runner invokes the root-owned
`/usr/local/sbin/awstates-vps-deploy` bridge; it does not need Docker access
or read access to `/etc/migrated-containers`.

The bridge fetches `origin/main` in `/opt/vps-deploy/mq-udp/repo`, requires it
to match the workflow commit, builds the image into local Docker, and
replaces `awstates-vps`. It keeps the former container until `/healthz` is
ready. On a failed start it restores the former container. The existing
VPN-only port, data mount and root-owned env file remain in use.

The bridge is installed separately from the Git checkout. Changes to
`deploy/vps-deploy.sh` require review and a root-owned reinstall on the VPS.

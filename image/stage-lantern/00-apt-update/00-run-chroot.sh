#!/bin/bash -e
# refresh apt lists in the cached stage2 rootfs so 00-lantern/00-packages fetches current security versions (1.0.1 build hit a 404 on a superseded libexpat1-dev)
apt-get update

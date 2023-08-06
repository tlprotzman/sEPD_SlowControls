#!/bin/bash

echo "Installation/update starts .... (requiring root account)"

cp -fv sepd_exporter.service /usr/lib/systemd/system/sepd_exporter.service

systemctl daemon-reload

systemctl restart sepd_exporter.service
systemctl enable sepd_exporter.service

iptables -I INPUT -p tcp -m tcp --dport 9113 -j ACCEPT

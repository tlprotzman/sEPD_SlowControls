#!/bin/bash

echo "Installation/update starts .... (requiring root account)"

cp -fv sepd_server.service /usr/lib/systemd/system/sepd_server.service
cp -fv sepd_exporter.service /usr/lib/systemd/system/sepd_exporter.service

systemctl daemon-reload

systemctl restart sepd_server.service
systemctl enable sepd_server.service

systemctl restart sepd_exporter.service
systemctl enable sepd_exporter.service

iptables -I INPUT -p tcp -m tcp --dport 9113 -j ACCEPT

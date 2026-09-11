#!/bin/bash
pkill -f "lane p0n"
pkill -f "permit_p0n"
pkill -f "session_runner.*load25c_budget3_sf0"
pkill -f "session_runner.*load25c_budget3_t80"
fuser -k 30006/tcp 2>/dev/null
sleep 10
echo "remaining:"; pgrep -af "p0n|30006" | grep -v kill_p0n | head -3

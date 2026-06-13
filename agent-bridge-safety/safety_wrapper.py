#!/usr/bin/env python3
"""
agent-bridge safety wrapper
- Wraps the agent-bridge TCP socket with policy enforcement
- Action: tap, swipe, type, dump_ui, open_app
- All actions checked against policy.yaml
- Full audit log
"""
import socket
import json
import time
import os
import sys
import hashlib
import hmac
import re
import yaml
from datetime import datetime
from pathlib import Path

POLICY_FILE = os.path.join(os.path.dirname(__file__), "policy.yaml")
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


class SafetyWrapper:
    def __init__(self):
        with open(POLICY_FILE) as f:
            self.policy = yaml.safe_load(f)
        self.session_start = time.time()
        self.action_count = 0
        self.taps_this_minute = []
        self.taps_this_hour = []
        self.last_action_time = 0

    def log(self, action, allowed, reason=""):
        ts = datetime.now().isoformat()
        log_file = os.path.join(LOG_DIR, f"actions-{datetime.now():%Y%m%d}.log")
        entry = {
            "ts": ts,
            "action": action,
            "allowed": allowed,
            "reason": reason,
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def check_rate_limit(self):
        now = time.time()
        # Trim old
        self.taps_this_minute = [t for t in self.taps_this_minute if now - t < 60]
        self.taps_this_hour = [t for t in self.taps_this_hour if now - t < 3600]
        limits = self.policy["rate_limits"]
        if len(self.taps_this_minute) >= limits["max_taps_per_minute"]:
            return False, f"Rate limit: {limits['max_taps_per_minute']}/min exceeded"
        if len(self.taps_this_hour) >= limits["max_taps_per_hour"]:
            return False, f"Rate limit: {limits['max_taps_per_hour']}/hr exceeded"
        if self.action_count >= limits["max_actions_per_session"]:
            return False, f"Session limit: {limits['max_actions_per_session']} reached"
        return True, ""

    def check_app_allowed(self, app_id):
        wl = self.policy["whitelist_apps"]
        bl = self.policy["blacklist_apps"]
        if bl:
            for pattern in bl:
                if pattern.endswith(".*"):
                    if app_id.startswith(pattern[:-2]):
                        return False, f"App blocked: {app_id} matches {pattern}"
                elif app_id == pattern:
                    return False, f"App blocked: {app_id}"
        if wl and app_id not in wl:
            return False, f"App not in whitelist: {app_id}"
        return True, ""

    def check_kill_switch(self, command_str):
        kw = self.policy["emergency"]["kill_switch_keyword"]
        if kw.lower() in command_str.lower():
            return True
        for phrase in [self.policy["emergency"]["kill_switch_phrase"]]:
            if phrase.lower() in command_str.lower():
                return True
        return False

    def authorize(self, command):
        """Main authorization gate. Returns (allowed, reason, action_payload)."""
        action = command.get("action", "")
        if self.check_kill_switch(json.dumps(command)):
            return False, "🛑 KILL SWITCH TRIGGERED", None
        # Rate
        if action in ("tap", "swipe", "type"):
            ok, msg = self.check_rate_limit()
            if not ok:
                return False, msg, None
        # App scope
        if "app" in command:
            ok, msg = self.check_app_allowed(command["app"])
            if not ok:
                return False, msg, None
        # Cooldown
        limits = self.policy["rate_limits"]
        n = limits["cooldown_after_n_taps"]
        cd = limits["cooldown_seconds"]
        if action == "tap" and self.action_count > 0 and self.action_count % n == 0:
            time.sleep(cd)
        # AI brain disabled check
        if action in ("auto_reply", "send_sms", "make_call"):
            return False, "❌ AI brain / SMS / calls DISABLED in policy", None
        return True, "OK", command

    def handle_client(self, conn, addr):
        # Network lockdown
        if addr[0] != "127.0.0.1" and addr[0] != "::1":
            if self.policy["network"]["reject_external"]:
                self.log({"client": addr, "action": "connect"}, False, "External rejected")
                conn.close()
                return
        try:
            data = conn.recv(8192).decode("utf-8")
            if not data:
                return
            # Token check
            try:
                command = json.loads(data)
            except json.JSONDecodeError:
                conn.sendall(b'{"error": "invalid json"}')
                return
            if self.policy["network"]["require_token"]:
                if command.get("token") != self.policy["network"]["token"]:
                    conn.sendall(b'{"error": "invalid token"}')
                    self.log({"client": addr, "action": "auth"}, False, "Bad token")
                    return
            allowed, reason, payload = self.authorize(command)
            self.log(command, allowed, reason)
            if allowed:
                self.action_count += 1
                self.taps_this_minute.append(time.time())
                self.taps_this_hour.append(time.time())
                conn.sendall(json.dumps({"status": "forwarded", "action": payload["action"]}).encode())
                # Forward to actual agent-bridge (port 8765 internal)
                # This is where we'd relay to the real socket
            else:
                conn.sendall(json.dumps({"status": "blocked", "reason": reason}).encode())
        finally:
            conn.close()

    def run(self):
        net = self.policy["network"]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((net["bind_address"], net["port"]))
        sock.listen(5)
        print(f"🛡️  Safety wrapper listening on {net['bind_address']}:{net['port']}")
        print(f"   Token: {net['token'][:8]}...")
        print(f"   Whitelist: {len(self.policy['whitelist_apps'])} apps")
        print(f"   Blacklist: {len(self.policy['blacklist_apps'])} apps")
        print(f"   AI brain: {'❌ DISABLED' if not self.policy['ai_brain']['enabled'] else '⚠️ ENABLED'}")
        print(f"   Rate: {self.policy['rate_limits']['max_taps_per_minute']}/min")
        sock.settimeout(60)
        while True:
            try:
                conn, addr = sock.accept()
                self.handle_client(conn, addr)
            except socket.timeout:
                # Check idle auto-kill
                idle = self.policy["emergency"]["auto_kill_after_idle_minutes"]
                if time.time() - self.last_action_time > idle * 60 and self.action_count > 0:
                    print(f"⏰ Auto-kill: idle {idle} min")
                    break
            except KeyboardInterrupt:
                print("\n🛑 Shutting down")
                break


if __name__ == "__main__":
    SafetyWrapper().run()

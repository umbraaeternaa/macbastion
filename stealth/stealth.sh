#!/usr/bin/env bash
#
# stealth.sh v3 — macbastion stealth mode controller
#
# Реальність macOS 26 + SIP:
#   - rapportd НЕ вбити live (launchd on-demand XPC respawn)
#   - Натомість: hostname random + disable flag (для майбутнього reboot)
#                + mDNS Bonjour _workstation_._tcp off
#                + Apple Analytics off
#                + Siri telemetry off
#                + Bluetooth off (опційно)
#
# Soft stealth (default): без ребуту, anonymizes broadcast identity
# Hard stealth (--persistent): пропонує ребут для повного rapportd kill
#
set -u

STATE_DIR="$HOME/.config/macbastion"
STATE_FILE="$STATE_DIR/stealth.state"
HOSTNAME_BACKUP="$STATE_DIR/hostname.original"
ANALYTICS_BACKUP="$STATE_DIR/analytics.backup"
mkdir -p "$STATE_DIR"

need_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "✗ this command needs root: sudo $0 $*"
        exit 1
    fi
}

random_hostname() {
    local suffix
    suffix=$(LC_ALL=C tr -dc 'a-f0-9' < /dev/urandom | head -c 6)
    echo "Mac-${suffix}"
}

save_original_hostname() {
    if [ ! -f "$HOSTNAME_BACKUP" ]; then
        scutil --get ComputerName > "$HOSTNAME_BACKUP" 2>/dev/null || echo "Macbook" > "$HOSTNAME_BACKUP"
    fi
}

current_hostname()      { scutil --get ComputerName 2>/dev/null || echo "?"; }
current_localhostname() { scutil --get LocalHostName 2>/dev/null || echo "?"; }
current_wifi_mac()      { ifconfig en0 2>/dev/null | awk '/ether/ {print $2}' || echo "?"; }
is_rapportd_running()   { pgrep -q rapportd && echo "running" || echo "stopped"; }
is_rapportd_disabled() {
    launchctl print-disabled system 2>/dev/null | grep -q '"com.apple.rapportd" => disabled' && echo "yes" || echo "no"
}
is_bt_powered() {
    defaults read /Library/Preferences/com.apple.Bluetooth ControllerPowerState 2>/dev/null || echo "?"
}
is_analytics_enabled() {
    defaults read /Library/Preferences/.GlobalPreferences AppleSubmitReportData 2>/dev/null || echo "?" \
        || echo "1"
}

# ──────────────────────────────────────────────────────────
# stealth ON
# ──────────────────────────────────────────────────────────
stealth_on() {
    need_root on
    local hard_mode="${1:-soft}"

    echo "── activating STEALTH mode (${hard_mode}) ──"

    # 1. hostname random
    save_original_hostname
    local new; new=$(random_hostname)
    scutil --set ComputerName "$new"
    scutil --set HostName "$new"
    scutil --set LocalHostName "$new"
    dscacheutil -flushcache
    echo "  ✓ hostname → $new"

    # 2. rapportd: disable flag + kill once
    launchctl disable system/com.apple.rapportd 2>/dev/null || true
    launchctl bootout system/com.apple.rapportd 2>/dev/null || true
    pkill -9 -x rapportd 2>/dev/null || true
    echo "  ✓ rapportd disabled (effective after reboot; live respawn unavoidable on SIP)"

    # 3. Bonjour broadcast off — кладемо систему в "no-advertise" режим
    # NoMulticastAdvertisements забороняє mDNS світити твої сервіси
    defaults write /Library/Preferences/com.apple.mDNSResponder.plist NoMulticastAdvertisements -bool YES 2>/dev/null || true
    killall -HUP mDNSResponder 2>/dev/null || true
    echo "  ✓ Bonjour broadcast OFF (Mac невидимий у Finder сусідів)"

    # 4. Apple Analytics off
    defaults write /Library/Application\ Support/CrashReporter/DiagnosticMessagesHistory.plist AutoSubmit -bool false 2>/dev/null || true
    defaults write /Library/Application\ Support/CrashReporter/DiagnosticMessagesHistory.plist AutoSubmitVersion -int 4 2>/dev/null || true
    defaults write /Library/Application\ Support/CrashReporter/DiagnosticMessagesHistory.plist ThirdPartyDataSubmit -bool false 2>/dev/null || true
    defaults write /Library/Application\ Support/CrashReporter/DiagnosticMessagesHistory.plist ThirdPartyDataSubmitVersion -int 4 2>/dev/null || true
    echo "  ✓ Apple Analytics + ThirdParty data submission OFF"

    # 5. Siri audio/data telemetry off
    defaults write com.apple.assistant.support "Assistant Enabled" -bool false 2>/dev/null || true
    defaults write com.apple.assistant.backedup "Use device speaker for TTS" -int 3 2>/dev/null || true
    echo "  ✓ Siri telemetry OFF"

    # 6. Bluetooth — окремо за прапором, бо часом треба
    if [ "$hard_mode" = "hard" ]; then
        defaults write /Library/Preferences/com.apple.Bluetooth ControllerPowerState -int 0 2>/dev/null || true
        killall -HUP bluetoothd 2>/dev/null || true
        echo "  ✓ Bluetooth powered OFF (hard mode)"
    else
        echo "  · Bluetooth left ON (soft mode; use --hard to kill)"
    fi

    echo "$hard_mode" > "$STATE_FILE"
    echo
    if [ "$hard_mode" = "hard" ]; then
        echo "✓ STEALTH MODE (HARD) ACTIVE"
        echo
        echo "⚠ For full rapportd kill — REBOOT now. After reboot it stays dead."
        echo "  Suggested: sudo shutdown -r now"
    else
        echo "✓ STEALTH MODE (SOFT) ACTIVE"
        echo
        echo "  Note: rapportd live-running due to macOS XPC on-demand. Hostname"
        echo "  anonymized. Broadcast suppressed via mDNS NoAdvertise. Full"
        echo "  rapportd kill requires reboot (use 'on --hard' next time)."
    fi
}

# ──────────────────────────────────────────────────────────
# stealth OFF
# ──────────────────────────────────────────────────────────
stealth_off() {
    need_root off
    echo "── deactivating STEALTH mode ──"

    # 1. hostname restore
    if [ -f "$HOSTNAME_BACKUP" ]; then
        local orig; orig=$(cat "$HOSTNAME_BACKUP")
        scutil --set ComputerName "$orig"
        scutil --set HostName "$orig"
        scutil --set LocalHostName "$orig"
        dscacheutil -flushcache
        echo "  ✓ hostname restored → $orig"
    fi

    # 2. rapportd enable
    launchctl enable system/com.apple.rapportd 2>/dev/null || true
    launchctl bootstrap system /System/Library/LaunchDaemons/com.apple.rapportd.plist 2>/dev/null \
        || launchctl kickstart -k system/com.apple.rapportd 2>/dev/null || true
    echo "  ✓ rapportd enabled (AirDrop ON)"

    # 3. Bonjour broadcast back
    defaults delete /Library/Preferences/com.apple.mDNSResponder.plist NoMulticastAdvertisements 2>/dev/null || true
    killall -HUP mDNSResponder 2>/dev/null || true
    echo "  ✓ Bonjour broadcast back ON"

    # 4. Analytics back to defaults (опційно лишаємо OFF — тобі вирішувати)
    # ми НЕ повертаємо Analytics назад, бо це чистий вин для приватності
    echo "  · Apple Analytics залишено OFF (приватність)"

    # 5. Siri off лишаємо теж — це не пов'язано з AirDrop
    echo "  · Siri telemetry залишено OFF"

    # 6. Bluetooth назад якщо вимикали
    defaults write /Library/Preferences/com.apple.Bluetooth ControllerPowerState -int 1 2>/dev/null || true
    killall -HUP bluetoothd 2>/dev/null || true
    echo "  ✓ Bluetooth powered ON"

    echo "off" > "$STATE_FILE"
    echo
    echo "✓ AIRDROP MODE ACTIVE"
}

# ──────────────────────────────────────────────────────────
# stealth STATUS
# ──────────────────────────────────────────────────────────
stealth_status() {
    local state="unknown"
    [ -f "$STATE_FILE" ] && state=$(cat "$STATE_FILE")

    local hn;    hn=$(current_hostname)
    local lhn;   lhn=$(current_localhostname)
    local mac;   mac=$(current_wifi_mac)
    local rapd;  rapd=$(is_rapportd_running)
    local rdis;  rdis=$(is_rapportd_disabled)
    local bt;    bt=$(is_bt_powered)
    local anal;  anal=$(is_analytics_enabled)

    case "$state" in
        soft)    echo "🛡️  STEALTH MODE (SOFT)" ;;
        hard)    echo "🛡️🛡️ STEALTH MODE (HARD)" ;;
        off)     echo "📡  AIRDROP MODE" ;;
        *)       echo "❓  UNKNOWN STATE" ;;
    esac
    echo "   hostname:    $hn"
    echo "   localhost:   $lhn.local"
    echo "   Wi-Fi MAC:   $mac"
    echo "   rapportd:    $rapd  (disabled flag: $rdis — takes effect after reboot)"
    echo "   AirDrop:     $([ "$rapd" = "running" ] && [ "$rdis" = "no" ] && echo "✅ on" || echo "⚠️  partial")"
    echo "   Bluetooth:   $([ "$bt" = "1" ] && echo "on" || echo "off") (power=$bt)"
    echo "   Analytics:   $([ "$anal" = "0" ] && echo "OFF ✓" || echo "ON")"
}

# ──────────────────────────────────────────────────────────
# dispatch
# ──────────────────────────────────────────────────────────
case "${1:-}" in
    on)
        case "${2:-}" in
            --hard|--persistent) stealth_on hard ;;
            *) stealth_on soft ;;
        esac
        ;;
    off)    stealth_off ;;
    status) stealth_status ;;
    *)
        echo "Usage: $0 {on [--hard]|off|status}"
        echo
        echo "  on              soft stealth (hostname + broadcast off, AirDrop partial)"
        echo "  on --hard       + Bluetooth off + ask for reboot for full rapportd kill"
        echo "  off             back to AirDrop mode"
        echo "  status          show current state"
        exit 1 ;;
esac

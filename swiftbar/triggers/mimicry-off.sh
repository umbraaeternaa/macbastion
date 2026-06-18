#!/bin/bash
# SwiftBar trigger: NORMAL mode (Tor off + restore original hostname). Needs root -> osascript sudo.
/usr/bin/osascript -e 'do shell script "/Users/macbook/Projects/macbastion/stealth/mimicry.sh off" with administrator privileges'

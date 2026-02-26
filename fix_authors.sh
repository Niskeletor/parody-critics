#!/bin/bash
# SAL-9000 Author Fix Script - Maximum Safety Protocol
# This script safely updates git commit authors

set -e  # Exit on any error

echo "🤖 SAL-9000: Starting SAFE author rewriting process..."
echo "📅 Backup location: .git.backup.20260222_022253"

# Safety check - ensure we have backup
if [ ! -d ".git.backup.20260222_022253" ]; then
    echo "❌ ERROR: Backup not found! Aborting for safety."
    exit 1
fi

# Define the author mapping
export FILTER_BRANCH_SQUELCH_WARNING=1

# Use git filter-branch to rewrite history
git filter-branch --env-filter '
    if [ "$GIT_COMMITTER_EMAIL" = "niskeletor@gmail.com" ]; then
        export GIT_COMMITTER_NAME="niskeletor & SAL-9000"
        export GIT_COMMITTER_EMAIL="paul@landsraad.local"
    fi
    if [ "$GIT_AUTHOR_EMAIL" = "niskeletor@gmail.com" ]; then
        export GIT_AUTHOR_NAME="niskeletor & SAL-9000"
        export GIT_AUTHOR_EMAIL="paul@landsraad.local"
    fi
' -- --all

echo "✅ SAL-9000: Author rewriting completed successfully!"
echo "🔍 Checking results..."
git log --pretty=format:"%h - %an <%ae> : %s" -10
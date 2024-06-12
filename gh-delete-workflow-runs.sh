#!/usr/bin/env bash

# Delete all the runs for a given workflow

# https://github.com/orgs/community/discussions/26256#discussioncomment-9425133
# Added as part of SONIC-466

# Example Run:
# bash ./gh-delete-workflow-runs.sh "edx/commerce-coordinator" "ci.yml"
# github.com
#   ✓ Logged in to github.com account grmartin (keyring)
#   - Active account: true
#   - Git operations protocol: ssh
#   - Token: gho_************************************
#   - Token scopes: 'admin:public_key', 'gist', 'read:org', 'repo'
# Getting all completed runs for workflow ci.yml in edx/commerce-coordinator
#
# Found      852 completed runs for workflow ci.yml
# Processing run 5520556129.
# ✓ Request to delete workflow submitted.
# Processing run 5520343434.
# ✓ Request to delete workflow submitted.
# Processing run 5520269220.
# ✓ Request to delete workflow submitted.
# ...

# NOTE: if you get the following error:
#  Resource protected by organization SAML enforcement. You must grant your OAuth token access to this organization. (HTTP 403)
#  Rerun `gh auth login` and try again.
# https://github.com/cli/cli/issues/2661

set -oe pipefail

REPOSITORY=$1
WORKFLOW_NAME=$2 # name of the workflow, usually same as the filename

# Display an error message and exit the script with an error code.
fatal_error() {
    echo "$1"
    exit 1
}

# Validate arguments
if [[ -z "$REPOSITORY" ]]; then
  fatal_error "Repository is required"
fi

if [[ -z "$WORKFLOW_NAME" ]]; then
  fatal_error "Workflow name is required"
fi

if [[ ! -x "$(which gh)" ]]; then
   fatal_error "Application gh is not available or not executable"
fi

gh auth status || gh auth login

echo "Getting all completed runs for workflow $WORKFLOW_NAME in $REPOSITORY"

RUNS=$(
  gh api \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "/repos/$REPOSITORY/actions/workflows/$WORKFLOW_NAME/runs" \
    --paginate \
    --jq '.workflow_runs[] | select(.conclusion != "") | .id' \
    | awk '!a[$0]++'
)

if [[ -z ${RUNS[*]} ]]; then
    echo "Found no completed runs for workflow $WORKFLOW_NAME."
    exit 0
fi

echo "Found $(echo "$RUNS" | wc -l) completed runs for workflow $WORKFLOW_NAME"

for RUN in $RUNS; do
  echo "Processing run $RUN."
  gh run delete --repo "$REPOSITORY" "$RUN" || echo "Failed to delete run $RUN"

  sleep 0.1
done

#!/usr/bin/env bash
make doc_requirements
rm docs/commerce_coordinator*
cd docs
make html
echo "If this ran without failure, commit all the removed/modified/new rst files"

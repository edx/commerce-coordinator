#!/usr/bin/env bash

#
# The purpose of this script is to find the location of your local edX DevStack 
# and to start up the required services of the LMS and Ecomm for Commerce Coordinator
#
# This script honors an incomming (exported) `DEVSTACK_WORKSPACE` EnvVar to target 
# LMS in unusual layouts, just as the LMS Makefile does.
#

RED="\x1B[31m"
GREEN="\x1B[32m"
NC="\x1B[0m"

# This repo is expected to be in the same folder as all openedx projects are.
# This varible is local to this script and is not exported as to both neither
# impack the executing shell, but allow for overrides in the standard way
# used by edx-platform developers in their own environbments. 
if [ -z ${DEVSTACK_WORKSPACE+x} ]; then DEVSTACK_WORKSPACE=$(pwd)/..; fi


if [ ! -d "${DEVSTACK_WORKSPACE}/devstack" ]; then
    echo -e "${RED}Cannot find location of openedx/devstack, please set DEVSTACK_WORKSPACE to devstack's parent directory.'${NC}"
    exit 1
fi


if [ "$( docker ps -a | grep -c edx.devstack.lms )" -gt 0 ]; then
    echo -e "${GREEN}Ensuring LMS is up.${NC}"
    pushd "${DEVSTACK_WORKSPACE}/devstack" || exit # directory mysteriously disappeared
    make dev.up.ecommerce+lms+redis

    echo "Waiting for LMS MySQL"
    until docker exec -i edx.devstack.mysql57 mysql -u root -se "SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = 'root')" &> /dev/null
    do
      printf "."
      sleep 1
    done
    echo -e ""

    popd || exit # original directory mysteriously disappeared
else
    echo -e "${RED}LMS Docker Container is Missing, and is required, please compose the openedx devstack first${NC}"
    exit 1
fi

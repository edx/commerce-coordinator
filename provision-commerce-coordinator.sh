#!/usr/bin/env bash

name="commerce_coordinator"
port="8140"

RED="\x1B[31m"
GREEN="\x1B[32m"
NC="\x1B[0m"

bash ./find-start-lms.sh

# Install requirements
# Can be skipped right now because we're using the --build flag on docker-compose. This will need to be changed once we move to devstack.

# Wait for MySQL
echo "Waiting for MySQL"
until docker exec -i edx.devstack.mysql80 mysql -u root -se "SELECT EXISTS(SELECT 1 FROM mysql.user WHERE user = 'root')" &> /dev/null
do
  printf "."
  sleep 1
done
sleep 5
echo -e ""

# Create the database
docker exec -i edx.devstack.mysql80 mysql -u root -se "CREATE DATABASE commerce_coordinator;"

# Run migrations
echo -e "${GREEN}Running migrations for ${name}...${NC}"
make migrate

# Create superuser
echo -e "${GREEN}Creating super-user for ${name}...${NC}"
python ./manage.py shell << EOIS
from django.contrib.auth import get_user_model;
User = get_user_model();
User.objects.create_superuser("edx", "edx@example.com", "edx") if not User.objects.filter(username="edx").exists() else None;
EOIS

lms_exec() {
    docker exec -t edx.devstack.lms  bash -c "source /edx/app/edxapp/edxapp_env && python /edx/app/edxapp/edx-platform/manage.py lms --settings=devstack_docker ${*}"
}


# Provision IDA User in LMS (https://2u-internal.atlassian.net/wiki/spaces/SRE/pages/19267432/Setup+OAuth+Client+and+JWT+for+Internal+Services+Django+Oauth+Toolkit+version)
echo -e "${GREEN}Provisioning ${name}_worker in LMS...${NC}"
lms_exec "manage_user ${name}_worker ${name}_worker@example.com --staff --superuser"
lms_exec "create_dot_application --grant-type authorization-code --skip-authorization --redirect-uris 'http://localhost:${port}/complete/edx-oauth2/' --client-id '${name}-sso-key' --client-secret '${name}-sso-secret' --scopes 'user_id' ${name}-sso ${name}_worker"
lms_exec "create_dot_application --grant-type client-credentials --client-id '${name}-backend-service-key' --client-secret '${name}-backend-service-secret' ${name}-backend-service ${name}_worker"

echo -e "${GREEN}Provisioning titan_worker in LMS...${NC}"
lms_exec "manage_user titan_worker titan_worker@example.com --staff --superuser"
lms_exec "create_dot_application --grant-type client-credentials --client-id 'titan-backend-service-key' --client-secret 'titan-backend-service-secret' titan-backend-service titan_worker"

echo -e "${GREEN}Processing static files...${NC}"
python ./manage.py collectstatic

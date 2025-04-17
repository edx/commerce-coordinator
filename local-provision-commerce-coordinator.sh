name="commerce_coordinator"
port="8140"

ida_name="commerce-coordinator"

# Create superuser
echo -e "${GREEN}Creating super-user for ${name}...${NC}"
bash -c "echo 'from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser(\"edx\", \"edx@example.com\", \"edx\") if not User.objects.filter(username=\"edx\").exists() else None' | python manage.py shell"

# Provision IDA User in LMS
echo -e "${GREEN}Provisioning ${name}_worker in LMS...${NC}"
docker exec -t edx.devstack.lms  bash -c "source /edx/app/edxapp/edxapp_env && python /edx/app/edxapp/edx-platform/manage.py lms --settings=devstack_docker manage_user ${name}_worker ${name}_worker@example.com --staff --superuser"

# Create the DOT applications - one for single sign-on and one for backend service IDA-to-IDA authentication.
docker exec -t edx.devstack.lms  bash -c "source /edx/app/edxapp/edxapp_env && python /edx/app/edxapp/edx-platform/manage.py lms --settings=devstack_docker create_dot_application --grant-type authorization-code --skip-authorization --redirect-uris 'http://localhost:${port}/complete/edx-oauth2/' --client-id '${ida_name}-sso-key' --client-secret '${ida_name}-sso-secret' --scopes 'user_id' ${ida_name}-sso ${name}_worker"
docker exec -t edx.devstack.lms bash -c "source /edx/app/edxapp/edxapp_env && python /edx/app/edxapp/edx-platform/manage.py lms --settings=devstack_docker create_dot_application --grant-type client-credentials --client-id '${ida_name}-backend-service-key' --client-secret '${ida_name}-backend-service-secret' ${ida_name}-backend-service ${name}_worker"

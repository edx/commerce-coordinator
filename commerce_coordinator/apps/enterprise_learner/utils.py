from commerce_coordinator.apps.enterprise_learner.enterprise_client import EnterpriseApiClient


def is_user_enterprise_learner(request):
    """
    Check if user is enterprise learner
    :param request: request object
    :return: Boolean whether user is enterprise learner or not
    """
    if (EnterpriseApiClient().check_user_is_enterprise_customer(request.user.username)):
        return True
    return False

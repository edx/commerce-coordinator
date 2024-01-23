"""Enterprise Learner Utils Test"""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse
from mock import patch

from commerce_coordinator.apps.enterprise_learner.utils import is_user_enterprise_learner

User = get_user_model()


class TestEnterpriseLearnerUtils(TestCase):
    """
    Test class for utils
    """
    url = reverse('lms:payment_page_redirect')

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='test', email='test@example.com', password='secret'
        )

    @patch(
        'commerce_coordinator.apps.enterprise_learner.enterprise_client'
        '.EnterpriseApiClient.check_user_is_enterprise_customer'
        )
    def test_check_user_enterprise(self, mock_enterprise_user):
        request = self.factory.get(self.url)
        request.user = self.user
        mock_enterprise_user.return_value = True
        enterprise_user = is_user_enterprise_learner(request)
        self.assertTrue(enterprise_user, f'{request.user} is an enterprise user')

    @patch(
        'commerce_coordinator.apps.enterprise_learner.enterprise_client'
        '.EnterpriseApiClient.check_user_is_enterprise_customer'
        )
    def test_check_user_non_enterprise(self, mock_enterprise_user):
        request = self.factory.get(self.url)
        request.user = self.user
        mock_enterprise_user.return_value = False
        enterprise_user = is_user_enterprise_learner(request)
        self.assertFalse(enterprise_user, f'{request.user} is not an enterprise user')

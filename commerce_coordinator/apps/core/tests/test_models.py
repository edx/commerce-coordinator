""" Tests for core models. """

import mock
from django.test import TestCase
from django_dynamic_fixture import G
from social_django.models import UserSocialAuth

from commerce_coordinator.apps.core.models import User


class UserTests(TestCase):
    """ User model tests. """
    TEST_CONTEXT = {'foo': 'bar', 'baz': None}

    def test_access_token(self):
        user = G(User)
        self.assertIsNone(user.access_token)

        social_auth = G(UserSocialAuth, user=user)
        self.assertIsNone(user.access_token)

        access_token = 'My voice is my passport. Verify me.'
        social_auth.extra_data['access_token'] = access_token
        social_auth.save()
        self.assertEqual(user.access_token, access_token)

    def test_get_full_name(self):
        """ Test that the user model concatenates first and last name if the full name is not set. """
        full_name = 'George Costanza'
        user = G(User, full_name=full_name)
        self.assertEqual(user.get_full_name(), full_name)

        first_name = 'Jerry'
        last_name = 'Seinfeld'
        user = G(User, full_name=None, first_name=first_name, last_name=last_name)
        expected = f'{first_name} {last_name}'
        self.assertEqual(user.get_full_name(), expected)

        user = G(User, full_name=full_name, first_name=first_name, last_name=last_name)
        self.assertEqual(user.get_full_name(), full_name)

    def test_string(self):
        """Verify that the model's string method returns the user's full name."""
        full_name = 'Bob'
        user = G(User, full_name=full_name)
        self.assertEqual(str(user), full_name)

    def test_add_lms_user_id(self):
        '''
        Verify lms_user_id is added to user if exists in social_auth entry.
        '''
        full_name = 'Kosmo Kramer'
        user = G(User, full_name=full_name)
        assert user.lms_user_id is None

        UserSocialAuth.objects.create(
            user=user,
            provider='edx-oauth2',
            uid='1',
            extra_data={'user_id': 1337, 'access_token': 'access_token_1'}
        )

        user.add_lms_user_id('Calling from test')
        user.refresh_from_db()
        assert user.lms_user_id == 1337

    def test_add_lms_user_id_does_not_change_if_exists(self):
        full_name = 'Elaine Benes'
        user = G(User, full_name=full_name, lms_user_id=1234)
        assert user.lms_user_id == 1234

        UserSocialAuth.objects.create(
            user=user,
            provider='edx-oauth2',
            uid='1',
            extra_data={'user_id': 9999, 'access_token': 'access_token_1'}
        )

        user.add_lms_user_id('Calling from test')
        user.refresh_from_db()
        assert user.lms_user_id == 1234

    def test_add_lms_user_id_not_added_if_no_auth_entries(self):
        '''
        If no auth_entries in social_auth, lms_user_id should not be updated.
        '''
        full_name = 'Newman...'
        user = G(User, full_name=full_name)
        assert user.lms_user_id is None

        assert not UserSocialAuth.objects.filter(user=user).exists()

        user.add_lms_user_id('Calling from test')
        user.refresh_from_db()
        assert user.lms_user_id is None

    @mock.patch('commerce_coordinator.apps.core.models.User._get_lms_user_id_from_social_auth')
    def test_add_lms_user_id_not_added_if_get_from_social_auth_fails(self, mock_get_lms_user_id_from_social_auth):
        """
        If fetching social auth entry excepts, lms_user_id should not be updated.
        """
        full_name = 'Jerry the Mouse'
        user = G(User, full_name=full_name)
        assert user.lms_user_id is None

        UserSocialAuth.objects.create(
            user=user,
            provider='edx-oauth2',
            uid='1',
            extra_data={'user_id': 1337, 'access_token': 'access_token_1'}
        )

        mock_get_lms_user_id_from_social_auth.side_effect = Exception('Something went wrong')
        with self.assertRaises(Exception):
            user.add_lms_user_id('Calling from test')
        user.refresh_from_db()
        assert user.lms_user_id is None

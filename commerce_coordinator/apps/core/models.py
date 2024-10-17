""" Core models. """

import logging

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class User(AbstractUser):
    """
    Custom user model for use with python-social-auth via edx-auth-backends.

    .. pii: Stores full name, username, and email address for a user.
    .. pii_types: name, username, email_address
    .. pii_retirement: local_api

    """
    full_name = models.CharField(_('Full Name'), max_length=255, blank=True, null=True)
    lms_user_id = models.IntegerField(null=True, db_index=True)

    @property
    def access_token(self):
        """
        Returns an OAuth2 access token for this user, if one exists; otherwise None.
        Assumes user has authenticated at least once with the OAuth2 provider (LMS).
        """
        try:
            return self.social_auth.first().extra_data['access_token']  # pylint: disable=no-member
        except Exception:  # pylint: disable=broad-except
            return None

    class Meta:
        get_latest_by = 'date_joined'

    def get_full_name(self):
        return self.full_name or super().get_full_name()

    def __str__(self):
        return str(self.get_full_name())

    def add_lms_user_id(self, called_from):
        """
        If this user does not already have an LMS user id, look for the id in social auth. If the id can be found,
        add it to the user and save the user.
        The LMS user_id may already be present for the user. It may have been added from the jwt (see the
        EDX_DRF_EXTENSIONS.JWT_PAYLOAD_USER_ATTRIBUTE_MAPPING settings) or by a previous call to this method.
        Arguments:
            called_from (String): Descriptive string describing the caller. This will be included in log messages.
        """
        if not self.lms_user_id:
            # Check for the LMS user id in social auth
            lms_user_id_social_auth, social_auth_id = self._get_lms_user_id_from_social_auth()
            if lms_user_id_social_auth:
                self.lms_user_id = lms_user_id_social_auth
                self.save()
                log_message = (
                    'Saving lms_user_id from social auth with id %s '
                    'for user %s. Called from %s',
                    social_auth_id,
                    self.id,
                    called_from
                )
                logger.info(log_message)
            else:
                log_message = (
                    'No lms_user_id found in social auth with id %s '
                    'for user %s. Called from %s',
                    social_auth_id,
                    self.id,
                    called_from
                )
                logger.warning(log_message)

    def _get_lms_user_id_from_social_auth(self):
        """
        Find the LMS user_id passed through social auth. Because a single user_id can be associated with multiple
        provider/uid combinations, start by checking the most recently saved social auth entry.
        Returns:
            (lms_user_id, social_auth_id): a tuple containing the LMS user id and the id of the social auth entry
                where the LMS user id was found. Returns None, None if the LMS user id was not found.
        """
        try:
            auth_entries = self.social_auth.order_by('-id')
            if auth_entries:
                for auth_entry in auth_entries:
                    lms_user_id_social_auth = auth_entry.extra_data.get('user_id')
                    if lms_user_id_social_auth:
                        return lms_user_id_social_auth, auth_entry.id
        except Exception:  # pylint: disable=broad-except
            logger.warning('Exception retrieving lms_user_id from social_auth for user %s.', self.id, exc_info=True)
        return None, None

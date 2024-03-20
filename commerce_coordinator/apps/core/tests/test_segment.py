"""
Tests for segment module.
"""
import mock
from django.test.utils import override_settings

from commerce_coordinator.apps.core import segment


@mock.patch("commerce_coordinator.apps.core.segment.analytics.track")
@mock.patch("commerce_coordinator.apps.core.segment.logger")
@override_settings(SEGMENT_KEY="dummy_key")
def test_track_with_segment_key(mock_logger, mock_track):
    lms_user_id = 'test_id'
    event = 'test_event'

    segment.track(lms_user_id=lms_user_id, event=event)

    mock_track.assert_called_once_with(lms_user_id, event, None, None, None, None, None, None)
    mock_logger.debug.assert_not_called()


@mock.patch("commerce_coordinator.apps.core.segment.analytics.track")
@mock.patch("commerce_coordinator.apps.core.segment.logger")
def test_track_without_segment_key(mock_logger, mock_track):
    lms_user_id = 'test_id'
    event = 'test_event'

    segment.track(lms_user_id=lms_user_id, event=event)

    mock_track.assert_not_called()
    mock_logger.debug.assert_called_once_with(
        f"{event} for user {lms_user_id} not tracked because SEGMENT_KEY is not set."
    )

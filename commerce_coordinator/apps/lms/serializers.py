"""Serializers for LMS (edx-platform) service"""
from typing import Dict

from rest_framework import serializers

from commerce_coordinator.apps.core.serializers import CoordinatorSerializer


# Originally stolen verbatim from Ecomm
class OrderCreatedSignalInputSerializer(CoordinatorSerializer):
    """
    Serializer for order_created_signal input validation.
    """
    sku = serializers.ListField(
        child=serializers.CharField(), allow_empty=False
    )
    edx_lms_user_id = serializers.IntegerField(allow_null=False)
    email = serializers.EmailField(allow_null=False)
    coupon_code = serializers.CharField(allow_null=True)


def enrollment_attribute_key(namespace: str, name: str) -> str:
    """ Returns the key for the given namespace and name """
    return f"{namespace}.{name}"


class EnrollmentAttributeSerializer(CoordinatorSerializer):
    """
    Serializer for Enrollment Attribute input validation.

    Input data should look like this:

    .. code-block:: json

        {
            "namespace": "courseware",
            "name": "provider_id",
            "value": "hogwarts"
        }

    """
    namespace = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    value = serializers.CharField(required=True)

    @staticmethod
    def dict_tuple(data: dict) -> (str, str):
        """ Converts serializer data to a tuple of (f"{namespace}.{name}", value) """
        return enrollment_attribute_key(data['namespace'], data['name']), data['value']


class CourseRefundInputSerializer(CoordinatorSerializer):
    """
    Serializer for Course Refund input validation.

    Input data should look like this:

    .. code-block:: json

        {
            "course_id": "course-v1:edX+DemoX+DemoC",
            "username": "johndoe",
            "enrollment_attributes": [
                {
                    "namespace": "courseware",
                    "name": "provider_id",
                    "value": "hogwarts"
                }
            ]
        }

    """
    course_id = serializers.CharField(required=True)
    username = serializers.CharField(required=True)
    enrollment_attributes = EnrollmentAttributeSerializer(many=True)

    def enrollment_attributes_dict(self) -> Dict[str, str]:
        """ Converts serializer data to a dict of {f"{namespace}.{name}": value, ... n} """
        return dict([EnrollmentAttributeSerializer.dict_tuple(e) for e in self.data['enrollment_attributes']])

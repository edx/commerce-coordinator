""" Commercetools Application Consonants """

COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM = 'commercetools'
COMMERCETOOLS_REFUND = 'commercetools_refund'

SOURCE_SYSTEM = COMMERCETOOLS_ORDER_MANAGEMENT_SYSTEM


EMAIL_NOTIFICATION_CACHE_TTL_SECS = (60 * 60 * 24) - 60  # 23hrs 59mins


CT_ORDER_PRODUCT_TYPE_FOR_BRAZE = {
    'edx_course': 'course',
    'edx_program': 'program',
    'edx_course_entitlement': 'program'
}

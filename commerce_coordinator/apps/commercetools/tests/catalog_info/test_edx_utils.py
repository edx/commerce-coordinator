import json
import unittest
from typing import Union

from commercetools.platform.models import Customer as CTCustomer
from commercetools.platform.models import Order as CTOrder
from commercetools.platform.models import Product as CTProduct
from utils import uuid4_str

from commerce_coordinator.apps.commercetools.catalog_info.edx_utils import (
    get_edx_items,
    get_edx_lms_user_id,
    get_edx_lms_user_name,
    get_edx_product_course_key,
    get_edx_product_course_run_key,
    is_edx_lms_order
)
from commerce_coordinator.apps.commercetools.tests.conftest import DEFAULT_EDX_LMS_USER_ID, gen_customer, gen_order

_TEST_USER_NAME = "jdoe22"


class TestEdXFunctions(unittest.TestCase):
    order: Union[CTOrder, None]
    user: Union[CTCustomer, None]

    def setUp(self):
        self.order = gen_order(uuid4_str())
        self.user = gen_customer("email@example.com", _TEST_USER_NAME)
        super().setUp()

    def tearDown(self):
        self.order = None
        self.user = None
        super().tearDown()

    def test_get_edx_product_course_run_key(self):
        li = self.order.line_items[0]
        prodvar = li.variant

        self.assertEqual(get_edx_product_course_run_key(prodvar), prodvar.sku)
        self.assertEqual(get_edx_product_course_run_key(li), prodvar.sku)

    def test_get_edx_product_course_key(self):
        li = self.order.line_items[0]
        prod = CTProduct.deserialize(json.loads(
            """
            {
              "id": "9895858a-2d43-471d-be25-7a5007d52b9f",
              "version": 15,
              "createdAt": "2023-10-29T15:42:41.126000+00:00",
              "lastModifiedAt": "2023-12-06T17:47:14.951000+00:00",
              "lastModifiedBy": {
              },
              "createdBy": {
              },
              "key": "MichiganX+InjuryPreventionX",
              "productType": {
                "typeId": "product-type",
                "id": "b2aa56d2-7b98-4d51-9d70-81d675a45686"
              },
              "masterData": {
                "published": true,
                "current": {
                  "name": {
                    "en-US": "Injury Prevention for Children & Teens"
                  },
                  "categories": [
                    {
                      "typeId": "category",
                      "id": "5a79fdbc-d42a-4d88-a53f-926dbe9869ee"
                    }
                  ],
                  "categoryOrderHints": {
                  },
                  "description": {
                    "en-US": "<p>Injuries, such as motor vehicle crash, youth violence, and suicide, are the leading cause of child and adolescent death. However, almost all of these injuries can be prevented through the widespread application of evidence-based practices and policies.</p> <p>Public health experts, nurses, physicians, social workers, teachers, child care providers, and parents all play a vital role in pediatric injury prevention. Despite its impact, very little training on injury prevention science currently exists.</p> <p>This course lays a broad foundation for pediatric injury prevention and will increase your understanding of this major public health issue through powerful, concise, up-to-date lectures, interviews, and demonstrations from a multidisciplinary panel of nationally-recognized injury prevention experts.</p> <p>This course is designed for multiple fields and levels of training, including healthcare, kinesiology, public policy, social work, pharmacy, dentistry, and psychology.The course is also appropriate for educators, coaches, child care providers, and parents.</p> <p>Asa learner, you will have the ability to select all modules or individual topics that interest you most. Comprised of 8 modules, this course may be taken from the comfort of your home or office, and you can learn at your own pace.</p> <p><strong>Obtaining Credit for Continuing Education</strong></p> <p>Learners may apply for Continuing Medical Education (CME), American Board of Pediatrics’ (ABP) Maintenance of Certification (MOC) Part II, or Certified Health Education Specialist (CHES) credit. See the FAQ for more information on each offering.</p>"
                  },
                  "slug": {
                    "en-US": "injury-prevention-for-children-teens"
                  },
                  "metaTitle": {
                    "de-DE": "",
                    "en-US": ""
                  },
                  "metaDescription": {
                    "de-DE": "",
                    "en-US": ""
                  },
                  "masterVariant": {
                    "id": 1,
                    "sku": "course-v1:MichiganX+InjuryPreventionX+1T2021",
                    "key": "course-v1:MichiganX+InjuryPreventionX+1T2021",
                    "prices": [
                    ],
                    "attributes": [
                      {
                        "name": "primarySubjectArea",
                        "value": {
                          "key": "business",
                          "label": "Business"
                        }
                      },
                      {
                        "name": "brand-text",
                        "value": "MichiganX"
                      },
                      {
                        "name": "date-created",
                        "value": "2019-08-21T00:02:00.000Z"
                      },
                      {
                        "name": "status",
                        "value": {
                          "key": "Published",
                          "label": "Published"
                        }
                      },
                      {
                        "name": "duration-low",
                        "value": 4
                      },
                      {
                        "name": "duration-high",
                        "value": 5
                      },
                      {
                        "name": "duration-unit",
                        "value": {
                          "key": "duration-weeks",
                          "label": "Weeks"
                        }
                      },
                      {
                        "name": "effort-low",
                        "value": 4
                      },
                      {
                        "name": "effort-high",
                        "value": 6
                      },
                      {
                        "name": "effort-unit",
                        "value": {
                          "key": "effot-per-week",
                          "label": "Hours per Week"
                        }
                      },
                      {
                        "name": "courserun-id",
                        "value": "32126"
                      },
                      {
                        "name": "courserun_start",
                        "value": "2021-04-19"
                      },
                      {
                        "name": "courserun-end",
                        "value": "2024-04-18"
                      },
                      {
                        "name": "courserun-status",
                        "value": {
                          "key": "courserun-status-published",
                          "label": "Published"
                        }
                      },
                      {
                        "name": "external-ids-product",
                        "value": "MichiganX+InjuryPreventionX"
                      },
                      {
                        "name": "external-ids-variant",
                        "value": "course-v1:MichiganX+InjuryPreventionX+1T2021"
                      }
                    ],
                    "images": [
                    ],
                    "assets": [
                    ]
                  },
                  "variants": [
                    {
                      "id": 2,
                      "sku": "course-v1:MichiganX+InjuryPreventionX+1T2018",
                      "key": "course-v1:MichiganX+InjuryPreventionX+1T2018",
                      "prices": [
                      ],
                      "attributes": [
                        {
                          "name": "primarySubjectArea",
                          "value": {
                            "key": "business",
                            "label": "Business"
                          }
                        },
                        {
                          "name": "brand-text",
                          "value": "MichiganX"
                        },
                        {
                          "name": "date-created",
                          "value": "2019-08-21T00:02:00.000Z"
                        },
                        {
                          "name": "status",
                          "value": {
                            "key": "Published",
                            "label": "Published"
                          }
                        },
                        {
                          "name": "duration-low",
                          "value": 4
                        },
                        {
                          "name": "duration-high",
                          "value": 5
                        },
                        {
                          "name": "duration-unit",
                          "value": {
                            "key": "duration-weeks",
                            "label": "Weeks"
                          }
                        },
                        {
                          "name": "effort-low",
                          "value": 4
                        },
                        {
                          "name": "effort-high",
                          "value": 6
                        },
                        {
                          "name": "effort-unit",
                          "value": {
                            "key": "effot-per-week",
                            "label": "Hours per Week"
                          }
                        },
                        {
                          "name": "courserun-id",
                          "value": "7115"
                        },
                        {
                          "name": "courserun_start",
                          "value": "2018-04-24"
                        },
                        {
                          "name": "courserun-end",
                          "value": "2021-04-24"
                        },
                        {
                          "name": "courserun-status",
                          "value": {
                            "key": "courserun-status-unpublished",
                            "label": "Unpublished"
                          }
                        },
                        {
                          "name": "external-ids-product",
                          "value": "MichiganX+InjuryPreventionX"
                        },
                        {
                          "name": "external-ids-variant",
                          "value": "course-v1:MichiganX+InjuryPreventionX+1T2018"
                        }
                      ],
                      "images": [
                      ],
                      "assets": [
                      ]
                    }
                  ],
                  "searchKeywords": {
                  }
                },
                "staged": {
                  "name": {
                    "en-US": "Injury Prevention for Children & Teens"
                  },
                  "categories": [
                    {
                      "typeId": "category",
                      "id": "5a79fdbc-d42a-4d88-a53f-926dbe9869ee"
                    }
                  ],
                  "categoryOrderHints": {
                  },
                  "description": {
                    "en-US": "<p>Injuries, such as motor vehicle crash, youth violence, and suicide, are the leading cause of child and adolescent death. However, almost all of these injuries can be prevented through the widespread application of evidence-based practices and policies.</p> <p>Public health experts, nurses, physicians, social workers, teachers, child care providers, and parents all play a vital role in pediatric injury prevention. Despite its impact, very little training on injury prevention science currently exists.</p> <p>This course lays a broad foundation for pediatric injury prevention and will increase your understanding of this major public health issue through powerful, concise, up-to-date lectures, interviews, and demonstrations from a multidisciplinary panel of nationally-recognized injury prevention experts.</p> <p>This course is designed for multiple fields and levels of training, including healthcare, kinesiology, public policy, social work, pharmacy, dentistry, and psychology.The course is also appropriate for educators, coaches, child care providers, and parents.</p> <p>Asa learner, you will have the ability to select all modules or individual topics that interest you most. Comprised of 8 modules, this course may be taken from the comfort of your home or office, and you can learn at your own pace.</p> <p><strong>Obtaining Credit for Continuing Education</strong></p> <p>Learners may apply for Continuing Medical Education (CME), American Board of Pediatrics’ (ABP) Maintenance of Certification (MOC) Part II, or Certified Health Education Specialist (CHES) credit. See the FAQ for more information on each offering.</p>"
                  },
                  "slug": {
                    "en-US": "injury-prevention-for-children-teens"
                  },
                  "metaTitle": {
                    "de-DE": "",
                    "en-US": ""
                  },
                  "metaDescription": {
                    "de-DE": "",
                    "en-US": ""
                  },
                  "masterVariant": {
                    "id": 1,
                    "sku": "course-v1:MichiganX+InjuryPreventionX+1T2021",
                    "key": "course-v1:MichiganX+InjuryPreventionX+1T2021",
                    "prices": [
                    ],
                    "attributes": [
                      {
                        "name": "primarySubjectArea",
                        "value": {
                          "key": "business",
                          "label": "Business"
                        }
                      },
                      {
                        "name": "brand-text",
                        "value": "MichiganX"
                      },
                      {
                        "name": "date-created",
                        "value": "2019-08-21T00:02:00.000Z"
                      },
                      {
                        "name": "status",
                        "value": {
                          "key": "Published",
                          "label": "Published"
                        }
                      },
                      {
                        "name": "duration-low",
                        "value": 4
                      },
                      {
                        "name": "duration-high",
                        "value": 5
                      },
                      {
                        "name": "duration-unit",
                        "value": {
                          "key": "duration-weeks",
                          "label": "Weeks"
                        }
                      },
                      {
                        "name": "effort-low",
                        "value": 4
                      },
                      {
                        "name": "effort-high",
                        "value": 6
                      },
                      {
                        "name": "effort-unit",
                        "value": {
                          "key": "effot-per-week",
                          "label": "Hours per Week"
                        }
                      },
                      {
                        "name": "courserun-id",
                        "value": "32126"
                      },
                      {
                        "name": "courserun_start",
                        "value": "2021-04-19"
                      },
                      {
                        "name": "courserun-end",
                        "value": "2024-04-18"
                      },
                      {
                        "name": "courserun-status",
                        "value": {
                          "key": "courserun-status-published",
                          "label": "Published"
                        }
                      },
                      {
                        "name": "external-ids-product",
                        "value": "MichiganX+InjuryPreventionX"
                      },
                      {
                        "name": "external-ids-variant",
                        "value": "course-v1:MichiganX+InjuryPreventionX+1T2021"
                      },
                      {
                        "name": "test-reference-category",
                        "value": {
                          "typeId": "category",
                          "id": "d4ae2b24-3be4-4033-b55c-237ca62cc4bf"
                        }
                      }
                    ],
                    "images": [
                    ],
                    "assets": [
                    ]
                  },
                  "variants": [
                    {
                      "id": 2,
                      "sku": "course-v1:MichiganX+InjuryPreventionX+1T2018",
                      "key": "course-v1:MichiganX+InjuryPreventionX+1T2018",
                      "prices": [
                      ],
                      "attributes": [
                        {
                          "name": "primarySubjectArea",
                          "value": {
                            "key": "business",
                            "label": "Business"
                          }
                        },
                        {
                          "name": "brand-text",
                          "value": "MichiganX"
                        },
                        {
                          "name": "date-created",
                          "value": "2019-08-21T00:02:00.000Z"
                        },
                        {
                          "name": "status",
                          "value": {
                            "key": "Published",
                            "label": "Published"
                          }
                        },
                        {
                          "name": "duration-low",
                          "value": 4
                        },
                        {
                          "name": "duration-high",
                          "value": 5
                        },
                        {
                          "name": "duration-unit",
                          "value": {
                            "key": "duration-weeks",
                            "label": "Weeks"
                          }
                        },
                        {
                          "name": "effort-low",
                          "value": 4
                        },
                        {
                          "name": "effort-high",
                          "value": 6
                        },
                        {
                          "name": "effort-unit",
                          "value": {
                            "key": "effot-per-week",
                            "label": "Hours per Week"
                          }
                        },
                        {
                          "name": "courserun-id",
                          "value": "7115"
                        },
                        {
                          "name": "courserun_start",
                          "value": "2018-04-24"
                        },
                        {
                          "name": "courserun-end",
                          "value": "2021-04-24"
                        },
                        {
                          "name": "courserun-status",
                          "value": {
                            "key": "courserun-status-unpublished",
                            "label": "Unpublished"
                          }
                        },
                        {
                          "name": "external-ids-product",
                          "value": "MichiganX+InjuryPreventionX"
                        },
                        {
                          "name": "external-ids-variant",
                          "value": "course-v1:MichiganX+InjuryPreventionX+1T2018"
                        }
                      ],
                      "images": [
                      ],
                      "assets": [
                      ]
                    }
                  ],
                  "searchKeywords": {
                  }
                },
                "hasStagedChanges": true
              },
              "taxCategory": {
                "typeId": "tax-category",
                "id": "1ae3b4da-8e7c-4f36-b777-662007e41e88"
              },
              "priceMode": "Standalone"
            }
            """))
        self.assertEqual(get_edx_product_course_key(prod), "MichiganX+InjuryPreventionX")
        self.assertEqual(get_edx_product_course_key(li), "edx-prod-142765f0-7c1e-4ac4-93fe-8516d87f985e")

    def test_get_edx_items(self):
        self.assertEqual(len(get_edx_items(self.order)), 1)

    def test_is_edx_lms_order(self):
        self.assertTrue(is_edx_lms_order(self.order))

    def test_get_edx_lms_user_id(self):
        self.assertEqual(get_edx_lms_user_id(self.user), DEFAULT_EDX_LMS_USER_ID)

    def test_get_edx_lms_user_name(self):
        self.assertEqual(get_edx_lms_user_name(self.user), _TEST_USER_NAME)


if __name__ == '__main__':
    unittest.main()

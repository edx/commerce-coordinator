# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/edx/commerce-coordinator/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                   |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|--------------------------------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| commerce\_coordinator/\_\_init\_\_.py                                                  |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/\_\_init\_\_.py                                             |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/api/\_\_init\_\_.py                                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/api/models.py                                               |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/api/serializers.py                                          |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/api/tests/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/api/urls.py                                                 |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/api/v1/\_\_init\_\_.py                                      |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/api/v1/tests/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/api/v1/urls.py                                              |        2 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/api/v1/views.py                                             |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/\_\_init\_\_.py                               |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/authentication.py                             |        6 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/catalog\_info/constants.py                    |       43 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/catalog\_info/edx\_utils.py                   |       64 |        1 |       16 |        1 |     98% |        68 |
| commerce\_coordinator/apps/commercetools/catalog\_info/foundational\_types.py          |       18 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/catalog\_info/utils.py                        |       69 |        0 |       30 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/clients.py                                    |      255 |        9 |       30 |        4 |     95% |341, 371-372, 497->499, 538-539, 628-631, 719-723 |
| commerce\_coordinator/apps/commercetools/constants.py                                  |        5 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/data.py                                       |       45 |        0 |        8 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/filters.py                                    |        6 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/pipeline.py                                   |      132 |       18 |       20 |        4 |     84% |80-82, 124-126, 155, 182-185, 191-193, 278-279, 346-347 |
| commerce\_coordinator/apps/commercetools/serializers.py                                |       92 |        0 |        2 |        1 |     99% |    21->23 |
| commerce\_coordinator/apps/commercetools/signals.py                                    |       23 |        2 |        2 |        0 |     92% |     63-66 |
| commerce\_coordinator/apps/commercetools/sub\_messages/\_\_init\_\_.py                 |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/sub\_messages/signals\_delayed.py             |       16 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/sub\_messages/signals\_dispatch.py            |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/sub\_messages/tasks.py                        |      135 |        8 |       24 |        5 |     92% |166, 251, 325->321, 335-336, 339->382, 362-369 |
| commerce\_coordinator/apps/commercetools/tasks.py                                      |       76 |       23 |       10 |        3 |     67% |49-50, 53-69, 79-80, 85, 99-100, 110-114, 158-177 |
| commerce\_coordinator/apps/commercetools/tests/\_\_init\_\_.py                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/\_test\_cases.py                        |       25 |        0 |        2 |        1 |     96% |  36->exit |
| commerce\_coordinator/apps/commercetools/tests/catalog\_info/\_\_init\_\_.py           |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/catalog\_info/test\_edx\_utils.py       |       68 |        1 |        2 |        1 |     97% |       114 |
| commerce\_coordinator/apps/commercetools/tests/catalog\_info/test\_utils.py            |       90 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/conftest.py                             |      123 |        1 |        8 |        1 |     98% |       134 |
| commerce\_coordinator/apps/commercetools/tests/constants.py                            |       10 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/mocks.py                                |       45 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/sub\_messages/\_\_init\_\_.py           |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/sub\_messages/test\_signals\_delayed.py |       45 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/sub\_messages/test\_tasks.py            |      214 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_authentication.py                 |       25 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_clients.py                        |      438 |        4 |        8 |        0 |     99% |690-701, 775-786 |
| commerce\_coordinator/apps/commercetools/tests/test\_data.py                           |       87 |        0 |        6 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_pipeline.py                       |      174 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_signals.py                        |       40 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_tasks.py                          |       58 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_utils.py                          |      189 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_views.py                          |      182 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/urls.py                                       |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/utils.py                                      |      104 |        1 |       26 |        2 |     98% |89->exit, 233 |
| commerce\_coordinator/apps/commercetools/views.py                                      |       55 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools\_frontend/constants.py                        |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools\_frontend/pipeline.py                         |        9 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/core/\_\_init\_\_.py                                        |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/cache.py                                               |       29 |       29 |        2 |        0 |      0% |      5-51 |
| commerce\_coordinator/apps/core/clients.py                                             |       26 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/core/constants.py                                           |       49 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/context\_processors.py                                 |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/exceptions.py                                          |        2 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/memcache.py                                            |       28 |        0 |        6 |        0 |    100% |           |
| commerce\_coordinator/apps/core/middleware.py                                          |       25 |        0 |        8 |        3 |     91% |22->26, 27->30, 31->38 |
| commerce\_coordinator/apps/core/models.py                                              |       41 |        2 |       10 |        2 |     92% |82->88, 84->82, 86-87 |
| commerce\_coordinator/apps/core/pipeline.py                                            |        6 |        6 |        0 |        0 |      0% |      5-23 |
| commerce\_coordinator/apps/core/segment.py                                             |        8 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/core/serializers.py                                         |       26 |        2 |        2 |        0 |     93% |     58-59 |
| commerce\_coordinator/apps/core/signal\_helpers.py                                     |       34 |        1 |        6 |        1 |     95% |        57 |
| commerce\_coordinator/apps/core/signals.py                                             |        5 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/\_\_init\_\_.py                                  |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_cache.py                                   |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_clients.py                                 |       11 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_context\_processors.py                     |        8 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_memcache.py                                |       46 |        0 |       10 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_middleware.py                              |       47 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_models.py                                  |       66 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_segment.py                                 |       20 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_serializers.py                             |       27 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_signal\_helpers.py                         |      107 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_tests\_utils.py                            |       18 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_views.py                                   |       37 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/utils.py                                         |      100 |       16 |       28 |        2 |     81% |270, 273-274, 285-313 |
| commerce\_coordinator/apps/core/views.py                                               |       77 |        0 |       10 |        0 |    100% |           |
| commerce\_coordinator/apps/demo\_lms/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/demo\_lms/filters.py                                        |       10 |        5 |        2 |        0 |     42% |     25-29 |
| commerce\_coordinator/apps/demo\_lms/models.py                                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/demo\_lms/pipeline.py                                       |        7 |        7 |        0 |        0 |      0% |      5-29 |
| commerce\_coordinator/apps/demo\_lms/signals.py                                        |       24 |        8 |        2 |        0 |     62% |41, 51, 61-63, 72-74 |
| commerce\_coordinator/apps/demo\_lms/tasks.py                                          |       12 |        3 |        0 |        0 |     75% |18, 28, 38 |
| commerce\_coordinator/apps/demo\_lms/tests.py                                          |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/demo\_lms/urls.py                                           |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/demo\_lms/views.py                                          |       18 |        9 |        0 |        0 |     50% |18-19, 34-36, 50-70, 78-79 |
| commerce\_coordinator/apps/ecommerce/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/clients.py                                        |       19 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/constants.py                                      |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/data.py                                           |      131 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/models.py                                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/pipeline.py                                       |       21 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/serializers.py                                    |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/signals.py                                        |        4 |        4 |        0 |        0 |      0% |       4-8 |
| commerce\_coordinator/apps/ecommerce/tests/\_\_init\_\_.py                             |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/tests/test\_clients.py                            |       21 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/tests/test\_views.py                              |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/urls.py                                           |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/views.py                                          |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/enterprise\_learner/enterprise\_client.py                   |       19 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/enterprise\_learner/tests/test\_enterprise\_client.py       |       32 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/enterprise\_learner/tests/test\_utils.py                    |       25 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/enterprise\_learner/utils.py                                |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/\_\_init\_\_.py                    |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/filters.py                         |       15 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/models.py                          |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/tests/\_\_init\_\_.py              |       14 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/tests/conftest.py                  |       17 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/tests/test\_filters.py             |       14 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/tests/test\_views.py               |      127 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/urls.py                            |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/views.py                           |       52 |        0 |        8 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/\_\_init\_\_.py                      |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/constants.py                         |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/exceptions.py                        |        9 |        9 |        0 |        0 |      0% |      3-15 |
| commerce\_coordinator/apps/frontend\_app\_payment/filters.py                           |       26 |       10 |        0 |        0 |     62% |27-28, 45-55, 72-75 |
| commerce\_coordinator/apps/frontend\_app\_payment/models.py                            |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/pipeline.py                          |       10 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/serializers.py                       |       31 |        4 |        2 |        0 |     82% |     64-67 |
| commerce\_coordinator/apps/frontend\_app\_payment/tests/\_\_init\_\_.py                |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/tests/test\_filters.py               |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/tests/test\_views.py                 |       27 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/urls.py                              |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/views.py                             |       18 |        6 |        0 |        0 |     67% |     28-36 |
| commerce\_coordinator/apps/lms/\_\_init\_\_.py                                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/clients.py                                              |       50 |        3 |        2 |        1 |     92% |42, 113, 165 |
| commerce\_coordinator/apps/lms/filters.py                                              |       11 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/serializers.py                                          |       32 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/signal\_handlers.py                                     |       12 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/signals.py                                              |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tasks.py                                                |       82 |        0 |       10 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/constants.py                                      |        9 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_clients.py                                  |       33 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_signals.py                                  |       31 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_tasks.py                                    |      134 |       18 |        0 |        0 |     87% |   303-350 |
| commerce\_coordinator/apps/lms/tests/test\_utils.py                                    |       40 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_views.py                                    |      298 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/urls.py                                                 |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/utils.py                                                |       11 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/views.py                                                |      163 |        4 |       14 |        0 |     98% |223-226, 397 |
| commerce\_coordinator/apps/paypal/\_\_init\_\_.py                                      |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/clients.py                                           |       19 |        8 |        2 |        0 |     52% |     40-65 |
| commerce\_coordinator/apps/paypal/pipeline.py                                          |       33 |        0 |        6 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/signals.py                                           |        2 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/tests/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/tests/test\_pipeline.py                              |       16 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/tests/test\_views.py                                 |       51 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/urls.py                                              |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/views.py                                             |       72 |        3 |       12 |        3 |     93% |45, 60-61, 107->112, 108->107 |
| commerce\_coordinator/apps/rollout/\_\_init\_\_.py                                     |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/rollout/pipeline.py                                         |       59 |        1 |       18 |        1 |     97% |       119 |
| commerce\_coordinator/apps/rollout/tests/test\_pipeline.py                             |      146 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/rollout/tests/test\_util\_functions.py                      |       27 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/rollout/utils.py                                            |       25 |        3 |        8 |        0 |     85% |     62-64 |
| commerce\_coordinator/apps/rollout/waffle.py                                           |        8 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/\_\_init\_\_.py                                      |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/clients.py                                           |       99 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/constants.py                                         |       11 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/exceptions.py                                        |       29 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/filters.py                                           |        9 |        2 |        0 |        0 |     78% |     25-26 |
| commerce\_coordinator/apps/stripe/pipeline.py                                          |       54 |       21 |       10 |        2 |     58% |43-66, 96-109, 122-123, 172-173 |
| commerce\_coordinator/apps/stripe/signals.py                                           |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_clients.py                               |       78 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_pipeline.py                              |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_utils.py                                 |        9 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_views.py                                 |       66 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/urls.py                                              |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/utils.py                                             |        2 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/views.py                                             |       63 |       11 |       10 |        3 |     78% |65, 67, 111-144 |
| commerce\_coordinator/docker\_gunicorn\_configuration.py                               |       27 |       27 |       10 |        0 |      0% |      4-57 |
| commerce\_coordinator/urls.py                                                          |       22 |        0 |        0 |        0 |    100% |           |
|                                                                              **TOTAL** | **6405** |  **290** |  **424** |   **41** | **95%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/edx/commerce-coordinator/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/edx/commerce-coordinator/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/edx/commerce-coordinator/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/edx/commerce-coordinator/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fedx%2Fcommerce-coordinator%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/edx/commerce-coordinator/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.
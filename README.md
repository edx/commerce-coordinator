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
| commerce\_coordinator/apps/commercetools/catalog\_info/constants.py                    |       58 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/catalog\_info/edx\_utils.py                   |      102 |       20 |       32 |        4 |     78% |25-26, 85, 104, 121, 285-302 |
| commerce\_coordinator/apps/commercetools/catalog\_info/foundational\_types.py          |       19 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/catalog\_info/utils.py                        |       72 |        0 |       30 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/clients.py                                    |      520 |       74 |       82 |       23 |     83% |210, 317-322, 426-430, 475, 547-565, 706-712, 739, 761-768, 796->802, 803, 809->813, 817->820, 823->830, 834->836, 851->862, 877-878, 883, 994-997, 1063-1064, 1094-1098, 1189, 1283-1289, 1337-1343, 1363-1376, 1392-1399, 1414-1420, 1453-1459, 1539-1545, 1681-1687, 1717-1724, 1774-1781, 1846, 1849->1848, 1850->1849, 1857-1864, 1923, 1929 |
| commerce\_coordinator/apps/commercetools/constants.py                                  |        5 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/data.py                                       |       55 |        0 |       16 |        3 |     96% |115->114, 160->163, 165->174 |
| commerce\_coordinator/apps/commercetools/filters.py                                    |        6 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/http\_api\_client.py                          |       68 |        9 |       16 |        4 |     85% |31-41, 135, 150, 165, 172->171 |
| commerce\_coordinator/apps/commercetools/pipeline.py                                   |      161 |       20 |       36 |        4 |     85% |87-89, 129-131, 160, 177-180, 205-208, 214-216, 389-390 |
| commerce\_coordinator/apps/commercetools/predicate\_parser.py                          |      109 |       13 |       42 |       10 |     83% |114, 119->121, 130-131, 138, 250, 257-258, 269, 316, 326, 341, 350-353 |
| commerce\_coordinator/apps/commercetools/serializers.py                                |       97 |        0 |        2 |        1 |     99% |    21->23 |
| commerce\_coordinator/apps/commercetools/signals.py                                    |       31 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/sub\_messages/\_\_init\_\_.py                 |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/sub\_messages/signals\_delayed.py             |       16 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/sub\_messages/signals\_dispatch.py            |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/sub\_messages/tasks.py                        |      166 |        2 |       36 |        4 |     97% |216, 409, 431->434, 455->461 |
| commerce\_coordinator/apps/commercetools/tasks.py                                      |      143 |       13 |       20 |        2 |     91% |70-71, 78-91, 109-119, 252-257 |
| commerce\_coordinator/apps/commercetools/tests/\_\_init\_\_.py                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/\_test\_cases.py                        |       25 |        0 |        2 |        1 |     96% |  36->exit |
| commerce\_coordinator/apps/commercetools/tests/catalog\_info/\_\_init\_\_.py           |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/catalog\_info/test\_edx\_utils.py       |      118 |        1 |        2 |        1 |     98% |       211 |
| commerce\_coordinator/apps/commercetools/tests/catalog\_info/test\_utils.py            |       90 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/conftest.py                             |      119 |        1 |       12 |        1 |     98% |       145 |
| commerce\_coordinator/apps/commercetools/tests/constants.py                            |       10 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/mocks.py                                |       45 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/sub\_messages/\_\_init\_\_.py           |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/sub\_messages/test\_signals\_delayed.py |       45 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/sub\_messages/test\_tasks.py            |      343 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_authentication.py                 |       25 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_clients.py                        |      816 |        4 |       10 |        1 |     99% |764-775, 849-860, 1131->1136 |
| commerce\_coordinator/apps/commercetools/tests/test\_data.py                           |       87 |        0 |        6 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_http\_api\_client.py              |       79 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_pipeline.py                       |      206 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_signals.py                        |       77 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_tasks.py                          |      251 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_utils.py                          |      306 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_views.py                          |      197 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/urls.py                                       |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/utils.py                                      |      154 |        2 |       44 |        3 |     97% |94->exit, 297, 401 |
| commerce\_coordinator/apps/commercetools/views.py                                      |       61 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools\_frontend/constants.py                        |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/\_\_init\_\_.py                                        |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/cache.py                                               |       29 |       29 |        2 |        0 |      0% |      5-51 |
| commerce\_coordinator/apps/core/clients.py                                             |       26 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/core/constants.py                                           |       50 |        0 |        0 |        0 |    100% |           |
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
| commerce\_coordinator/apps/ecommerce/clients.py                                        |       28 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/constants.py                                      |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/data.py                                           |      133 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/models.py                                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/pipeline.py                                       |       21 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/serializers.py                                    |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/signals.py                                        |        4 |        4 |        0 |        0 |      0% |       4-8 |
| commerce\_coordinator/apps/ecommerce/tests/\_\_init\_\_.py                             |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/tests/test\_clients.py                            |       31 |        0 |        0 |        0 |    100% |           |
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
| commerce\_coordinator/apps/frontend\_app\_ecommerce/tests/test\_views.py               |      128 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/urls.py                            |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/views.py                           |       70 |        7 |       10 |        1 |     90% |   101-107 |
| commerce\_coordinator/apps/frontend\_app\_payment/\_\_init\_\_.py                      |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/constants.py                         |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/exceptions.py                        |        9 |        9 |        0 |        0 |      0% |      3-15 |
| commerce\_coordinator/apps/frontend\_app\_payment/filters.py                           |       26 |       10 |        0 |        0 |     62% |27-28, 45-55, 72-75 |
| commerce\_coordinator/apps/frontend\_app\_payment/models.py                            |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/pipeline.py                          |       10 |       10 |        2 |        0 |      0% |      4-23 |
| commerce\_coordinator/apps/frontend\_app\_payment/serializers.py                       |       31 |        4 |        2 |        0 |     82% |     64-67 |
| commerce\_coordinator/apps/frontend\_app\_payment/tests/\_\_init\_\_.py                |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/tests/test\_filters.py               |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/tests/test\_views.py                 |       27 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/urls.py                              |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/views.py                             |       18 |        6 |        0 |        0 |     67% |     28-36 |
| commerce\_coordinator/apps/iap/\_\_init\_\_.py                                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/authentication.py                                       |       25 |        1 |        4 |        1 |     93% |        51 |
| commerce\_coordinator/apps/iap/google\_validator.py                                    |       38 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/ios\_validator.py                                       |       20 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/payment\_processor.py                                   |      111 |        0 |       24 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/segment\_events.py                                      |       28 |        0 |        2 |        1 |     97% |  249->252 |
| commerce\_coordinator/apps/iap/serializers.py                                          |       16 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/signals.py                                              |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/tests/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/tests/test\_authentication.py                           |       39 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/tests/test\_google\_validator.py                        |       51 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/tests/test\_ios\_validator.py                           |       40 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/tests/test\_payment\_processor.py                       |      102 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/tests/test\_segment\_events.py                          |      131 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/tests/test\_utils.py                                    |      192 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/tests/test\_views.py                                    |      266 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/urls.py                                                 |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/iap/utils.py                                                |       72 |        1 |       20 |        0 |     99% |       208 |
| commerce\_coordinator/apps/iap/views.py                                                |      153 |        5 |       20 |        4 |     95% |134->136, 155, 234, 241, 313-314 |
| commerce\_coordinator/apps/lms/\_\_init\_\_.py                                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/clients.py                                              |       50 |        3 |        2 |        1 |     92% |42, 113, 165 |
| commerce\_coordinator/apps/lms/constants.py                                            |        2 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/filters.py                                              |       11 |        2 |        0 |        0 |     82% |     23-25 |
| commerce\_coordinator/apps/lms/serializers.py                                          |       35 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/signal\_handlers.py                                     |       12 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/signals.py                                              |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tasks.py                                                |       84 |        0 |       10 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/constants.py                                      |       10 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_clients.py                                  |       33 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_signals.py                                  |       31 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_tasks.py                                    |      134 |       18 |        0 |        0 |     87% |   305-352 |
| commerce\_coordinator/apps/lms/tests/test\_utils.py                                    |       64 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_views.py                                    |      542 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/urls.py                                                 |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/utils.py                                                |       43 |        0 |       18 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/views.py                                                |      318 |       31 |       42 |        5 |     89% |87-89, 236-239, 422, 438, 448-452, 495-497, 512-514, 530-532, 556-561, 682->694, 752-755 |
| commerce\_coordinator/apps/order\_fulfillment/\_\_init\_\_.py                          |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/order\_fulfillment/clients.py                               |       38 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/order\_fulfillment/serializers.py                           |       13 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/order\_fulfillment/tests/test\_clients.py                   |       34 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/order\_fulfillment/tests/test\_views.py                     |       64 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/order\_fulfillment/urls.py                                  |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/order\_fulfillment/views.py                                 |       32 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/\_\_init\_\_.py                                      |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/clients.py                                           |       19 |        8 |        2 |        0 |     52% |     40-65 |
| commerce\_coordinator/apps/paypal/pipeline.py                                          |       32 |        0 |        6 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/signals.py                                           |        2 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/tests/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/tests/test\_pipeline.py                              |       16 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/tests/test\_views.py                                 |       51 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/urls.py                                              |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/views.py                                             |       72 |        3 |       12 |        3 |     93% |45, 60-61, 107->112, 108->107 |
| commerce\_coordinator/apps/rollout/\_\_init\_\_.py                                     |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/rollout/pipeline.py                                         |       63 |        2 |       18 |        2 |     95% |   68, 127 |
| commerce\_coordinator/apps/rollout/tests/test\_pipeline.py                             |      119 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/rollout/tests/test\_util\_functions.py                      |       27 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/rollout/utils.py                                            |       28 |        3 |        8 |        0 |     86% |     80-82 |
| commerce\_coordinator/apps/rollout/waffle.py                                           |       14 |        1 |        0 |        0 |     93% |        29 |
| commerce\_coordinator/apps/stripe/\_\_init\_\_.py                                      |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/clients.py                                           |       99 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/constants.py                                         |       11 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/exceptions.py                                        |       29 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/filters.py                                           |        9 |        2 |        0 |        0 |     78% |     25-26 |
| commerce\_coordinator/apps/stripe/pipeline.py                                          |       54 |       21 |       10 |        2 |     58% |39-62, 92-105, 118-119, 172-173 |
| commerce\_coordinator/apps/stripe/signals.py                                           |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_clients.py                               |       78 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_pipeline.py                              |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_utils.py                                 |        9 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_views.py                                 |       66 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/urls.py                                              |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/utils.py                                             |        2 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/views.py                                             |       63 |       11 |       10 |        3 |     78% |65, 67, 112-145 |
| commerce\_coordinator/docker\_gunicorn\_configuration.py                               |       27 |       27 |       10 |        0 |      0% |      4-57 |
| commerce\_coordinator/urls.py                                                          |       24 |        0 |        0 |        0 |    100% |           |
|                                                                              **TOTAL** | **10094** |  **436** |  **752** |   **93** | **95%** |           |


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
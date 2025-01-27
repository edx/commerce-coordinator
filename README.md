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
| commerce\_coordinator/apps/commercetools/catalog\_info/constants.py                    |       40 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/catalog\_info/edx\_utils.py                   |       49 |        2 |       10 |        1 |     95% |    69, 92 |
| commerce\_coordinator/apps/commercetools/catalog\_info/foundational\_types.py          |       17 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/catalog\_info/utils.py                        |       69 |        0 |       30 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/clients.py                                    |      241 |        7 |       22 |        2 |     97% |339, 369-370, 512-513, 675-679 |
| commerce\_coordinator/apps/commercetools/constants.py                                  |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/data.py                                       |       42 |        0 |        8 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/filters.py                                    |        6 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/pipeline.py                                   |      129 |       16 |       20 |        3 |     86% |83-85, 127-129, 152, 178-181, 187-189, 339-340 |
| commerce\_coordinator/apps/commercetools/serializers.py                                |       95 |        0 |        2 |        1 |     99% |    21->23 |
| commerce\_coordinator/apps/commercetools/signals.py                                    |       22 |        2 |        2 |        0 |     92% |     62-65 |
| commerce\_coordinator/apps/commercetools/sub\_messages/\_\_init\_\_.py                 |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/sub\_messages/signals\_delayed.py             |       16 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/sub\_messages/signals\_dispatch.py            |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/sub\_messages/tasks.py                        |      112 |        1 |       16 |        2 |     98% |112, 281->329 |
| commerce\_coordinator/apps/commercetools/tasks.py                                      |       41 |       11 |        4 |        0 |     71% |    87-106 |
| commerce\_coordinator/apps/commercetools/tests/\_\_init\_\_.py                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/\_test\_cases.py                        |       25 |        0 |        2 |        1 |     96% |  36->exit |
| commerce\_coordinator/apps/commercetools/tests/catalog\_info/\_\_init\_\_.py           |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/catalog\_info/test\_edx\_utils.py       |       39 |        1 |        2 |        1 |     95% |        69 |
| commerce\_coordinator/apps/commercetools/tests/catalog\_info/test\_utils.py            |       90 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/conftest.py                             |      113 |        1 |        8 |        1 |     98% |       134 |
| commerce\_coordinator/apps/commercetools/tests/constants.py                            |       10 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/mocks.py                                |       45 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/sub\_messages/\_\_init\_\_.py           |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/sub\_messages/test\_signals\_delayed.py |       45 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/sub\_messages/test\_tasks.py            |      161 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_authentication.py                 |       25 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_clients.py                        |      419 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_data.py                           |       87 |        0 |        6 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_pipeline.py                       |      139 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_signals.py                        |       40 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_tasks.py                          |       58 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_utils.py                          |      156 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_views.py                          |      182 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/urls.py                                       |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/utils.py                                      |       89 |        0 |       20 |        1 |     99% |  80->exit |
| commerce\_coordinator/apps/commercetools/views.py                                      |       55 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools\_frontend/constants.py                        |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools\_frontend/pipeline.py                         |        9 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/core/\_\_init\_\_.py                                        |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/cache.py                                               |       47 |        0 |        2 |        0 |    100% |           |
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
| commerce\_coordinator/apps/core/tests/test\_cache.py                                   |       62 |        0 |        2 |        0 |    100% |           |
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
| commerce\_coordinator/apps/ecommerce/serializers.py                                    |       17 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/signals.py                                        |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/tests/\_\_init\_\_.py                             |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/tests/test\_clients.py                            |       21 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/tests/test\_views.py                              |       51 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/urls.py                                           |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/views.py                                          |       59 |       27 |       14 |        0 |     47% |45-69, 153-187 |
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
| commerce\_coordinator/apps/frontend\_app\_ecommerce/views.py                           |       51 |        0 |        8 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/\_\_init\_\_.py                      |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/constants.py                         |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/exceptions.py                        |        9 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/filters.py                           |       34 |        4 |        0 |        0 |     88% |     72-79 |
| commerce\_coordinator/apps/frontend\_app\_payment/models.py                            |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/pipeline.py                          |       10 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/serializers.py                       |       33 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/tests/\_\_init\_\_.py                |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/tests/test\_filters.py               |       77 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/tests/test\_views.py                 |      141 |       12 |        4 |        0 |     92% |66-69, 119-126 |
| commerce\_coordinator/apps/frontend\_app\_payment/urls.py                              |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/views.py                             |       93 |       48 |       16 |        0 |     41% |45-51, 58-71, 75-97, 112-121, 131-138 |
| commerce\_coordinator/apps/lms/\_\_init\_\_.py                                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/clients.py                                              |       38 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/filters.py                                              |       11 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/serializers.py                                          |       28 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/signal\_handlers.py                                     |        8 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/signals.py                                              |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tasks.py                                                |       46 |        0 |        6 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/constants.py                                      |        8 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_clients.py                                  |       33 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_signals.py                                  |       18 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_tasks.py                                    |       67 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_views.py                                    |      248 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/urls.py                                                 |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/views.py                                                |      149 |        1 |       14 |        0 |     99% |       369 |
| commerce\_coordinator/apps/paypal/\_\_init\_\_.py                                      |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/clients.py                                           |       19 |        9 |        2 |        0 |     48% | 17, 40-56 |
| commerce\_coordinator/apps/paypal/pipeline.py                                          |       33 |       10 |        6 |        1 |     67% |     67-86 |
| commerce\_coordinator/apps/paypal/signals.py                                           |        2 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/tests/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/tests/test\_pipeline.py                              |       16 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/tests/test\_views.py                                 |       51 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/urls.py                                              |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/paypal/views.py                                             |       72 |        3 |       12 |        3 |     93% |45, 60-61, 107->112, 108->107 |
| commerce\_coordinator/apps/rollout/\_\_init\_\_.py                                     |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/rollout/pipeline.py                                         |       48 |        1 |       12 |        1 |     97% |        96 |
| commerce\_coordinator/apps/rollout/tests/test\_util\_functions.py                      |       23 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/rollout/utils.py                                            |       24 |        3 |        8 |        0 |     84% |     48-50 |
| commerce\_coordinator/apps/rollout/waffle.py                                           |        5 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/\_\_init\_\_.py                                      |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/clients.py                                           |       99 |        0 |        4 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/constants.py                                         |       11 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/exceptions.py                                        |       33 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/filters.py                                           |        9 |        2 |        0 |        0 |     78% |     25-26 |
| commerce\_coordinator/apps/stripe/pipeline.py                                          |       85 |       16 |       14 |        3 |     77% |45-68, 94, 222-223, 272-273 |
| commerce\_coordinator/apps/stripe/signals.py                                           |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_clients.py                               |       78 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_pipeline.py                              |       68 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_utils.py                                 |       13 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_views.py                                 |       97 |        0 |        6 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/urls.py                                              |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/utils.py                                             |        6 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/views.py                                             |       63 |        0 |       10 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/\_\_init\_\_.py                                       |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/clients.py                                            |      101 |        0 |       38 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/exceptions.py                                         |       25 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/filters.py                                            |        9 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/pipeline.py                                           |      113 |        1 |       20 |        2 |     98% |48, 250->252 |
| commerce\_coordinator/apps/titan/serializers.py                                        |      163 |        0 |        8 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/signals.py                                            |       17 |        2 |        0 |        0 |     88% |     24-31 |
| commerce\_coordinator/apps/titan/tasks.py                                              |       44 |        3 |        4 |        1 |     92% |33-39, 109->exit |
| commerce\_coordinator/apps/titan/tests/\_\_init\_\_.py                                 |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/tests/constants.py                                    |        6 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/tests/test\_clients.py                                |      111 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/tests/test\_pipeline.py                               |      174 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/tests/test\_tasks.py                                  |       62 |        0 |        8 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/tests/test\_views.py                                  |       54 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/urls.py                                               |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/views.py                                              |       23 |        1 |        2 |        1 |     92% |        79 |
| commerce\_coordinator/docker\_gunicorn\_configuration.py                               |       27 |       27 |       10 |        0 |      0% |      4-57 |
| commerce\_coordinator/urls.py                                                          |       23 |        0 |        0 |        0 |    100% |           |
|                                                                              **TOTAL** | **7230** |  **270** |  **504** |   **33** | **95%** |           |


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
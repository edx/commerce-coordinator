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
| commerce\_coordinator/apps/commercetools/authentication.py                             |        6 |        0 |        2 |        1 |     88% |    33->32 |
| commerce\_coordinator/apps/commercetools/catalog\_info/constants.py                    |       23 |        3 |        0 |        0 |     87% |35, 38, 41 |
| commerce\_coordinator/apps/commercetools/catalog\_info/edx\_utils.py                   |       48 |        0 |       12 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/catalog\_info/foundational\_types.py          |       13 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/catalog\_info/utils.py                        |       65 |        0 |       32 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/clients.py                                    |      136 |        0 |       12 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/constants.py                                  |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/data.py                                       |       42 |        0 |        8 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/filters.py                                    |        6 |        0 |        2 |        1 |     88% |    13->12 |
| commerce\_coordinator/apps/commercetools/pipeline.py                                   |      112 |       17 |       18 |        3 |     85% |75-77, 126-128, 151, 171-174, 180-182, 238-239, 309 |
| commerce\_coordinator/apps/commercetools/serializers.py                                |       85 |        0 |        2 |        1 |     99% |    19->21 |
| commerce\_coordinator/apps/commercetools/signals.py                                    |       18 |        0 |        6 |        2 |     92% |19->18, 44->43 |
| commerce\_coordinator/apps/commercetools/sub\_messages/\_\_init\_\_.py                 |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/sub\_messages/signals\_delayed.py             |       16 |        0 |        6 |        3 |     86% |18->17, 29->28, 38->37 |
| commerce\_coordinator/apps/commercetools/sub\_messages/signals\_dispatch.py            |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/sub\_messages/tasks.py                        |       99 |        2 |       20 |        5 |     94% |43->42, 138->137, 185->184, 257->306, 264-266 |
| commerce\_coordinator/apps/commercetools/tasks.py                                      |       31 |        0 |        4 |        1 |     97% |    49->48 |
| commerce\_coordinator/apps/commercetools/tests/\_\_init\_\_.py                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/\_test\_cases.py                        |       25 |        0 |        4 |        1 |     97% |  36->exit |
| commerce\_coordinator/apps/commercetools/tests/catalog\_info/\_\_init\_\_.py           |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/catalog\_info/test\_edx\_utils.py       |       39 |        1 |        2 |        1 |     95% |        69 |
| commerce\_coordinator/apps/commercetools/tests/catalog\_info/test\_utils.py            |       76 |        0 |       52 |       22 |     83% |49->58, 57->49, 58->57, 62->71, 70->62, 71->70, 79->86, 85->79, 86->85, 98->137, 136->98, 137->136, 143->173, 172->143, 173->172, 178->184, 183->178, 184->183, 195->265, 264->195, 265->264, 267->exit |
| commerce\_coordinator/apps/commercetools/tests/conftest.py                             |      108 |        4 |       22 |        8 |     91% |39->38, 44->43, 54->53, 86, 89, 91, 131, 139->138, 156->exit, 210->exit, 216->exit |
| commerce\_coordinator/apps/commercetools/tests/constants.py                            |        9 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/mocks.py                                |       45 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/sub\_messages/\_\_init\_\_.py           |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/sub\_messages/test\_signals\_delayed.py |       45 |        0 |       15 |        6 |     90% |15->23, 22->15, 44->54, 52->44, 73->81, 80->73 |
| commerce\_coordinator/apps/commercetools/tests/sub\_messages/test\_tasks.py            |      152 |        0 |       48 |       22 |     89% |95->99, 97->95, 103->102, 112->111, 129->127, 144->148, 146->144, 152->151, 159->158, 175->173, 190->188, 205->203, 219->217, 258->257, 266->265, 270->272, 271->270, 272->271, 285->288, 286->285, 287->286, 288->287 |
| commerce\_coordinator/apps/commercetools/tests/test\_authentication.py                 |       25 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/tests/test\_clients.py                        |      263 |        0 |       62 |       29 |     91% |82->exit, 122->exit, 151->exit, 183->exit, 187->exit, 203->exit, 216->203, 239->exit, 291->exit, 333->exit, 364->exit, 371->364, 372->379, 406->exit, 436->exit, 443->436, 465->exit, 507->exit, 514->507, 515->522, 533->532, 551->exit, 570->569, 586->exit, 593->586, 611->613, 612->611, 613->612, 624->exit |
| commerce\_coordinator/apps/commercetools/tests/test\_data.py                           |       87 |        0 |       28 |       10 |     91% |71->109, 108->71, 109->108, 145->135, 160->196, 195->160, 196->195, 200->236, 235->200, 236->235 |
| commerce\_coordinator/apps/commercetools/tests/test\_pipeline.py                       |      110 |        0 |       36 |       18 |     88% |35->34, 92->95, 93->92, 94->93, 95->94, 111->113, 112->111, 113->112, 118->125, 130->133, 131->130, 132->131, 133->132, 150->153, 151->150, 152->151, 153->152, 192->188 |
| commerce\_coordinator/apps/commercetools/tests/test\_signals.py                        |       40 |        0 |       10 |        4 |     92% |16->24, 23->16, 53->61, 60->53 |
| commerce\_coordinator/apps/commercetools/tests/test\_tasks.py                          |       63 |        0 |       14 |        5 |     94% |40->39, 66->65, 93->92, 138->exit, 147->146 |
| commerce\_coordinator/apps/commercetools/tests/test\_utils.py                          |      162 |        0 |       65 |       32 |     86% |47->43, 57->54, 66->63, 78->84, 83->78, 84->83, 92->exit, 103->110, 108->103, 109->108, 110->109, 118->exit, 151->148, 177->174, 251->253, 252->251, 263->262, 269->268, 275->274, 290->296, 295->290, 296->295, 301->exit, 317->323, 322->317, 323->322, 328->exit, 344->351, 349->344, 350->349, 351->350, 357->exit |
| commerce\_coordinator/apps/commercetools/tests/test\_views.py                          |      182 |        0 |       77 |       37 |     86% |81->86, 89->93, 90->89, 175->179, 176->175, 205->213, 209->205, 213->209, 225->233, 229->225, 233->229, 252->260, 256->252, 260->256, 271->279, 275->271, 279->275, 291->299, 295->291, 299->295, 312->316, 313->312, 342->350, 346->342, 350->346, 362->370, 366->362, 370->366, 389->397, 393->389, 397->393, 408->416, 412->408, 416->412, 428->436, 432->428, 436->432 |
| commerce\_coordinator/apps/commercetools/urls.py                                       |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/utils.py                                      |       96 |        0 |       12 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools/views.py                                      |       52 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools\_frontend/constants.py                        |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/commercetools\_frontend/pipeline.py                         |        9 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/core/\_\_init\_\_.py                                        |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/cache.py                                               |       47 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/core/clients.py                                             |       39 |        0 |       10 |        3 |     94% |56->55, 115->114, 119->118 |
| commerce\_coordinator/apps/core/constants.py                                           |       49 |        4 |        0 |        0 |     92% |55, 65, 88, 95 |
| commerce\_coordinator/apps/core/context\_processors.py                                 |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/exceptions.py                                          |        2 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/memcache.py                                            |       28 |        0 |        6 |        0 |    100% |           |
| commerce\_coordinator/apps/core/middleware.py                                          |       25 |        0 |        8 |        3 |     91% |22->26, 27->30, 31->38 |
| commerce\_coordinator/apps/core/models.py                                              |       18 |        0 |        2 |        1 |     95% |    21->20 |
| commerce\_coordinator/apps/core/pipeline.py                                            |        6 |        6 |        0 |        0 |      0% |      5-23 |
| commerce\_coordinator/apps/core/segment.py                                             |        8 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/core/serializers.py                                         |       26 |        2 |        4 |        1 |     90% |     58-59 |
| commerce\_coordinator/apps/core/signal\_helpers.py                                     |       34 |        1 |        8 |        2 |     93% |21->20, 57 |
| commerce\_coordinator/apps/core/signals.py                                             |        5 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/\_\_init\_\_.py                                  |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_cache.py                                   |       62 |        0 |       18 |        7 |     91% |39->41, 44->46, 51->93, 92->51, 93->92, 103->105, 109->111 |
| commerce\_coordinator/apps/core/tests/test\_clients.py                                 |       11 |        0 |        8 |        3 |     84% |13->25, 24->13, 25->24 |
| commerce\_coordinator/apps/core/tests/test\_context\_processors.py                     |        8 |        0 |        2 |        1 |     90% |    14->13 |
| commerce\_coordinator/apps/core/tests/test\_memcache.py                                |       46 |        0 |       10 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_middleware.py                              |       47 |        0 |       14 |        7 |     89% |31->30, 40->48, 48->54, 61->60, 66->69, 76->75, 81->84 |
| commerce\_coordinator/apps/core/tests/test\_models.py                                  |       30 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/core/tests/test\_segment.py                                 |       20 |        0 |       14 |        7 |     79% |10->13, 11->10, 12->11, 13->12, 23->25, 24->23, 25->24 |
| commerce\_coordinator/apps/core/tests/test\_serializers.py                             |       27 |        0 |       20 |        9 |     81% |19->exit, 23->exit, 31->40, 39->31, 40->39, 45->51, 50->45, 51->50, 53->56 |
| commerce\_coordinator/apps/core/tests/test\_signal\_helpers.py                         |      107 |        0 |       28 |       10 |     93% |22->21, 28->27, 37->36, 81->exit, 83->exit, 88->exit, 117->exit, 128->exit, 140->exit, 223->exit |
| commerce\_coordinator/apps/core/tests/test\_tests\_utils.py                            |       18 |        0 |        8 |        4 |     85% |15->14, 28->27, 31->exit, 52->60 |
| commerce\_coordinator/apps/core/tests/test\_views.py                                   |       37 |        0 |        6 |        3 |     93% |25->exit, 49->48, 55->54 |
| commerce\_coordinator/apps/core/tests/utils.py                                         |      100 |       16 |       34 |        5 |     80% |78->83, 94->93, 222->221, 270, 273-274, 285-313 |
| commerce\_coordinator/apps/core/views.py                                               |       77 |        0 |       16 |        3 |     97% |24->23, 105->104, 128->127 |
| commerce\_coordinator/apps/demo\_lms/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/demo\_lms/filters.py                                        |       10 |        5 |        4 |        1 |     43% |21->20, 25-29 |
| commerce\_coordinator/apps/demo\_lms/models.py                                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/demo\_lms/pipeline.py                                       |        7 |        7 |        0 |        0 |      0% |      5-29 |
| commerce\_coordinator/apps/demo\_lms/signals.py                                        |       24 |        8 |       12 |        5 |     58% |21->20, 36->35, 41, 45->44, 51, 55->54, 61-63, 67->66, 72-74 |
| commerce\_coordinator/apps/demo\_lms/tasks.py                                          |       12 |        3 |        6 |        3 |     67% |12->11, 18, 22->21, 28, 32->31, 38 |
| commerce\_coordinator/apps/demo\_lms/tests.py                                          |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/demo\_lms/urls.py                                           |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/demo\_lms/views.py                                          |       18 |        9 |        0 |        0 |     50% |18-19, 34-36, 50-70, 78-79 |
| commerce\_coordinator/apps/ecommerce/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/clients.py                                        |       20 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/constants.py                                      |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/data.py                                           |      131 |        2 |       18 |        0 |     99% |  144, 146 |
| commerce\_coordinator/apps/ecommerce/models.py                                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/pipeline.py                                       |       21 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/serializers.py                                    |       17 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/signals.py                                        |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/tests/\_\_init\_\_.py                             |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/tests/test\_clients.py                            |       21 |        0 |        4 |        1 |     96% |  56->exit |
| commerce\_coordinator/apps/ecommerce/tests/test\_views.py                              |       51 |        0 |       14 |        4 |     94% |61->105, 103->61, 104->103, 105->104 |
| commerce\_coordinator/apps/ecommerce/urls.py                                           |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/ecommerce/views.py                                          |       59 |       27 |       14 |        0 |     47% |45-69, 153-187 |
| commerce\_coordinator/apps/enterprise\_learner/enterprise\_client.py                   |       19 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/enterprise\_learner/tests/test\_enterprise\_client.py       |       32 |        0 |       23 |       11 |     80% |14->18, 17->14, 23->70, 69->23, 70->69, 72->exit, 73->72, 95->101, 100->95, 101->100, 102->exit |
| commerce\_coordinator/apps/enterprise\_learner/tests/test\_utils.py                    |       25 |        0 |        4 |        2 |     93% |29->25, 40->36 |
| commerce\_coordinator/apps/enterprise\_learner/utils.py                                |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/\_\_init\_\_.py                    |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/filters.py                         |       15 |        0 |        4 |        2 |     89% |16->15, 38->37 |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/models.py                          |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/tests/\_\_init\_\_.py              |       14 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/tests/conftest.py                  |       17 |        0 |        4 |        2 |     90% |14->exit, 21->exit |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/tests/test\_filters.py             |       14 |        0 |        5 |        2 |     89% |21->27, 23->21 |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/tests/test\_views.py               |      120 |        0 |       33 |       14 |     91% |28->34, 30->28, 99->98, 174->176, 175->174, 176->175, 188->191, 189->188, 190->189, 191->190, 219->207, 226->228, 227->226, 228->227 |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/urls.py                            |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_ecommerce/views.py                           |       43 |        0 |       10 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/\_\_init\_\_.py                      |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/constants.py                         |        1 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/exceptions.py                        |        9 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/filters.py                           |       34 |        4 |        8 |        4 |     81% |21->20, 39->38, 66->65, 72-79, 90->89 |
| commerce\_coordinator/apps/frontend\_app\_payment/models.py                            |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/pipeline.py                          |       10 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/serializers.py                       |       33 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/tests/\_\_init\_\_.py                |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/tests/test\_filters.py               |       77 |        0 |       42 |       20 |     83% |23->42, 37->23, 38->37, 39->38, 40->39, 41->40, 42->41, 113->131, 127->113, 128->127, 129->128, 130->129, 131->130, 188->199, 198->188, 199->198, 219->236, 225->219, 235->225, 236->235 |
| commerce\_coordinator/apps/frontend\_app\_payment/tests/test\_views.py                 |      141 |       12 |       20 |        4 |     90% |66-69, 119-126, 232->266, 264->232, 265->264, 266->265 |
| commerce\_coordinator/apps/frontend\_app\_payment/urls.py                              |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/frontend\_app\_payment/views.py                             |       93 |       48 |       20 |        2 |     42% |41->40, 45-51, 54->53, 58-71, 75-97, 112-121, 131-138 |
| commerce\_coordinator/apps/lms/\_\_init\_\_.py                                         |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/clients.py                                              |       36 |        0 |        4 |        2 |     95% |21->20, 28->27 |
| commerce\_coordinator/apps/lms/filters.py                                              |        9 |        0 |        2 |        1 |     91% |    16->15 |
| commerce\_coordinator/apps/lms/serializers.py                                          |       23 |        0 |        2 |        1 |     96% |    47->46 |
| commerce\_coordinator/apps/lms/signal\_handlers.py                                     |        8 |        0 |        2 |        1 |     90% |    13->12 |
| commerce\_coordinator/apps/lms/signals.py                                              |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tasks.py                                                |       17 |        0 |        2 |        1 |     95% |    19->18 |
| commerce\_coordinator/apps/lms/tests/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/constants.py                                      |        7 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/tests/test\_clients.py                                  |       33 |        0 |       10 |        4 |     91% |52->50, 69->67, 71->78, 92->exit |
| commerce\_coordinator/apps/lms/tests/test\_signals.py                                  |       18 |        0 |        5 |        2 |     91% |14->22, 21->14 |
| commerce\_coordinator/apps/lms/tests/test\_tasks.py                                    |       34 |        0 |        4 |        1 |     97% |    32->31 |
| commerce\_coordinator/apps/lms/tests/test\_views.py                                    |      155 |        0 |       43 |       18 |     91% |26->28, 27->26, 73->75, 74->73, 75->74, 79->exit, 101->100, 108->110, 109->108, 110->109, 114->exit, 227->226, 236->235, 251->250, 259->258, 266->275, 274->266, 275->274 |
| commerce\_coordinator/apps/lms/urls.py                                                 |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/lms/views.py                                                |       96 |        0 |       16 |        2 |     98% |82->81, 127->126 |
| commerce\_coordinator/apps/rollout/\_\_init\_\_.py                                     |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/rollout/pipeline.py                                         |       48 |        1 |       12 |        1 |     97% |        96 |
| commerce\_coordinator/apps/rollout/tests/test\_util\_functions.py                      |       23 |        0 |       20 |        9 |     79% |17->26, 25->17, 26->25, 29->39, 38->29, 39->38, 47->51, 50->47, 51->50 |
| commerce\_coordinator/apps/rollout/utils.py                                            |       24 |        3 |       11 |        0 |     86% |     48-50 |
| commerce\_coordinator/apps/rollout/waffle.py                                           |        5 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/\_\_init\_\_.py                                      |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/clients.py                                           |       99 |        0 |        6 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/constants.py                                         |       11 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/exceptions.py                                        |       33 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/filters.py                                           |        9 |        2 |        2 |        1 |     73% |19->18, 25-26 |
| commerce\_coordinator/apps/stripe/pipeline.py                                          |       82 |       14 |       12 |        2 |     79% |44-67, 93, 269-270 |
| commerce\_coordinator/apps/stripe/signals.py                                           |        3 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/tests/test\_clients.py                               |       78 |        0 |       33 |       15 |     86% |27->29, 28->27, 89->exit, 131->exit, 161->213, 162->161, 212->162, 213->212, 226->exit, 261->exit, 325->exit, 394->exit, 461->exit, 483->exit, 518->exit |
| commerce\_coordinator/apps/stripe/tests/test\_pipeline.py                              |       68 |        0 |       16 |        8 |     90% |26->25, 56->exit, 63->62, 99->exit, 110->109, 131->exit, 138->137, 158->exit |
| commerce\_coordinator/apps/stripe/tests/test\_utils.py                                 |       13 |        0 |       14 |        6 |     78% |14->21, 20->14, 21->20, 27->32, 31->27, 32->31 |
| commerce\_coordinator/apps/stripe/tests/test\_views.py                                 |       97 |        0 |       42 |       18 |     87% |41->40, 49->48, 53->exit, 70->exit, 84->105, 102->84, 103->102, 104->103, 105->104, 138->exit, 150->138, 158->177, 172->158, 173->172, 174->173, 175->174, 176->175, 177->176 |
| commerce\_coordinator/apps/stripe/urls.py                                              |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/utils.py                                             |        6 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/stripe/views.py                                             |       63 |        0 |       16 |        1 |     99% |    46->45 |
| commerce\_coordinator/apps/titan/\_\_init\_\_.py                                       |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/clients.py                                            |      102 |        0 |       42 |        2 |     99% |26->25, 31->30 |
| commerce\_coordinator/apps/titan/exceptions.py                                         |       25 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/filters.py                                            |        9 |        0 |        2 |        1 |     91% |    19->18 |
| commerce\_coordinator/apps/titan/pipeline.py                                           |      113 |        1 |       20 |        2 |     98% |48, 250->252 |
| commerce\_coordinator/apps/titan/serializers.py                                        |      163 |        0 |        8 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/signals.py                                            |       17 |        2 |        6 |        3 |     78% |20->19, 24-31, 35->34, 49->48 |
| commerce\_coordinator/apps/titan/tasks.py                                              |       44 |        3 |       10 |        4 |     87% |22->21, 33-39, 43->42, 66->65, 109->exit |
| commerce\_coordinator/apps/titan/tests/\_\_init\_\_.py                                 |        0 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/tests/constants.py                                    |        6 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/tests/test\_clients.py                                |      111 |        0 |       19 |        8 |     94% |178->183, 182->178, 199->exit, 208->210, 209->208, 210->209, 356->363, 509->505 |
| commerce\_coordinator/apps/titan/tests/test\_pipeline.py                               |      174 |        0 |       70 |       31 |     87% |47->46, 89->88, 112->111, 122->127, 134->133, 144->149, 156->155, 168->173, 180->184, 183->180, 184->183, 208->286, 285->208, 286->285, 306->326, 324->306, 325->324, 326->325, 338->343, 358->356, 369->368, 374->379, 399->398, 420->419, 422->432, 458->457, 470->469, 473->478, 513->512, 525->524, 528->532 |
| commerce\_coordinator/apps/titan/tests/test\_tasks.py                                  |       62 |        0 |       34 |       12 |     88% |29->28, 57->62, 58->57, 59->58, 60->59, 61->60, 62->61, 122->125, 123->122, 124->123, 125->124, 143->159 |
| commerce\_coordinator/apps/titan/tests/test\_views.py                                  |       54 |        0 |        2 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/urls.py                                               |        4 |        0 |        0 |        0 |    100% |           |
| commerce\_coordinator/apps/titan/views.py                                              |       23 |        1 |        2 |        1 |     92% |        79 |
| commerce\_coordinator/docker\_gunicorn\_configuration.py                               |       27 |       27 |       10 |        0 |      0% |      4-57 |
| commerce\_coordinator/urls.py                                                          |       22 |        0 |        0 |        0 |    100% |           |
|                                                                              **TOTAL** | **6368** |  **235** | **1545** |  **516** | **90%** |           |


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
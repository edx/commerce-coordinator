from rest_framework.negotiation import BaseContentNegotiation


class IgnoreClientContentNegotiation(BaseContentNegotiation):
    """
    Ignores Content Negotiation to handle our specific call, selects the first format.

    A good example of why to use this can be found in `THES-236`, however, the basic reason is this:
    LMS just FORWARDS to CC via a browser, it doesn't set a body, nor does it customize headers, and thus we are not
    able to make it use the `Use-Jwt-Cookie` (edx_rest_framework_extensions.auth.jwt.constants.USE_JWT_COOKIE_HEADER)
    nor can we limit it from wanting an HTML resource.
    """

    def select_parser(self, request, parsers):
        """
        Select the first parser in the `.parser_classes` list.
        """
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix=None):
        """
        Select the first renderer in the `.renderer_classes` list.
        """
        return renderers[0], renderers[0].media_type


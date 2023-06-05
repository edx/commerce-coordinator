"""
Views for the frontend_app_payment app
"""

import logging

from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ActiveOrderRequested

logger = logging.getLogger(__name__)

class GetActiveOrderView(APIView):

    def get(self, request):
        """return the user's current active order"""

        # deny global queries
        if not request.user.username:
            raise PermissionDenied(detail="Could not detect username.")
        
        params = {'username': request.user.username}

        current_order = ActiveOrderRequested.run_filter(params)
        return Response(current_order)
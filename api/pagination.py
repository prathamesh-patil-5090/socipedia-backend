from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'posts': data,
            'pagination': {
                'currentPage': self.page.number,
                'totalPages': self.page.paginator.num_pages,
                'totalPosts': self.page.paginator.count,
                'hasNextPage': self.page.has_next(),
                'hasPrevPage': self.page.has_previous(),
                'limit': self.get_page_size(self.request),
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            }
        })


class PostsPagination(StandardResultsSetPagination):
    """Custom pagination class specifically for posts"""
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response({
            'posts': data,
            'pagination': {
                'currentPage': self.page.number,
                'totalPages': self.page.paginator.num_pages,
                'totalPosts': self.page.paginator.count,
                'hasNextPage': self.page.has_next(),
                'hasPrevPage': self.page.has_previous(),
                'limit': self.get_page_size(self.request),
            }
        })

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            'success': False,
            'error': {
                'code': response.status_code,
                'message': _get_error_message(response.data),
                'details': response.data
            }
        }
        response.data = error_data

    return response


def _get_error_message(data):
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        first_key = next(iter(data))
        val = data[first_key]
        if isinstance(val, list):
            return f"{first_key}: {val[0]}"
        return str(val)
    if isinstance(data, list):
        return str(data[0])
    return str(data)

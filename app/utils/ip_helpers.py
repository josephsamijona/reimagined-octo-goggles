def get_client_ip(request):
    """
    Retrieves the client IP address from the request.
    Handles standard headers and proxy headers (X-Forwarded-For).
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

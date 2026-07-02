class NoStoreForAuthenticatedAPIMiddleware:
    """
    Ensures any response for an authenticated request under /api/ is never
    cached by the browser or any intermediary (proxy/CDN). Prevents user A's
    session-scoped data (e.g. /api/users/me/, /api/expert-profiles/me/) from
    being replayed to user B via a shared cache.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/") and getattr(request, "user", None) and request.user.is_authenticated:
            response["Cache-Control"] = "no-store, private"
            response["Pragma"] = "no-cache"
        return response
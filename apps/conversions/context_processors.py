


def credit_quota(request):
    """
    Globally exposes authenticated credit data to all Django templates.
    """
    if request.user.is_authenticated:
        try:
            quota = request.user.conversion_quota
            return {
                'user_credits': "∞" if quota.is_unlimited else quota.remaining,
                'is_unlimited_credits': quota.is_unlimited
            }
        except Exception:
            return {
                'user_credits': 0,
                'is_unlimited_credits': False
            }
    return {
        'user_credits': 0,
        'is_unlimited_credits': False
    }
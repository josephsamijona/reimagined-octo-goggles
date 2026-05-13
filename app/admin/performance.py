class AdminPerformanceMixin:
    """Common queryset tuning for high-volume Django admin pages."""

    admin_select_related = ()
    admin_prefetch_related = ()
    admin_defer_changelist = ()
    list_per_page = 50
    show_full_result_count = False

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if self.admin_select_related:
            queryset = queryset.select_related(*self.admin_select_related)

        if self.admin_prefetch_related:
            queryset = queryset.prefetch_related(*self.admin_prefetch_related)

        if self.admin_defer_changelist and self._is_changelist_request(request):
            queryset = queryset.defer(*self.admin_defer_changelist)

        return queryset

    @staticmethod
    def _is_changelist_request(request):
        match = getattr(request, "resolver_match", None)
        url_name = getattr(match, "url_name", "") or ""
        return url_name.endswith("_changelist")

from apps.audit.models import WorkflowEvent


def record_event(actor, action, *, booking=None, job=None, **detail):
    """Write one audit row. Anonymous actions (public booking) are not recorded."""
    if actor is None or not getattr(actor, 'is_authenticated', False):
        return None
    return WorkflowEvent.objects.create(actor=actor, action=action, booking=booking, job=job,
                                        detail={k: str(v) for k, v in detail.items()})

"""
gunicorn configuration file, see https://docs.gunicorn.org/en/develop/configure.html for more info.
"""
import multiprocessing  # pylint: disable=unused-import
import os

preload_app = True
timeout = 300
bind = "0.0.0.0:8140"

workers = 2


# StatsD / DogStatsD configuration
# Gunicorn's statsd_host validator (validate_statsd_address) accepts a STRING:
#   "HOST:PORT"     -> Gunicorn parses into (host, port) tuple -> AF_INET UDP
#   "unix://PATH"   -> Gunicorn parses into a bare string path -> AF_UNIX SOCK_DGRAM
_dogstatsd_url = os.environ.get("DD_DOGSTATSD_URL", "").strip()

if _dogstatsd_url:
    if _dogstatsd_url.startswith(("unix://", "unixgram://")):
        # Normalize unixgram:// -> unix:// (Gunicorn's validator expects unix://)
        _socket_path = _dogstatsd_url.split("://", 1)[1]
        if _socket_path:  # guard against bare "unix://" with no path
            statsd_host = f"unix://{_socket_path}"
            statsd_prefix = "commerce-coordinator"
    else:
        # Strip udp:// if present; pass plain HOST:PORT string to Gunicorn
        _statsd_host = (
            _dogstatsd_url[len("udp://"):]
            if _dogstatsd_url.startswith("udp://")
            else _dogstatsd_url
        ).strip()

        if _statsd_host:
            statsd_host = _statsd_host
            statsd_prefix = "commerce-coordinator"


def pre_request(worker, req):
    """Log requests before they are processed."""
    worker.log.info(f"{req.method} {req.path}")


def close_all_caches():
    """
    Close the cache so newly forked workers cannot accidentally share the socket with the parent processes.

    This prevents a race condition in which one worker could get a cache response intended for another worker.
    """
    # We do this in a way that is safe for 1.4 and 1.8 while we still have some
    # 1.4 installations.
    from django.conf import settings  # lint-amnesty, pylint: disable=import-outside-toplevel
    from django.core import cache as django_cache  # lint-amnesty, pylint: disable=import-outside-toplevel
    if hasattr(django_cache, 'caches'):
        get_cache = django_cache.caches.__getitem__
    else:
        get_cache = django_cache.get_cache  # pylint: disable=no-member
    for cache_name in settings.CACHES:
        cache = get_cache(cache_name)
        if hasattr(cache, 'close'):
            cache.close()

    # The 1.4 global default cache object needs to be closed also: 1.4
    # doesn't ensure you get the same object when requesting the same
    # cache. The global default is a separate Python object from the cache
    # you get with get_cache("default"), so it will have its own connection
    # that needs to be closed.
    cache = django_cache.cache
    if hasattr(cache, 'close'):
        cache.close()


def post_fork(server, worker):  # pylint: disable=unused-argument
    """Close the cache so newly forked workers cannot accidentally share the socket with the parent processes."""
    close_all_caches()


def when_ready(server):  # pylint: disable=unused-argument
    """When running in debug mode, run Django's `check` to better match what `manage.py runserver` does."""
    from django.conf import settings  # lint-amnesty, pylint: disable=import-outside-toplevel
    from django.core.management import call_command  # lint-amnesty, pylint: disable=import-outside-toplevel
    if settings.DEBUG:
        call_command("check")

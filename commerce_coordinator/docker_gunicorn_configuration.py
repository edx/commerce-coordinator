"""
gunicorn configuration file, see https://docs.gunicorn.org/en/develop/configure.html for more info.
"""
import logging
import multiprocessing  # pylint: disable=unused-import
import os

# Use the specific gunicorn error logger
logger = logging.getLogger("gunicorn.error")

preload_app = True
timeout = 300
bind = "0.0.0.0:8140"

workers = 2


# StatsD / DogStatsD configuration
_dogstatsd_url = os.environ.get("DD_DOGSTATSD_URL", "").strip()
statsd_host = None

if _dogstatsd_url:
    # 1. Handle Unix Domain Sockets (requires 'unix:' or 'unixpack:' prefix for Gunicorn)
    if _dogstatsd_url.startswith("unix://"):
        path = _dogstatsd_url[len("unix://"):]
        if path:
            statsd_host = f"unix:{path}"

    elif _dogstatsd_url.startswith("unixpack://"):
        path = _dogstatsd_url[len("unixpack://"):]
        if path:
            statsd_host = f"unixpack:{path}"

    # 2. Handle UDP or standard HOST:PORT (Gunicorn expects plain "HOST:PORT")
    elif _dogstatsd_url.startswith("udp://"):
        statsd_host = _dogstatsd_url[len("udp://"):]

    else:
        statsd_host = _dogstatsd_url

    if statsd_host:
        statsd_prefix = "commerce-coordinator"

        # Log parsed statsd host on startup for verification using gunicorn.error logger
        logger.info("Configured statsd_host=%s", statsd_host)
    else:
        logger.info("DogStatsD URL provided but empty, skipping configuration.")


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

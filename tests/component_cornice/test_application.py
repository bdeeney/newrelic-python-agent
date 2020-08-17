import pytest

from testing_support.fixtures import (validate_transaction_errors,
        validate_transaction_metrics)

from newrelic.packages import six

def target_application():
    # We need to delay Pyramid application creation because of ordering
    # issues whereby the agent needs to be initialised before Pyramid is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as Pyramid relies on view handlers being
    # at global scope, so import it from a separate module.

    from _test_application import _test_application
    return _test_application

_test_cornice_service_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/pyramid.router:Router.__call__', 1),
        ('Function/_test_application:cornice_service_get_info', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:cornice_service_get_info',
        scoped_metrics=_test_cornice_service_scoped_metrics)
def test_cornice_service():
    application = target_application()
    application.get('/service')

_test_cornice_resource_collection_get_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/pyramid.router:Router.__call__', 1),
        ('Function/_test_application:Resource.collection_get', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:Resource.collection_get',
        scoped_metrics=_test_cornice_resource_collection_get_scoped_metrics)
def test_cornice_resource_collection_get():
    from utils import CORNICE_VERSION

    if CORNICE_VERSION < (0, 18):
        if six.PY3:
            _test_cornice_resource_collection_get_scoped_metrics.extend([
                ('Function/cornice.service:decorate_view.<locals>.wrapper', 1)])
        else:
            _test_cornice_resource_collection_get_scoped_metrics.extend([
                ('Function/cornice.service:wrapper', 1)])

    application = target_application()
    application.get('/resource')

_test_cornice_resource_get_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/pyramid.router:Router.__call__', 1),
        ('Function/_test_application:Resource.get', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:Resource.get',
        scoped_metrics=_test_cornice_resource_get_scoped_metrics)
def test_cornice_resource_get():
    from utils import CORNICE_VERSION

    if CORNICE_VERSION < (0, 18):
        if six.PY3:
            _test_cornice_resource_get_scoped_metrics.extend([
                ('Function/cornice.service:decorate_view.<locals>.wrapper', 1)])
        else:
            _test_cornice_resource_get_scoped_metrics.extend([
                ('Function/cornice.service:wrapper', 1)])

    application = target_application()
    application.get('/resource/1')

_test_cornice_error_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Function/pyramid.router:Router.__call__', 1),
        ('Function/cornice.pyramidhook:handle_exceptions', 1),
        ('Function/_test_application:cornice_error_get_info', 1)]

if six.PY3:
    _test_cornice_error_errors = ['builtins:RuntimeError']
else:
    _test_cornice_error_errors = ['exceptions:RuntimeError']

@validate_transaction_errors(errors=_test_cornice_error_errors)
@validate_transaction_metrics('cornice.pyramidhook:handle_exceptions',
        scoped_metrics=_test_cornice_error_scoped_metrics)
def test_cornice_error():
    application = target_application()
    with pytest.raises(RuntimeError):
        application.get('/error', status=500)
import sys
import webtest

from newrelic.agent import (callable_name, wsgi_application, record_exception,
        application)

from testing_support.fixtures import (validate_transaction_error_event,
        validate_non_transaction_error_event)

TRANS_URI = '/rad-page'
ERR_MESSAGE = 'Transaction had bad value'
ERROR = ValueError(ERR_MESSAGE)

@wsgi_application()
def exceptional_wsgi_application(environ, start_response):

    if 'err_message' in environ:
        err_message = environ['err_message']
    else:
        err_message = 'Generic error message'
    try:
        raise ValueError(err_message)
    except:
        start_response('500 :(',[])
        raise

exceptional_application = webtest.TestApp(exceptional_wsgi_application)

_intrinsic_attributes = {
    'type': 'TransactionError',
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
    'transactionName': 'WebTransaction/Uri'+TRANS_URI,
}

@validate_transaction_error_event(_intrinsic_attributes)
def test_transaction_error_event():
    try:
        response = exceptional_application.get(TRANS_URI,
            extra_environ={'err_message' : ERR_MESSAGE})
    except ValueError:
        pass

_intrinsic_attributes = {
    'type': 'TransactionError',
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
    'transactionName': None,
}

@validate_non_transaction_error_event(_intrinsic_attributes)
def test_error_event_outside_transaction():
    try:
        raise ERROR
    except ValueError:
        app = application()
        record_exception(*sys.exc_info(), application=app)

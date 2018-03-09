from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, override_application_settings)

def target_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as we will then get view handler
    # functions are different between Python 2 and 3, with the latter
    # showing <local> scope in path.

    from _test_compress import _test_application
    return _test_application

_test_application_index_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_compress:index_page', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_compress:index_page',
        scoped_metrics=_test_application_index_scoped_metrics)
def test_compress_middleware():
    application = target_application()
    response = application.get('/compress')
    response.mustcontain(500*'X')

_test_html_insertion_settings = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}

@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_flask_middleware():
    application = target_application()
    headers = { 'Accept-Encoding': 'gzip' }
    response = application.get('/html_insertion', headers=headers, status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain('NREUM HEADER', 'NREUM.info')


@override_application_settings(_test_html_insertion_settings)
def test_html_inserted_for_html_served_from_file():
    application = target_application()
    headers = { 'Accept-Encoding': 'gzip' }
    response = application.get('/html_served_from_file', headers=headers, status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain('NREUM HEADER', 'NREUM.info')


_test_html_insertion_manual_settings = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}

@override_application_settings(_test_html_insertion_manual_settings)
def test_html_insertion_manual_flask_middleware():
    application = target_application()
    response = application.get('/html_insertion_manual', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=['NREUM HEADER', 'NREUM.info'])

@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_unnamed_attachment_header_flask_middleware():
    application = target_application()
    response = application.get(
            '/html_insertion_unnamed_attachment_header', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=['NREUM HEADER', 'NREUM.info'])

@override_application_settings(_test_html_insertion_settings)
def test_html_insertion_named_attachment_header_flask_middleware():
    application = target_application()
    response = application.get(
            '/html_insertion_named_attachment_header', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=['NREUM HEADER', 'NREUM.info'])


@override_application_settings(_test_html_insertion_settings)
def test_text_served_from_file():
    application = target_application()
    response = application.get(
            '/text_served_from_file', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=['NREUM HEADER', 'NREUM.info'])


def test_empty_content_type():
    application = target_application()
    response = application.get('/empty_content_type')

    # Make sure agent doesn't blow up, if content type is ''

    assert response.headers['Content-Type'] == ''
    response.mustcontain('Empty Content Type Header')

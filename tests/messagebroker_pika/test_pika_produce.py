import pika
import pytest

from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import transient_function_wrapper
from newrelic.core.config import global_settings

from testing_support.fixtures import (validate_transaction_metrics,
        validate_tt_collector_json)
from testing_support.external_fixtures import validate_messagebroker_headers
from testing_support.settings import rabbitmq_settings


@transient_function_wrapper(pika.frame, 'Header.__init__')
def cache_pika_headers(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    ret = wrapped(*args, **kwargs)
    headers = instance.properties.headers
    transaction._test_request_headers = headers
    return ret


DB_SETTINGS = rabbitmq_settings()
QUEUE = 'cats-are-better-than-dogs'
CORRELATION_ID = 'meowmeowmeow'
REPLY_TO = 'purrrr'
HEADERS = {u'MYHEADER': u'headtail'}

_message_broker_tt_included_params = {
    'routing_key': QUEUE,
}

_message_broker_tt_forgone_params = [
    'queue_name', 'correlation_id', 'reply_to']

_test_blocking_connection_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/Default', 2),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Default', None),
]


@validate_transaction_metrics(
        'test_pika_produce:test_blocking_connection',
        scoped_metrics=_test_blocking_connection_metrics,
        rollup_metrics=_test_blocking_connection_metrics,
        background_task=True)
@validate_tt_collector_json(
        message_broker_params=_message_broker_tt_included_params,
        message_broker_forgone_params=_message_broker_tt_forgone_params)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_blocking_connection(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        channel.basic_publish(
            exchange='',
            routing_key=QUEUE,
            body='test',
        )

        channel.publish(
            exchange='',
            routing_key=QUEUE,
            body='test',
        )


_message_broker_tt_included_test_correlation_id = (
        _message_broker_tt_included_params.copy())
_message_broker_tt_included_test_correlation_id.update({
    'correlation_id': CORRELATION_ID,
})

_message_broker_tt_forgone_test_correlation_id = ['queue_name', 'reply_to',
        'headers']


@validate_transaction_metrics(
        'test_pika_produce:test_blocking_connection_correlation_id',
        scoped_metrics=_test_blocking_connection_metrics,
        rollup_metrics=_test_blocking_connection_metrics,
        background_task=True)
@validate_tt_collector_json(
        message_broker_params=_message_broker_tt_included_test_correlation_id,
        message_broker_forgone_params=(
            _message_broker_tt_forgone_test_correlation_id))
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_blocking_connection_correlation_id(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        channel.basic_publish(
            exchange='',
            routing_key=QUEUE,
            body='test',
            properties=pika.spec.BasicProperties(
                correlation_id=CORRELATION_ID),
        )

        channel.publish(
            exchange='',
            routing_key=QUEUE,
            body='test',
            properties=pika.spec.BasicProperties(
                correlation_id=CORRELATION_ID),
        )


_message_broker_tt_included_test_reply_to = (
        _message_broker_tt_included_params.copy())
_message_broker_tt_included_test_reply_to.update({
    'reply_to': REPLY_TO,
})

_message_broker_tt_forgone_test_reply_to = ['queue_name', 'correlation_id',
        'headers']


@validate_transaction_metrics(
        'test_pika_produce:test_blocking_connection_reply_to',
        scoped_metrics=_test_blocking_connection_metrics,
        rollup_metrics=_test_blocking_connection_metrics,
        background_task=True)
@validate_tt_collector_json(
        message_broker_params=_message_broker_tt_included_test_reply_to,
        message_broker_forgone_params=_message_broker_tt_forgone_test_reply_to)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_blocking_connection_reply_to(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()

        channel.basic_publish(
            exchange='',
            routing_key=QUEUE,
            body='test',
            properties=pika.spec.BasicProperties(reply_to=REPLY_TO),
        )

        channel.publish(
            exchange='',
            routing_key=QUEUE,
            body='test',
            properties=pika.spec.BasicProperties(reply_to=REPLY_TO),
        )


_message_broker_tt_included_test_headers = (
        _message_broker_tt_included_params.copy())
_message_broker_tt_included_test_headers.update({
    'headers': HEADERS.copy(),
})

_message_broker_tt_forgone_test_headers = [
    'queue_name', 'correlation_id', 'reply_to']


@validate_transaction_metrics(
        'test_pika_produce:test_blocking_connection_headers',
        scoped_metrics=_test_blocking_connection_metrics,
        rollup_metrics=_test_blocking_connection_metrics,
        background_task=True)
@validate_tt_collector_json(
        message_broker_params=_message_broker_tt_included_test_headers,
        message_broker_forgone_params=_message_broker_tt_forgone_test_headers)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
@pytest.mark.parametrize('enable_distributed_tracing', [True, False])
def test_blocking_connection_headers(enable_distributed_tracing):
    settings = global_settings()
    original_feature_flag = set(settings.feature_flag)

    if enable_distributed_tracing:
        settings.feature_flag = settings.feature_flag.add(
            'distributed_tracing')
    else:
        if 'distributed_tracing' in settings.feature_flag:
            settings.feature_flag.remove('distributed_tracing')

    try:
        with pika.BlockingConnection(
                pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
            channel = connection.channel()

            channel.basic_publish(
                exchange='',
                routing_key=QUEUE,
                body='test',
                properties=pika.spec.BasicProperties(headers=HEADERS),
            )

            channel.publish(
                exchange='',
                routing_key=QUEUE,
                body='test',
                properties=pika.spec.BasicProperties(headers=HEADERS),
            )

    finally:
        settings.feature_flag = original_feature_flag


@validate_transaction_metrics(
        'test_pika_produce:test_blocking_connection_headers_reuse_properties',
        scoped_metrics=_test_blocking_connection_metrics,
        rollup_metrics=_test_blocking_connection_metrics,
        background_task=True)
@validate_tt_collector_json(
        message_broker_params=_message_broker_tt_included_test_headers,
        message_broker_forgone_params=_message_broker_tt_forgone_test_headers)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_blocking_connection_headers_reuse_properties(producer):
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        properties = pika.spec.BasicProperties(headers=HEADERS)

        channel.basic_publish(
            exchange='',
            routing_key=QUEUE,
            body='test',
            properties=properties,
        )

        channel.publish(
            exchange='',
            routing_key=QUEUE,
            body='test',
            properties=properties,
        )


_test_blocking_connection_two_exchanges_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/exchange-1', 1),
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/exchange-2', 1),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/exchange-1', None),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/exchange-2', None),
]


@validate_transaction_metrics(
        'test_pika_produce:test_blocking_connection_two_exchanges',
        scoped_metrics=_test_blocking_connection_two_exchanges_metrics,
        rollup_metrics=_test_blocking_connection_two_exchanges_metrics,
        background_task=True)
@validate_tt_collector_json(
        message_broker_params=_message_broker_tt_included_params,
        message_broker_forgone_params=_message_broker_tt_forgone_params)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_blocking_connection_two_exchanges():
    with pika.BlockingConnection(
            pika.ConnectionParameters(DB_SETTINGS['host'])) as connection:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE)
        channel.exchange_declare(exchange='exchange-1', durable=False,
                auto_delete=True)
        channel.exchange_declare(exchange='exchange-2', durable=False,
                auto_delete=True)

        channel.basic_publish(
            exchange='exchange-1',
            routing_key=QUEUE,
            body='test',
        )
        channel.basic_publish(
            exchange='exchange-2',
            routing_key=QUEUE,
            body='test',
        )


_test_select_connection_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/Default', 1),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Default', None),
]


@validate_transaction_metrics(
        'test_pika_produce:test_select_connection',
        scoped_metrics=_test_select_connection_metrics,
        rollup_metrics=_test_select_connection_metrics,
        background_task=True)
@validate_tt_collector_json(
        message_broker_params=_message_broker_tt_included_params,
        message_broker_forgone_params=_message_broker_tt_forgone_params)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_select_connection():
    def on_open(connection):
        connection.channel(on_channel_open)

    def on_channel_open(channel):
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE,
            body='test',
        )
        connection.close()

    parameters = pika.ConnectionParameters(DB_SETTINGS['host'])
    connection = pika.SelectConnection(
            parameters=parameters,
            on_open_callback=on_open)

    try:
        connection.ioloop.start()
    except:
        connection.close()
        # Start the IOLoop again so Pika can communicate, it will stop on its
        # own when the connection is closed
        connection.ioloop.start()
        raise


_test_tornado_connection_metrics = [
    ('MessageBroker/RabbitMQ/Exchange/Produce/Named/Default', 1),
    ('MessageBroker/RabbitMQ/Exchange/Consume/Named/Default', None),
]


@validate_transaction_metrics(
        'test_pika_produce:test_tornado_connection',
        scoped_metrics=_test_tornado_connection_metrics,
        rollup_metrics=_test_tornado_connection_metrics,
        background_task=True)
@validate_tt_collector_json(
        message_broker_params=_message_broker_tt_included_params,
        message_broker_forgone_params=_message_broker_tt_forgone_params)
@background_task()
@validate_messagebroker_headers
@cache_pika_headers
def test_tornado_connection():
    def on_open(connection):
        connection.channel(on_channel_open)

    def on_channel_open(channel):
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE,
            body='test',
        )
        connection.close()
        connection.ioloop.stop()

    parameters = pika.ConnectionParameters(DB_SETTINGS['host'])
    connection = pika.TornadoConnection(
            parameters=parameters,
            on_open_callback=on_open)

    try:
        connection.ioloop.start()
    except:
        connection.close()
        # Start the IOLoop again so Pika can communicate, it will stop on its
        # own when the connection is closed
        connection.ioloop.start()
        raise

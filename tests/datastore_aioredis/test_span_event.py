# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import aioredis

from newrelic.api.transaction import current_transaction
from newrelic.api.background_task import background_task

from testing_support.db_settings import redis_settings
from conftest import event_loop, loop, AIOREDIS_VERSION
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.util import instance_hostname


DB_SETTINGS = redis_settings()[0]

_enable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": True,
    "datastore_tracer.database_name_reporting.enabled": True,
    "distributed_tracing.enabled": True,
    "span_events.enabled": True,
}
_disable_instance_settings = {
    "datastore_tracer.instance_reporting.enabled": False,
    "datastore_tracer.database_name_reporting.enabled": False,
    "distributed_tracing.enabled": True,
    "span_events.enabled": True,
}

if AIOREDIS_VERSION >= (2, 0):
    clients = [
        aioredis.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0),
        aioredis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0),
    ]
else:
    clients = [
        event_loop.run_until_complete(
            aioredis.create_redis("redis://%s:%d" % (DB_SETTINGS["host"], DB_SETTINGS["port"]), db=0)
        ),
    ]


async def _exercise_db(client):
    await client.set("key", "value")
    await client.get("key")

    if hasattr(client, "execute_command"):
        await client.execute_command("CLIENT", "LIST", parse="LIST")
    else:
        await client.execute("CLIENT", "LIST")


@pytest.mark.parametrize("client", clients)
@pytest.mark.parametrize("db_instance_enabled", (True, False))
@pytest.mark.parametrize("instance_enabled", (True, False))
def test_span_events(client, instance_enabled, db_instance_enabled, loop):
    guid = "dbb533c53b749e0b"
    priority = 0.5

    common = {
        "type": "Span",
        "transactionId": guid,
        "priority": priority,
        "sampled": True,
        "category": "datastore",
        "component": "Redis",
        "span.kind": "client",
    }
    exact_agents = {}

    if instance_enabled:
        settings = _enable_instance_settings.copy()
        hostname = instance_hostname(DB_SETTINGS["host"])
        exact_agents.update(
            {
                "peer.address": "%s:%s" % (hostname, DB_SETTINGS["port"]),
                "peer.hostname": hostname,
            }
        )
    else:
        settings = _disable_instance_settings.copy()
        exact_agents.update(
            {
                "peer.address": "Unknown:Unknown",
                "peer.hostname": "Unknown",
            }
        )

    if db_instance_enabled and instance_enabled:
        exact_agents.update(
            {
                "db.instance": "0",
            }
        )
        unexpected_agents = ()
    else:
        settings["attributes.exclude"] = ["db.instance"]
        unexpected_agents = ("db.instance",)

    query_1 = common.copy()
    query_1["name"] = "Datastore/operation/Redis/set"

    query_2 = common.copy()
    query_2["name"] = "Datastore/operation/Redis/get"

    query_3 = common.copy()
    query_3["name"] = "Datastore/operation/Redis/client_list"

    @validate_span_events(
        count=1,
        exact_intrinsics=query_1,
        unexpected_intrinsics=("db.instance"),
        exact_agents=exact_agents,
        unexpected_agents=unexpected_agents,
    )
    @validate_span_events(
        count=1,
        exact_intrinsics=query_2,
        unexpected_intrinsics=("db.instance"),
        exact_agents=exact_agents,
        unexpected_agents=unexpected_agents,
    )
    @validate_span_events(
        count=1,
        exact_intrinsics=query_3,
        unexpected_intrinsics=("db.instance"),
        exact_agents=exact_agents,
        unexpected_agents=unexpected_agents,
    )
    @override_application_settings(settings)
    @background_task(name="span_events")
    def _test():
        txn = current_transaction()
        txn.guid = guid
        txn._priority = priority
        txn._sampled = True
        loop.run_until_complete(_exercise_db(client))

    _test()

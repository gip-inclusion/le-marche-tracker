#!/usr/bin/env python3
import argparse
import json
import logging
import math
import os
import sys
import uuid
from datetime import datetime
from enum import Enum

import asyncpg
from mailjet_rest import Client
import pytz
import uvicorn
import yaml
from fastapi import Depends, FastAPI, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, IPvAnyAddress, Json, PositiveInt
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

sys.path.append(os.path.dirname(__file__))

"""
TODO:
- monitoring
"""
VERSION = 1
START_TIME = datetime.now(pytz.utc)
COUNTER = 0


# ######################################################### DATA SCHEMA / MODEL
# #############################################################################
class Actions(str, Enum):
    """
    Enumeration of available actions.
    This enforcement of a limited and predefined list of actions is optional.
    """
    load = 'load'
    scroll = 'scroll'
    click = 'click'
    inscription = 'inscription'
    listing_new = 'listing_new'
    quote_new = 'quote_new'
    metric_userlink = 'metric_userlink'
    directory_search = 'directory_search'
    directory_list = 'directory_list'
    directory_csv = 'directory_csv'
    adopt = 'adopt'
    adopt_search = 'adopt_search'
    misc = 'misc'


class ClientContext(BaseModel):
    referer: str = None
    user_agent: str = None


class ServerContext(BaseModel):
    client_ip: IPvAnyAddress = None
    reception_timestamp: datetime = Field(None, alias='_timestamp', description="Timestamp (UNIX Epoch)")
    origin: str = None
    user_agent: str = None


class TrackerModel(BaseModel):
    """
    Tracker Data Model
    """
    v: PositiveInt = Field(..., alias='_v', description="Version")
    timestamp: datetime = Field(..., description="Timestamp (UNIX Epoch)")
    order: int
    env: str = None

    session_id: uuid.UUID = Field(..., description="browser session UUID")
    page: str = None
    action: Actions = Field(..., description="Type d'action")
    meta: Json = None

    client_context: ClientContext
    server_context: ServerContext

    class Config:
        schema_extra = {
            'example': {
                "_v": 1,
                "timestamp": "2019-11-18T10:14:14.758899+00:00",
                "order": 10,
                "env": "development",
                "session_id": "77777777-6666-5555-4444-333333333333",
                "page": "test_page",
                "action": "load",
                "meta": "{}",
                "client_context": {
                    "referer": None,
                },
                "server_context": {
                    "user_agent": "DOES_NOT_EXIST",
                    "client_ip": None,
                    "reception_timestamp": None,
                    "referer": "http://example.com"
                }
            }
        }


# ################################################## SETUP AND ARGUMENT PARSING
# #############################################################################
logger = logging.getLogger(__name__)
logger.setLevel(logging.getLevelName('INFO'))
logger.addHandler(logging.StreamHandler())


config = {
    'postgresql': {
        'dsn': os.getenv('PG_DSN', 'postgres://user:pass@localhost:5432/db'),
        'min_size': 4,
        'max_size': 20
    },
    'server': {
        'host': os.getenv('HOST', 'localhost'),
        'port': int(os.getenv('PORT', '5000')),
        'log_level': os.getenv('LOG_LEVEL', 'info'),
    },
    'email': {
        'host': os.getenv('MAILJET_HOST', 'localhost'),
        'api_key': os.getenv('MAILJET_KEY', 'user'),
        'api_secret': os.getenv('MAILJET_SECRET', ''),
        'addr': os.getenv('NOTIF_MAIL', 'none@example.com'),
    },
    'log_level': os.getenv('LOG_LEVEL', 'info'),
    'proxy_prefix': os.getenv('PROXY_PREFIX', '/'),
}

if config['log_level'] == 'debug':
    logger.setLevel(logging.getLevelName('DEBUG'))

logger.debug('Debug activated')
logger.debug('Config values: \n%s', yaml.dump(config))

app = FastAPI(root_path=config['proxy_prefix'])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


DB_POOL = []


MSG_LIST = {
    'inscription': 'Inscription d\'un nouvel utilisateur',
    'listing_new': 'Publication nouvelle annonce',
    'quote_new': 'Nouvelle demande de devis',
    'metric_userlink': 'Nouvelle mise en relation',
}


# ####################################################################### UTILS
# #############################################################################
async def get_db():
    global DB_POOL  # pylint:disable=global-statement
    conn = await DB_POOL.acquire()
    try:
        yield conn
    finally:
        await DB_POOL.release(conn)


# XXX: Test only, can be removed
# async def coro_test():
#     while True:
#         await asyncio.sleep(5)
#         logger.warning('coro is still running !')


# ################################################ STARTUP AND BACKGROUND TASKS
# #############################################################################
@app.on_event("startup")
async def startup_event():
    # Async task example:
    # asyncio.create_task(coro_test())
    pass


def check_notifications(query):
    if query.action in MSG_LIST.keys():
        logger.info('Event of interest, notifying by mail')
        send_notification(query)


def send_notification(query):
    cfg = config['email']
    msg = {}
    msg['From'] = {'Name': 'BITOUBI Notifications', 'Email': '<noreply@inclusion.beta.gouv.fr>'}
    msg['To'] = [{'Name': 'Le Marché', 'Email': cfg['addr']}]

    logger.info('connecting')
    mailjet = Client(auth=(cfg['api_key'], cfg['api_secret']), version='v3.1')
    data = {
        'Messages': [
            {
                'From': msg['From'],
                'To': msg['To'],
                'Subject': f"C4 Notif: {MSG_LIST.get(query.action, 'action')} [{query.env}]",
                'TextPart': write_notification(query)
            }
        ]
    }
    result = mailjet.send.create(data=data)
    logger.info(result.status_code)
    logger.info(result.json())
    logger.info('Sent notification %s', data['Messages'][0]['Subject'])


def write_notification(query):
    data = query.meta
    message = MSG_LIST.get(query.action, '(erreur message type)')
    if query.action == 'inscription':
        link = linkto_user(data.get('id', 'error'), query)
        return f"Notification C4:\n\n{message}\n\n---\n{yaml.dump(data,indent=2)}\n---\n\n{link}"

    if query.action == 'listing_new':
        link = linkto_listing(data.get('id', 'error'), query)
        return f"Notification C4:\n\n{message}\n\n---\n{yaml.dump(data,indent=2)}\n---\n\n{link}"

    return f"Notification C4:\n\n{message}\n\n---\n{yaml.dump(data,indent=2)}"


def linkto_user(userid, query):
    if query.env == 'staging':
        return f"https://bitoubi-staging.cleverapps.io/admin/user/{userid}/edit"
    return f"https://lemarche.inclusion.beta.gouv.fr/admin/user/{userid}/edit"


def linkto_listing(listingid, query):
    if query.env == 'staging':
        return f"https://bitoubi-staging.cleverapps.io/admin/listing/{listingid}/edit"
    return f"https://lemarche.inclusion.beta.gouv.fr/admin/listing/{listingid}/edit"


# ############################################################### SERVER ROUTES
# #############################################################################
@app.on_event("startup")
async def startup_event():
    global DB_POOL  # pylint:disable=global-statement
    if os.getenv('NO_ASYNCPG', 'false') == 'false':
        DB_POOL = await asyncpg.create_pool(**config['postgresql'])


@app.get("/")
def root():
    """
    Query service status
    """
    now = datetime.now(pytz.utc)
    delta = now - START_TIME
    delta_s = math.floor(delta.total_seconds())
    return {
        'all_systems': 'nominal',
        'timestamp': now,
        'start_time': START_TIME,
        'uptime': f'{delta_s} seconds | {divmod(delta_s, 60)[0]} minutes | {divmod(delta_s, 86400)[0]} days',
        'api_version': VERSION,
        'api_counter': COUNTER,
    }


@app.post("/track")
async def tracking(query: TrackerModel, request: Request, background_tasks: BackgroundTasks, db=Depends(get_db)):
    """
    Tracking endpoint
    """
    sql = """
    INSERT INTO trackers (
        session_id,
        version,
        send_order,
        env,
        source,
        page,
        action,
        data,
        isadmin
    ) VALUES ($1, $2, $3, $4, 'tracker', $5, $6, $7, $8);
    """
    # Plan a background task
    background_tasks.add_task(check_notifications, query)

    # Enrich query data
    query.server_context.reception_timestamp = datetime.now()
    query.server_context.user_agent = request.headers.get('user-agent', 'not_defined')

    # Check if request has been forwared by proxy
    logger.debug('Available request headers: %s', ', '.join(request.headers.keys()))
    if 'X-Real-IP' in request.headers:
        query.server_context.client_ip = request.headers['X-Real-Ip']
    elif 'x-real-ip' in request.headers:
        query.server_context.client_ip = request.headers['x-real-ip']
    else:
        query.server_context.client_ip = request.client.host

    await db.execute(
        sql,
        query.session_id,
        query.v,
        query.order,
        query.env,
        query.page,
        query.action,
        json.dumps(jsonable_encoder(query)),
        query.meta.get('is_admin', False),
    )
    logger.debug('Wrote tracking log # %s from %s', query.order, query.session_id)


# ##################################################################### STARTUP
# #############################################################################
def main():
    parser = argparse.ArgumentParser(description='Matching server process')
    parser.add_argument('--config', dest='config', help='config file', default=None)
    parser.add_argument('--debug', dest='debug', action='store_true', default=False, help='Debug mode')
    args = parser.parse_args()
    if args.debug:
        logger.debug('Debug activated')
        config['log_level'] = 'debug'
        config['server']['log_level'] = 'debug'
        logger.debug('Arguments: %s', args)

    uvicorn.run(
        app,
        **config['server']
    )


if __name__ == "__main__":
    main()

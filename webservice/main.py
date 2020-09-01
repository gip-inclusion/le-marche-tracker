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
import pytz
import uvicorn
import yaml
from fastapi import Depends, FastAPI
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


class ClientContext(BaseModel):
    referer: str = None


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


# ####################################################################### UTILS
# #############################################################################
async def get_db():
    global DB_POOL  # pylint:disable=global-statement
    conn = await DB_POOL.acquire()
    try:
        yield conn
    finally:
        await DB_POOL.release(conn)


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
async def tracking(query: TrackerModel, request: Request, db=Depends(get_db)):
    """
    Tracking endpoint
    """
    sql = """
    INSERT INTO trackers (
        session_id,
        version,
        send_order,
        data
    ) VALUES ($1, $2, $3, $4);
    """
    query.server_context.reception_timestamp = datetime.now()
    query.server_context.user_agent = request.headers['user-agent']

    # Check if request has been forwared by proxy
    logger.debug('Available request headers: %s', ', '.join(request.headers.keys()))
    if 'X-Real-IP' in request.headers:
        query.server_context.client_ip = request.headers['X-Real-Ip']
    elif 'x-real-ip' in request.headers:
        query.server_context.client_ip = request.headers['x-real-ip']
    else:
        query.server_context.client_ip = request.client.host

    await db.execute(sql, query.session_id, query.v, query.order, json.dumps(jsonable_encoder(query)))
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

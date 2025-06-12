import logging

from .datetime import datetime_to_inboxdatetime

logger = logging.getLogger("uvicorn.error")
dt2idt = datetime_to_inboxdatetime

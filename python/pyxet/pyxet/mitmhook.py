import asyncio
import sys
import mitmproxy
from mitmproxy import options
from mitmproxy.tools import dump
from . import xtracelib
import json

class MitmHook:
    def __init__(self, xtrace):
        self.xtrace = xtrace

    def responseheaders(self, flow):
        if flow.request.host.endswith("amazonaws.com"):
            host = flow.request.host
            method = flow.request.method
            path = flow.request.path
            headers = "\"\""
            respheaders = "\"\""
            # we use json dumps to string escape
            if flow.request is not None:
                headers = json.dumps(str(bytes(flow.request.headers), encoding='utf-8'))
            if flow.response is not None:
                respheaders = json.dumps(str(bytes(flow.response.headers), encoding='utf-8'))
            self.xtrace.write_xlog(f'{{"op":"http", "method":"{method}", "host":"{host}", "path":"{path}","reqheaders":{headers}, "respheaders":{respheaders}}}')


# from https://stackoverflow.com/questions/68654077/is-there-a-way-to-start-mitmproxy-v-7-0-2-programmatically-in-the-background/68661172#68661172


async def start_proxy(port):
    opts = options.Options(listen_host="0.0.0.0", listen_port=port)

    m = dump.DumpMaster(
        opts,
        with_termlog=False,
        with_dumper=False,
    )
    m.addons.add(MitmHook(xtracelib))
    await m.run()
    return m 
    
    
    
def proxy_loop():
    asyncio.run(start_proxy(8080))


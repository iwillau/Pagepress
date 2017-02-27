import sys, os, logging, posixpath, urllib, textwrap
from logging.config import fileConfig
from argparse import ArgumentParser
from configparser import SafeConfigParser
from pagepress.generator import Generator
from http.server import HTTPServer, SimpleHTTPRequestHandler

log = logging.getLogger(__name__)

LOG_FORMAT = '[1;31m%(levelname)-5.6s [0m%(message)s'


''' The following are utilities for command line management
If this file becomes too big and is split up, these utilities
should be moved to their own module
'''

truthy = ('1', 'true', 't', 'y', 'yes', 'on')

def asbool(value):
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    value = str(value).strip().lower()
    return value in truthy


'''Simple Handler for PagePress to attempt to resolve a URL
and serve it via a built in browser.

This is not particularly configurable and should not be used
for anything but testing
'''
class PagepressHTTPHandler(SimpleHTTPRequestHandler):
    def do_GET(self, *args, **kwargs):
        self.generator.update()
        return SimpleHTTPRequestHandler.do_GET(self, *args, **kwargs)

    def translate_path(self, path):
        '''Translate a /-separated PATH to the local filename syntax.

        Ripped off from SimpleHTTPRequestHandler

        '''
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = os.path.join(self.generator.base, 'static')
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path
    

'''Utility function to serve a PagePress setup using the above HTTP Handler'''
def serve(generator):
    server_address = ('', 6554)

    PagepressHTTPHandler.generator = generator
    httpd = HTTPServer(server_address, PagepressHTTPHandler)

    sa = httpd.socket.getsockname()
    log.info("Serving HTTP on %s:%s" % (sa[0], sa[1]))
    httpd.serve_forever()


'''Process the PagePress CLI arguments and merge them with
a config file (is one is given).
'''
def process_argv(argv, config):
    usage = '''PagePress is a website and static content generator.
    
            This utility will generate a PagePress website into a 
            directory which you can then upload (or via some other automated
            means) to a webserver.
            
            Alternatively you can run a simple webserver that will
            auto-generate content as you view it for development purposes.'''
    parser = ArgumentParser(
        prog='pagepress',
        description=textwrap.dedent(usage),
        usage='pagepress [options] [generate or serve]',
        )
    parser.add_argument(
        '-d', '--debug',
        action='count',
        default=0,
        help="Increase PagePress's own debugging. Use multiple times to keep " \
             "increasing the level of debugging."
        )
    parser.add_argument(
        '--source', '-s',
        action='store',
        default=config.pop('source', 'source'),
        help="The directory containing the source for the website.",
        )
    parser.add_argument(
        '--layout', '-l',
        action='store',
        default=config.pop('layout', 'layout'),
        help="The directory containing the layout/templates for the website.",
        )
    parser.add_argument(
        '--output', '-o',
        action='store',
        default=config.pop('output', 'html'),
        help="The output directory.",
        )
    parser.add_argument(
        'command',
        nargs=1,
        action='store',
        choices=['generate', 'serve'],
        help='The command you wish to run.',
    )
    config.update(vars(parser.parse_args(argv)))
    return config


def command(argv=sys.argv[1:]):
    # Config Files in order of priority
    config_files = [
        'pagepress.ini',
        'source/config.ini',
        'source/pagepress.ini',
        'pagepress/config.ini',
    ]
    bools = ['colour', 'dryrun', 'fail_fast', 
             'no_logs', 'no_stdout', 'backtrace']
    lists = ['locations']
    config = {}

    file_parser = SafeConfigParser()
    file_parser.read(config_files)
    if file_parser.has_section('pagepress'):
        # Tidy up values and keys
        for key, value in file_parser.items('pagepress'):
            key = key.strip().replace('-', '_').replace(' ', '_')
            if key in bools:
                value = asbool(value)
            if key in lists:
                value = value.strip().splitlines()
            config[key] = value
    
    config = process_argv(argv, config)

    # PagePress Logging
    # TODO: Let this be configured via ini file
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger = logging.getLogger('pagepress')
    logger.addHandler(handler)
    logger.propagate = False
    if config['debug'] > 3:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel((4 - config['debug']) * 10)

    g = Generator(config)
 
    if command == 'generate':
        g.update()
    else:
        serve(g)



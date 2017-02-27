import sys, os, logging, posixpath, urllib, textwrap
from logging.config import fileConfig
from argparse import ArgumentParser
from configparser import SafeConfigParser
# from pagepress.generator import Generator
from http.server import HTTPServer, SimpleHTTPRequestHandler

log = logging.getLogger(__name__)

LOG_FORMAT = '[1;31m%(levelname)-5.6s [0m%(message)s'


""" The following are utilities for command line management
If this file becomes too big and is split up, these utilities
should be moved to their own module
"""

truthy = ('1', 'true', 't', 'y', 'yes', 'on')

def asbool(value):
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    value = str(value).strip().lower()
    return value in truthy


"""Simple Handler for PagePress to attempt to resolve a URL
and serve it via a built in browser.

This is not particularly configurable and should not be used
for anything but testing
"""
class PagepressHTTPHandler(SimpleHTTPRequestHandler):
    def do_GET(self, *args, **kwargs):
        self.generator.update()
        return SimpleHTTPRequestHandler.do_GET(self, *args, **kwargs)

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Ripped off from SimpleHTTPRequestHandler

        """
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
    

"""Utility function to serve a PagePress setup using the above HTTP Handler"""
def serve(generator):
    server_address = ('', 6554)

    PagepressHTTPHandler.generator = generator
    httpd = HTTPServer(server_address, PagepressHTTPHandler)

    sa = httpd.socket.getsockname()
    log.info("Serving HTTP on %s:%s" % (sa[0], sa[1]))
    httpd.serve_forever()


"""Process the PagePress CLI arguments and merge them with
a config file (is one is given).
"""
def process_argv(argv, config):
    usage = '''Runs all Specs that it has been configured to find. '''
    parser = ArgumentParser(
        prog='pagepress',
        description=textwrap.dedent(usage),
        usage='pagepress [options] [files or directories]',
        )
    parser.add_argument(
        '-d', '--debug',
        action='count',
        default=0,
        help="Increase PagePress's own debugging. Use multiple times to keep " \
             "increasing the level of debugging."
        )
    format = parser.add_mutually_exclusive_group()
    format.add_argument(
        '--format',
        action='store',
        choices=['progress', 'detailed'],
        default=config.pop('format', 'progress'),
        help="Format the output as detailed or progress.",
        )
    format.add_argument(
        '-f',
        action='store',
        choices={'p': 'progress', 'd': 'detailed'},
        default='p',
        help="Synonym for --format",
        dest='format',
        )
    parser.add_argument(
        '-o', '--order',
        action='store',
        choices=['defined', 'random'],
        default=config.pop('order', 'random'),
        help='Run the tests in random order, or the order in which they ' \
             'were defined.',
    )
    parser.add_argument(
        '-ff', '--fail-fast',
        action='store_true',
        default=config.pop('fail_fast', False),
        help='Exit the run as soon as a test has failed',
    )
    colour = parser.add_mutually_exclusive_group()
    colour.add_argument(
        '-c', '--colour', '--color',
        action='store_true',
        help='format output in colour',
        default=config.pop('colour', True),
    )
    colour.add_argument(
        '-nc', '--no-colour', '--no-color',
        action='store_false',
        help="don't format output in colour",
        dest='colour',
    )
    parser.add_argument(
        '-s', '--no-stdout', '--no-stderr',
        action='store_true',
        default=config.pop('no_stdout', False),
        help="Don't capture stdout or stderr",
    )
    parser.add_argument(
        '-l', '--no-logs',
        action='store_true',
        default=config.pop('no_logs', False),
        help="Don't capture logs",
    )
    parser.add_argument(
        '--dryrun', '--dry-run',
        action='store_true',
        default=config.pop('dryrun', False),
        help="Don't run any tests, simply collect them and output as if " \
             "they had been run",
    )
    parser.add_argument(
        '-b', '--backtrace', '--full-backtrace',
        action='store_true',
        default=config.pop('backtrace', False),
        help="Show the full backtrace to exceptions, without filtering " \
             "PagePress internals",
    )
    parser.add_argument(
        'locations',
        nargs='*',
        default=config.pop('locations', ['spec']),
        help='The files or directories to search for tests.',
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
    if config['format'] == 'd':
        config['format'] = 'detailed'

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

    print("Generate OR Serve!!")


# def command():
#     if len(sys.argv) != 3:
#         print 'Invalid arguments'
#         print usage
#         sys.exit(1)
# 
#     command = sys.argv[1]
#     config_file = sys.argv[2]
#     if not os.path.isfile(config_file):
#         print 'Invalid Config File'
#         print usage
#         sys.exit(1)
# 
#     config_file = os.path.abspath(config_file)
#     parser = SafeConfigParser({'source': 'source',
# 			       'static': 'static',
# 			       'data': 'data',
# 				})
#     parser.read([config_file])
#     fileConfig([config_file]) # TODO: This should check for loggin config
#                               #       and if not present set to sane defaults
#     if not parser.has_option('pagepress:main', 'base'):
#         parser.set('pagepress:main', 'base', os.path.dirname(config_file))
# 
#     g = Generator(parser)
# 
#     if command == 'generate':
#         g.update()
#     elif command == 'serve':
#         serve(g)
#     else:
#         print 'Invalid Command'
#         print usage
#         sys.exit(1)

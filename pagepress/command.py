
import sys, os, logging, posixpath, urllib
from logging.config import fileConfig
from ConfigParser import SafeConfigParser
from pagepress.generator import Generator
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler

usage = '''
Usage:
    pagepress generate INI_FILE
    pagepress serve INI_FILE
    '''
log = logging.getLogger(__name__)

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
        path = os.path.join(self.pagepress_base, 'static')
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path
    

def serve(generator):
    server_address = ('', 6554)

    PagepressHTTPHandler.generator = generator
    httpd = HTTPServer(server_address, PagepressHTTPHandler)

    sa = httpd.socket.getsockname()
    log.info("Serving HTTP on %s:%s" % (sa[0], sa[1]))
    httpd.serve_forever()

def command():
    if len(sys.argv) != 3:
        print 'Invalid arguments'
        print usage
        sys.exit(1)

    command = sys.argv[1]
    config_file = sys.argv[2]
    if not os.path.isfile(config_file):
        print 'Invalid Config File'
        print usage
        sys.exit(1)

    config_file = os.path.abspath(config_file)
    parser = SafeConfigParser()
    parser.read([config_file])
    fileConfig([config_file]) # TODO: This should check for loggin config
                              #       and if not present set to sane defaults
    if not parser.has_option('pagepress:main', 'base'):
        parser.set('pagepress:main', 'base', os.path.dirname(config_file))

    g = Generator(parser)

    if command == 'generate':
        g.update()
    elif command == 'serve':
        serve(g)
    else:
        print 'Invalid Command'
        print usage
        sys.exit(1)


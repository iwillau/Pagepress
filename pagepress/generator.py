
import logging, os, errno
from datetime import datetime
from pagepress.page import Page, Blog, HTML, Templated
from pagepress.parsers import Markdown
from mako.lookup import TemplateLookup

log = logging.getLogger(__name__)

def list_files(base, path=[]):
    '''This function can be made much quicker
    by performing a lstat on each loop, and interpeting 
    all of the results. 

    In the Current Version, each file gets stat'd three times. (dirs only once
    though)
    '''
    base_path = os.path.join(base, *path)
    for entry in os.listdir(base_path):
        full_path = os.path.join(base_path, entry)
        if os.path.isdir(full_path) and entry[0:1] != '.':
            sub_path = path[:] 
            sub_path.append(entry)
            for s in list_files(base, sub_path):
                yield s
        elif os.path.isfile(full_path):
            file_path = path[:]
            file_path.append(entry)
            yield {
                'path': file_path,
                'mtime': datetime.fromtimestamp(os.path.getmtime(full_path)),
                'extension': os.path.splitext(full_path)[1],
            }

class Generator:
    def __init__(self, base):
        self.base = base
        self.source = os.path.join(base,'source')
        self.static = os.path.join(base,'static')
        self.data = os.path.join(base,'data')

        self.parsers = {
            '.md': Markdown(),
        }

        self.types = {
            'page': Page,
            'templated': Templated,
            'html': HTML,
            'blog': Blog,
        }

        self.templates = TemplateLookup(directories=[os.path.join(base, 'source')], 
                                        input_encoding='utf-8',
                                        output_encoding='utf-8',
                                        module_directory=self.data
                                       )

    def update(self):
        '''
        Firstly we loop through the source, and look for an mtime greater than
        the last generation. If we find one, then we generate.

        If we are newer, and have to generate, we make a couple of passes
        1. Generate the Page Object for each file
        2. Let them parse their own contents
        3. Pass them to the templater
        '''
        generated_file = os.path.join(self.static, 'generated.txt')
        try:
            fp = open(generated_file,'r')
            gen_string = fp.readline()
            fp.close()
            generated = datetime.strptime(gen_string, '%d/%m/%Y %H:%M:%S')
        except Exception, e:
            generated = datetime(1900,1,1)

        log.debug('Checking source for updated files')
        pages = list_files(self.source)
        # We check the mtimes here, to try and keep the check as 
        # 'light' as possible
        generate_time = None
        newer = False
        page_defs = []
        for page in pages:
            page_defs.append(page)
            if page['mtime'] > generated:
                newer = True

        if newer:
            generate_time = self.generate_all(page_defs)
            fp = open(generated_file,'w')
            fp.write(generate_time.strftime('%d/%m/%Y %H:%M:%S'));
            fp.close()

    def generate_all(self, pages):
        generating_time = datetime.now()
        log.info('Generating Site as of %s.' % generating_time)
        self.pages = []
        for page in pages:
            if page['extension'] in self.parsers:
                fp = open(os.path.join(self.source, *page['path']))
                try:
                    pagetype, metadata, content = self.parsers[page['extension']].parse(fp)
                    metadata.update(page)
                    self.pages.append(self.types[pagetype](
                                                generator=self,
                                                content=content,
                                                **metadata))
                except Exception, e:
                    log.error('Could not parse file: %s (%s)' %
                              ('/'.join(page['path']), e))

        for page in self.pages:
            try:
                rendered_file = os.path.join(self.static, *page.path)
                log.debug('Generating File: %s' % rendered_file)
                try:
                    rfp = open(rendered_file, 'w')
                except IOError, e:
                    if e.errno == errno.ENOENT:
                        directory = os.path.dirname(rendered_file)
                        os.makedirs(directory)
                        rfp = open(rendered_file, 'w')
                rfp.write(page.render())
                rfp.close()
            except Exception, e:
                log.error('Error rendering page %s (%s)' % 
                              ('/'.join(page.path), e))

        return generating_time


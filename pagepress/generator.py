
import logging, os, errno, gzip, shutil, codecs
from datetime import datetime
from pagepress.page import ( File, Page, Blog, HTML, Templated, Stylesheet,
                            Javascript)
from pagepress.parsers import Markdown, CSS, JS
from mako.lookup import TemplateLookup
from pagepress.convertors import asbool

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
    def __init__(self, config):
        self.base = config.get('pagepress:main', 'base')
        self.source = os.path.join(self.base,'source')
        self.web_path = os.path.join(self.base,'static')
        self.data = os.path.join(self.base,'data')

        self.static_resources = []
        self.current_path = []

        self.parsers = {
            '.md': Markdown(self),
            '.css': CSS(self),
            '.js': JS(self),
        }

        self.types = {
            'page': Page,
            'templated': Templated,
            'html': HTML,
            'blog': Blog,
            'stylesheet': Stylesheet,
            'javascript':Javascript,
        }

        template_debugging = asbool(config.get('pagepress:main', 'template_debugging'))
        self.stop_on_error = asbool(config.get('pagepress:main', 'stop_on_error'))
        self.templates = TemplateLookup(directories=[os.path.join(self.base, 'source')], 
                                        input_encoding='utf-8',
                                        output_encoding='utf-8',
                                        module_directory=self.data,
                                        format_exceptions=template_debugging,
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
        generated_file = os.path.join(self.web_path, 'generated.txt')
        try:
            fp = open(generated_file, "r")
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
            self.copy_static()
            fp = open(generated_file,'w')
            fp.write(generate_time.strftime('%d/%m/%Y %H:%M:%S'));
            fp.close()

    def generate_all(self, pages):
        generating_time = datetime.now()
        log.info('Generating Site as of %s.' % generating_time)
        self.pages = []
        for page in pages:
            if page['extension'] in self.parsers:
                filename = os.path.join(self.source, *page['path'])
                fp = codecs.open(filename, mode="r", encoding='utf-8')
                self.current_path = page['path'][:-1]
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
                    if self.stop_on_error:
                        raise
            # else:
            #     fp = open(os.path.join(self.source, *page['path']))
            #     content = fp.read()
            #     self.pages.append(File(generator=self, content=content, **page))

        for page in self.pages:
            try:
                rendered_file = os.path.join(self.web_path, *page.path)
                log.debug('Generating File: %s' % rendered_file)
                try:
                    rfp = open(rendered_file, 'w')
                except IOError, e:
                    if e.errno == errno.ENOENT:
                        directory = os.path.dirname(rendered_file)
                        os.makedirs(directory)
                        rfp = open(rendered_file, 'w')
                    else:
                        raise e
                page_content = page.render()
                rfp.write(page_content)
                rfp.close()
                if not rendered_file.endswith('.gz'):
                    rfp = gzip.open(rendered_file+'.gz', 'w')
                    rfp.write(page_content)
                    rfp.close()
            except Exception, e:
                log.error('Error rendering page %s (%s) Turn on template'
                          ' debugging to assist.' % 
                              ('/'.join(page.path), e))
                if self.stop_on_error:
                    raise

        return generating_time

    def static(self, path):
        if not path.startswith('/'):
            if len(self.current_path):
                path = os.path.join(os.path.join(*self.current_path), path)
            path = '/'+path
        if path not in self.static_resources:
            self.static_resources.append(path)
        return path

    def copy_static(self):
        log.debug('Copying Static resources')
        for sr in self.static_resources:
            log.debug('copying static %s' % sr)
            if sr.startswith('/'):
                sr = sr[1:]
            try:
                shutil.copy(os.path.join(self.source, sr), 
                            os.path.join(self.web_path, sr))
            except IOError, e:
                if e.errno == errno.ENOENT:
                    directory = os.path.dirname(os.path.join(self.web_path, sr))
                    os.makedirs(directory)
                    shutil.copy(os.path.join(self.source, sr), 
                                os.path.join(self.web_path, sr))
                else:
                    raise

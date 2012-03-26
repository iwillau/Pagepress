
import logging
from markdown import Markdown as MarkdownParser
from markdown_image import ImageExtension

log = logging.getLogger(__name__)

class Parser:
    default_page = 'page'
    def __init__(self, generator):
        self.generator = generator

    def read_intercept_head(self, meta, fp):
        for line in fp:
            try:
                name, value = line.split(':')
                meta[name.lower()] = value.strip()
            except Exception, e:
                yield line
                break
        for line in fp:
            yield line

    def parse(self, fp):
        meta = {}
        content = ''.join([l for l in self.read_intercept_head(meta, fp)])
        pagetype = meta.pop('type', self.default_page) 
        return pagetype, meta, content

class Markdown(Parser):
    def __init__(self, generator):
        self.generator = generator
        self.markdown = MarkdownParser(
                            output_format='html5',
                            extensions = ['tables',
                                          ImageExtension()],
                        )
    def parse(self, fp):
        meta = {}
        
        content = self.markdown.convert(''.join(self.read_intercept_head(meta, fp)))
        for href, title in self.markdown.references.itervalues():
            if ':' not in href:
                self.generator.static(href)
        self.markdown.reset()
        pagetype = meta.pop('type', 'templated') # Default Pagetype
        return pagetype, meta, content

class CSS(Parser):
    default_page = 'stylesheet'

class JS(Parser):
    default_page = 'javascript'



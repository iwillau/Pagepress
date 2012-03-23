
import logging
from markdown import Markdown as MarkdownParser

log = logging.getLogger(__name__)

class Markdown:
    def __init__(self):
        self.markdown = MarkdownParser(
                            output_format='html5',
                            extensions = ['tables'],
                        )
    def parse(self, fp):
        meta = {}
        def read_file():
            in_head = True
            for line in fp:
                if not in_head:
                    yield line
                else:
                    if len(line) < 2:
                        in_head = False
                        yield line
                    else:
                        name, value = line.split(':')
                        meta[name.lower()] = value.strip()

        
        content = self.markdown.convert(''.join(read_file()))
        self.markdown.reset()
        pagetype = meta.pop('type', 'templated') # Default Pagetype
        return pagetype, meta, content


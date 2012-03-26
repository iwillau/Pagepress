
import re
import markdown
from markdown.util import etree


class ImageBlockProcessor(markdown.blockprocessors.BlockProcessor):
    """ Process Image Blocks. """

    def test(self, parent, block):
        if block.startswith('&&&'):
            return True
        return False

    def run(self, parent, blocks):
        block = blocks.pop(0)
        try:
            header, block = block.split('\n', 1)
        except ValueError, e:
            header = block.strip()
            block = ''

        self.parser.state.set('imageblock')
        ib = etree.SubElement(parent, 'div')
        ib.attrib['class'] = 'img '+header[3:]
        self.parser.parseBlocks(ib, [self.looseDetab(block)])
        self.parser.state.reset()

IMAGE_PATTERN = '\&\[(.+?)\]\[(.+?)\](\[(.+?)\])?'
class ImagePattern(markdown.inlinepatterns.Pattern):
    """ Process Links with a & 
    
    This ImagePattern references 2 images to create a clickthrough
    to the larger one, with an optional group.

    If neither Image is referenced, then it is omitted.

    """

    def handleMatch(self, m):
        id_1 = m.group(2)
        id_2 = m.group(3)
        if not id_1 in self.markdown.references: 
            return None
        if not id_2 in self.markdown.references: 
            return None
        href_1, title_1 = self.markdown.references[id_1]
        href_2, title_2 = self.markdown.references[id_2]
        
        a = etree.Element('a')
        img = etree.SubElement(a, 'img')
        a.attrib['href'] = href_2
        a.attrib['title'] = title_2
        img.attrib['src'] = href_1
        img.attrib['alt'] = title_1
        if m.group(5) is not None:
            a.attrib['data-fancybox-group'] = m.group(5)
        return a

class ImageExtension(markdown.Extension):
    """ Add Image Blocks to Markdown. """

    def extendMarkdown(self, md, md_globals):
        md.parser.blockprocessors.add('imageblock', 
                                      ImageBlockProcessor(md.parser),
                                     '<paragraph')
        md.inlinePatterns.add('imageblocklink', 
                              ImagePattern(IMAGE_PATTERN, md), 
                              '_begin')




import datetime

class Page:
    def __init__(self, generator, path, mtime, content, **kwargs):
        self.generator = generator
        self.path = path
        self.content = content
        self.mtime = mtime
        self.metadata = kwargs

    def change_extension(self, extension):
        i = self.path[-1].rfind('.')
        basename = self.path[-1][0:i]
        self.path[-1] = basename + extension


    def url(self):
        return '/' + '/'.join(self.path)

    def render(self, **kwargs):
        return self.content


class Templated(Page):
    template_extension = '.mako'
    def __init__(self, generator, **kwargs):
        template_name = kwargs.pop('template', None)
        Page.__init__(self, generator, **kwargs)
        
        if not template_name:
            template_path = self.path[:]
            i = self.path[-1].rfind('.')
            basename = self.path[-1][0:i]
            template_path[-1] = basename + self.template_extension
            template_name='/'.join(template_path)
            self.change_extension('.html')
        else:
            i = template_name.rfind('.')
            if template_name[i:] == '.mako':
                self.change_extension('.html')
            else:
                self.change_extension(template_name[i:])
            # Check for / and generate path otherwise

        self.template = generator.templates.get_template(template_name)

    def render(self, **kwargs):
        return self.template.render(pagepress=self.generator, page=self)

class HTML(Templated):
    pass

class Blog(HTML):
    def __init__(self, **kwargs):
        self.title = kwargs.pop('title')
        self.published = kwargs.pop('published', None)
        if self.published is not None:
            day, month, year = [int(i) for i in self.published.split('/')]
            self.published = datetime.date(year, month, day)
        HTML.__init__(self, **kwargs)


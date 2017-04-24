from withspec import describe, context
from pagepress.command import command

#asbool
#PagepressHttpHandler
#serve
#process_argv
#command

with describe(command):

    def subject():
        return command

    with context('empty argv') as test:
        def it_should_have_defaults(subject):
            pass



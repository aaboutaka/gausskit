from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion, PathCompleter, WordCompleter
from prompt_toolkit.key_binding import KeyBindings

class HybridCompleter(Completer):
    def __init__(self, completers):
        self.completers = completers

    def get_completions(self, document, complete_event):
        for completer in self.completers:
            yield from completer.get_completions(document, complete_event)

def tab_autocomplete_prompt(message, completer=None, default=''):
    bindings = KeyBindings()

    @bindings.add('tab')
    def _(event):
        b = event.app.current_buffer
        b.complete_next()

    return prompt(
        message,
        completer=completer,
        key_bindings=bindings,
        default=default,
    )


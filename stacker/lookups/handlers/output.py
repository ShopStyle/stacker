from collections import namedtuple
from stacker.exceptions import FailedVariableLookup

TYPE_NAME = "output"

Output = namedtuple("Output", ("stack_name", "output_name"))


def handler(value, context=None, **kwargs):
    """Fetch an output from the designated stack.

    Args:
        value (str): string with the following format:
            <stack_name>::<output_name>, ie. some-stack::SomeOutput
        context (:class:`stacker.context.Context`): stacker context

    Returns:
        str: output from the specified stack

    """

    if context is None:
        raise ValueError('Context is required')

    d = deconstruct(value)
    stack = context.get_stack(d.stack_name)
    try:
        return stack.outputs[d.output_name]
    except KeyError:
        raise KeyError("%s not in %s" % (d.output_name, stack.outputs.keys()))


def deconstruct(value):

    try:
        stack_name, output_name = value.split("::")
    except ValueError:
        raise ValueError("output handler requires syntax "
                         "of <stack>::<output>.  Got: %s" % value)

    return Output(stack_name, output_name)

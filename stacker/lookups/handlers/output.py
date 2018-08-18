from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from collections import namedtuple

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
    if stack.outputs is None:
        raise ValueError("No outputs for %s" % (d.stack_name))

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

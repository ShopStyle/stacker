from __future__ import absolute_import

import yaml


class include_tag_obj(object):

    def __init__(self, s):
        self.s = s

    def __str__(self):
        return self.s

    def __repr__(self):
        return 'include({})'.format(self.s)


def include_representer(dumper, data):
    return dumper.represent_scalar('!include', str(data))


def include_constructor(loader, tag_suffix, node):
    return include_tag_obj(node.value)


yaml.Dumper.add_representer(include_tag_obj, include_representer)
yaml.SafeDumper.add_representer(include_tag_obj, include_representer)
yaml.add_multi_constructor('!include', include_constructor)


def load_yaml(filename):
    with open(filename) as f:
        return yaml.load(f)


def write_yaml(filename, data):
    with open(filename, 'w') as f:
        f.write(yaml.safe_dump(data, default_flow_style=False))

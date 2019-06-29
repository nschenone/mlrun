from os import path
from pprint import pprint

import click
import json
import os
from ast import literal_eval
import getpass
from tempfile import mktemp

import yaml

from .runtimes import run_start
from .secrets import SecretsStore
from .utils import run_keys

@click.group()
def main():
    pass

@main.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("url", type=str)
@click.option('--param', '-p', default='', multiple=True,
              help="parameter name and value tuples, e.g. -p x=37 -p y='text'")
@click.option('--in-artifact', '-i', multiple=True, help='input artifact')
@click.option('--out-artifact', '-o', multiple=True, help='output artifact')
@click.option('--in-path', help='default input path/url (prefix) for artifact')
@click.option('--out-path', help='default output path/url (prefix) for artifact')
@click.option('--secrets', '-s', multiple=True, help='secrets file=<filename> or env=ENV_KEY1,..')
@click.option('--uid', help='unique run ID')
@click.option('--name', help='run name')
@click.option('--workflow', help='workflow name/id')
@click.option('--project', help='project name/id')
@click.option('--save-to', default='', help='save run results yaml to path/url')
@click.option('--runtime', '-r', default='local', help='runtime environment e.g. local, remote, nuclio, mpi')
@click.option('--kfp', default=False,  help='running inside Kubeflow Piplines')
@click.argument('run_args', nargs=-1, type=click.UNPROCESSED)
#@click.option('--secrets', '-s', type=click.File(), help='secrets file')
def run(url, param, in_artifact, out_artifact, in_path, out_path, secrets, uid, name,
        workflow, project, save_to, runtime, kfp, run_args):
    """Execute a task and inject parameters."""

    print(run_args)

    meta = {}
    set_item(meta, uid, 'uid')
    set_item(meta, name, 'name')
    set_item(meta, project, 'project')
    set_item(meta, workflow, 'workflow')

    labels = {'owner': getpass.getuser()}
    set_item(labels, workflow, 'workflow')
    meta['labels'] = labels

    spec = {'runtime': {'kind': runtime, 'command': url}}
    set_item(spec['runtime'], run_args, 'args', list(run_args))

    if param:
        params_dict = {}
        for param in param:
            i = param.find('=')
            if i == -1:
                continue
            key, value = param[:i].strip(), param[i + 1:].strip()
            if key is None:
                raise ValueError(f'cannot find param key in line ({param})')
            params_dict[key] = literal_eval(value)
        spec['parameters'] = params_dict

    set_item(spec, in_artifact, run_keys.input_objects, line2keylist(in_artifact))
    set_item(spec, in_path, run_keys.input_path)
    set_item(spec, out_path, run_keys.output_path)
    set_item(spec, out_artifact, run_keys.output_artifacts, line2keylist(out_artifact))
    set_item(spec, secrets, run_keys.secrets, line2keylist(secrets, 'kind', 'source'))

    struct = {'metadata': meta, 'spec': spec}
    resp = run_start(struct, save_to=save_to, kfp=kfp)
    if resp:
        print(yaml.dump(resp, default_flow_style=False, sort_keys=False))


def set_item(struct, item, key, value=None):
    if item:
        if value:
            struct[key] = value
        else:
            struct[key] = item


def line2keylist(lines: list, keyname='key', valname='path'):
    out = []
    for line in lines:
        i = line.find('=')
        if i == -1:
            raise ValueError('cannot find "=" in line ({}={})'.format(keyname, valname))
        key, value = line[:i].strip(), line[i + 1:].strip()
        if key is None:
            raise ValueError('cannot find key in line ({}={})'.format(keyname, valname))
        value = path.expandvars(value)
        out += [{keyname: key, valname: value}]
    return out


if __name__ == "__main__":
    main()


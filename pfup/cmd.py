#!/usr/bin/env python3

import argparse
import os

import git
import pygerrit2
import requests
import ruamel.yaml


FORGE_URL = 'https://forgeapi.puppet.com/v3'
GERRIT_URL = 'http://review.rc.nectar.org.au'
GERRIT_PROJECT = 'internal/puppet-library'


def check_module(module):
    module_url = '%s/modules/%s' % (FORGE_URL, module.replace('/', '-'))
    response = requests.get(module_url)
    module_json = response.json()
    latest_version = module_json['releases'][0]['version']
    return latest_version


def check_modules(modules, open_changes):
    new_modules = []
    found_update = False
    message = ''

    for module in modules:
        name, version = list(module.items())[0]
        if name.startswith('openstack'):
            print("Skipping openstack module")
            new_modules.append(module)
            continue
        latest = check_module(name)
        if latest != version and not found_update:
            message = "%s %s -> %s" % (name, version, latest)
            if message not in open_changes:
                print(message)
                new_modules.append({name: str(latest)})
                found_update = True
                continue
            else:
                print("Skipping %s, pending review exists" % name)
        new_modules.append(module)
    return new_modules, message


def get_gerrit_open_changes(username, password):
    auth = pygerrit2.HTTPBasicAuth(username, password)
    gerrit = pygerrit2.GerritRestAPI(url=GERRIT_URL, auth=auth)
    changes = gerrit.get(
        "/changes/?q=project:%s status:open" % GERRIT_PROJECT)
    subjects = [c['subject'] for c in changes]
    print("Open changes are %s" % subjects)
    return subjects


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('modules_file', type=argparse.FileType('r+'))
    parser.add_argument('--gerrit-username',
                        default=os.environ.get('GERRIT_USERNAME',
                                               os.environ['USER']))
    parser.add_argument('--gerrit-password',
                        default=os.environ.get('GERRIT_PASSWORD'))
    args = parser.parse_args()

    open_changes = get_gerrit_open_changes(args.gerrit_username,
                                           args.gerrit_password)

    data = args.modules_file.read()
    yaml = ruamel.yaml.YAML()
    yaml.default_flow_style = False
    yaml_data = yaml.load(data)
    current_modules = yaml_data['modules_forge']

    new_modules, message = check_modules(current_modules, open_changes)

    yaml_data['modules_forge'] = new_modules
    args.modules_file.seek(0)
    yaml.dump(yaml_data, args.modules_file)
    args.modules_file.truncate()
    repo = git.Repo('.')
    changed_files = [item.a_path for item in repo.index.diff(None)]
    if message and changed_files:
        repo.index.add(changed_files)
        repo.index.commit(message)


if __name__ == '__main__':
    main()

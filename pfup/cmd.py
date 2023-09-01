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

# number of commits this will send up per run
COMMIT_LIMIT = 1


def check_module(module):
    module_url = '%s/modules/%s' % (FORGE_URL, module.replace('/', '-'))
    response = requests.get(module_url)
    module_json = response.json()
    latest_version = module_json['releases'][0]['version']
    return latest_version


def check_modules(modules, open_changes, constraints=[]):
    new_modules = []
    commits = 0
    message = ''

    for module in modules:
        name, version = list(module.items())[0]
        if name.startswith('openstack'):
            print("Skipping openstack module")
            new_modules.append(module)
            continue
        latest = check_module(name)
        if latest != version and commits < COMMIT_LIMIT:
            message = "%s %s -> %s" % (name, version, latest)
            if message not in open_changes:
                if constraints:
                    if not check_constraint(name, latest, constraints):
                        print("Skipping %s, due to constraints file" % name)
                        new_modules.append(module)
                        continue
                print(message)
                new_modules.append({name: str(latest)})
                commits += 1
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


def check_constraint(module_name, module_version, constraints_modules):
    for module in constraints_modules:
        name, version = list(module.items())[0]
        if name == module_name and version == module_version:
            return True
    return False


def modules_file_to_yaml(modules_file):
    data = modules_file.read()
    yaml = ruamel.yaml.YAML()
    yaml.default_flow_style = False

    return yaml, yaml.load(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('modules_file', type=argparse.FileType('r+'))
    parser.add_argument('--constraints-modules-file',
                        type=argparse.FileType('r+'),
                        help='Module file with allowed versions to upgrade to',
                        default=None)
    parser.add_argument('--gerrit-username',
                        default=os.environ.get('GERRIT_USERNAME',
                                               os.environ['USER']))
    parser.add_argument('--gerrit-password',
                        default=os.environ.get('GERRIT_PASSWORD'))
    args = parser.parse_args()

    open_changes = get_gerrit_open_changes(args.gerrit_username,
                                           args.gerrit_password)

    yaml, yaml_data = modules_file_to_yaml(args.modules_file)

    constraints = modules_file_to_yaml(args.constraints_modules_file)[
                  1]['modules_forge']if args.constraints_modules_file else None

    new_modules, message = check_modules(yaml_data['modules_forge'],
                                         open_changes,
                                         constraints)

    yaml_data['modules_forge'] = new_modules
    args.modules_file.seek(0)
    yaml.dump(yaml_data, args.modules_file)
    args.modules_file.truncate()
    repo = git.Repo('.')
    changed_files = [item.a_path for item in repo.index.diff(None)]
    return
    if message and changed_files:
        repo.index.add(changed_files)
        repo.index.commit(message + '\n')


if __name__ == '__main__':
    main()

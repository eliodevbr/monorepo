#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

import git
import ruamel.yaml
from git import RemoteProgress
from ruamel.yaml import YAML


class CloneProgress(RemoteProgress):
	def update(self, op_code, cur_count, max_count=None, message=''):
		if message:
			print(message)


class ExplicitDefaultsHelpFormatter(ArgumentDefaultsHelpFormatter):
	def _get_help_string(self, action):
		if action.default in (None, False):
			return action.help
		return super()._get_help_string(action)


ARGS_PARSED = None
DOCKER_REGISTRY = None

PARSER = ArgumentParser(
	usage='''%(prog)s\n''',
	description='Python MonoRepo Local Development',
	add_help=True,
	formatter_class=ExplicitDefaultsHelpFormatter)

PARSER.add_argument('-b', '--branch',
					dest='branch',
					required=False,
					type=str,
					default='main',
					help='Branch Name')

PARSER.add_argument('--ssh',
					dest='ssh',
					action='store_true',
					default=True,
					help='Uses SSH Protocol to clone')

PARSER.add_argument('--ssh-key',
					dest='ssh_key_path',
					type=str,
					default=os.path.expanduser(os.path.join('~', '.ssh', 'id_rsa')),
					help='SSH Key path location')


def represent_merger(self, data):
	return self.represent_scalar(u'tag:yaml.org,2002:merge', u'<<')


def represent_none(self, data):
	return self.represent_scalar(u'tag:yaml.org,2002:null', u'')


def ignore_aliases(self, data):
	return False


def load_yaml(load_data):
	try:
		if os.path.isfile(load_data):
			with open(load_data, 'r') as read_stream:
				yaml_data = read_stream.read()
		else:
			yaml_data = load_data
		return ruamel.yaml.round_trip_load(yaml_data, preserve_quotes=True)
	except Exception as load_yaml_ex:
		print(load_yaml_ex)


yml = YAML()
yml.preserve_quotes = True
yml.allow_duplicate_keys = True
yml.sort_base_mapping_type_on_output = True
yml.representer.add_representer(type(None), represent_none)
yml.representer.add_representer(u'tag:yaml.org,2002:merge', u'<<')
yml.indent(mapping=2, sequence=4, offset=2)


async def docker_build_images(docker_builder):
	print('Building Docker Images')

	build_tasks = []  # [asyncio.create_task(docker_build_image(build)) for build in docker_builder]

	print()
	print('Waiting for Docker Images to be built to complete...')
	print()

	await asyncio.wait(build_tasks)


def git_clone(repositories):
	idx = int
	repo = name = svc = git_repo_dir = None
	try:
		for idx, repo_info in enumerate(repositories):
			print(f'{str(idx)} - {repo_info}')
			repo = repo_info['repo']
			name = repo_info['name']
			svc = repo_info['dest']
			git_repo_dir = os.path.join(os.getcwd(), svc, name)

			if not os.path.exists(git_repo_dir):
				clone(git_repo_dir, repo)
	except Exception as e:
		logging.error(f'{idx} - Fail when try to prepare the cloning repo: {repo} into: {git_repo_dir}. {e}')


def clone(dest_repo_dir, repository):
	try:
		with git.Git().custom_environment(GIT_SSH_COMMAND=GIT_SSH_CMD):
			git.Repo.clone_from(repository, dest_repo_dir, progress=CloneProgress())
	except git.GitCommandError as e:
		logging.error(e)
		try:
			with git.Git().custom_environment(GIT_SSH_COMMAND=GIT_SSH_CMD):
				git.Repo.clone_from(repository, dest_repo_dir, branch=ARGS_PARSED.branch, progress=CloneProgress())
		except Exception as e:
			logging.error(e)


if __name__ == '__main__':
	GIT_SSH_CMD = None
	ARGS_PARSED, ARGS_PARSED_RESULTS = PARSER.parse_known_args()

	if len(ARGS_PARSED_RESULTS) > 0:
		logging.fatal(f'ArgsParse are not able to parse: {ARGS_PARSED_RESULTS}')
		exit(1)

	if ARGS_PARSED.ssh:
		GIT_SSH_CMD = 'ssh -i %s' % ARGS_PARSED.ssh_key_path

	repositories_data = load_yaml(os.path.join(os.getcwd(), 'repositories.yaml'))

	for repo_type in repositories_data['repositories']:
		git_clone(repositories_data['repositories'][repo_type])

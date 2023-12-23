#!/usr/bin/env python

import subprocess
import json
import datetime
import sys
import os

def get_issue(repository: str, number: int) -> dict:
	command = f"""gh issue view \
		--repo "{repository}" \
		"{number}" \
		--json title,author,number
	"""
	proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	pr_json, errors = proc.communicate()
	if proc.returncode != 0:
		print(errors)
		exit(1)
	return json.loads(pr_json)

def get_issues(repository: str, label: str) -> list:
	# print(f"Fetching Issues with label v4")
	command = f"""gh search issues \
		--repo "{repository}" \
		--label "{label}" \
		--state "open" \
		--json number
	"""
	proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	issues_json, errors = proc.communicate()
	if proc.returncode != 0:
		print(errors)
		exit(1)
	issues = list()
	for result in json.loads(issues_json):
		issues.append(get_issue(repository, result["number"]))

	return issues

def get_pr(repository: str, number: int) -> dict:
	command = f"""gh pr view \
		--repo "{repository}" \
		"{number}" \
		--json title,author,number
	"""
	proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	pr_json, errors = proc.communicate()
	if proc.returncode != 0:
		print(errors)
		exit(1)
	return json.loads(pr_json)

def get_prs(repository: str, label: str) -> list:
	# print(f"Fetching PRs with label v4")
	command = f"""gh search prs \
		--repo "{repository}" \
		--label "{label}" \
		--state "open" \
		--json number
	"""
	proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	prs_json, errors = proc.communicate()
	if proc.returncode != 0:
		print(errors)
		exit(1)
	prs = list()
	for result in json.loads(prs_json):
		prs.append(get_pr(repository, result["number"]))

	return prs


def run(source_repository: str, label: str):
	issues = get_issues(source_repository, label)
	issues_length = len(issues)
	print(f"Found {issues_length} Issues labelled with v4:")
	for issue in issues:
		print(f"* [#{issue['number']}](https://github.com/coreruleset/coreruleset/issues/{issue['number']}) {issue['title']}")

	print()

	prs = get_prs(source_repository, label)
	prs_length = len(prs)
	print(f"Found {prs_length} PRs labelled with v4:")
	for pr in prs:
		print(f"* [#{pr['number']}](https://github.com/coreruleset/coreruleset/pull/{issue['number']}) {pr['title']}")

	if issues_length == 0 and prs_length == 0:
	   print()
	   print(f"Congratulations! You're done. CRSv4 is ready.")
	   print()

if __name__ == "__main__":
	# disable pager
	os.environ["GH_PAGER"] = ''

	label = "v4"

	source_repository = 'coreruleset/coreruleset'

	run(source_repository, label)


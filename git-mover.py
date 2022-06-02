#!/usr/bin/env python2
# coding=utf-8

import requests
import json
import argparse
import os
import sys
import re
import math
import time

def check_res(r):
    """Test if a response object is valid"""
    # if the response status code is a failure (outside of 200 range)
    if r.status_code < 200 or r.status_code >= 300:
        # print the status code and associated response. Return false
        print("STATUS CODE: " + str(r.status_code))
        print("ERROR MESSAGE: " + r.text)
        print("REQUEST: " + str(r))
        # if error, return False
        return False
    # if successful, return True
    return True


def get_req(url, credentials):
    """
    INPUT: an API endpoint for retrieving data
    OUTPUT: the request object containing the retrieved data for successful requests. If a request fails, False is returned.
    """
    print("GETTING: " + url)
    r = requests.get(url=url, auth=(credentials['user_name'], credentials['token']), headers={
                     'Content-type': 'application/json'})
    return r


def post_req(url, data, credentials):
    """
    INPUT: an API endpoint for posting data
    OUTPUT: the request object containing the posted data response for successful requests. If a request fails, False is returned.
    """
    #print("POSTING: " + url)
    r = requests.post(url=url, data=data, auth=(credentials['user_name'], credentials['token']), headers={
                      'Content-type': 'application/json', 'Accept': 'application/vnd.github.v3.html+json'})
    return r


def download_issues(source_url, source, credentials):
    """
    INPUT:
        source_url: the root url for the GitHub API
        source: the team and repo '<team>/<repo>' to retrieve issues from
    OUTPUT: retrieved issues sorted by their number if request was successful. False otherwise
    """
    issues = []
    url = "%srepos/%s/issues?filter=all" % (source_url, source)

    while True:
        r = get_req(url, credentials)
        status = check_res(r)
        time.sleep(1)
        if not status:
            break

        # if the requests succeeded, sort the retireved issues by their number
        issues_on_page = json.loads(r.text)
        if not issues_on_page:
            break

        for i in issues_on_page:
            issues.append(i)

        # Find the next page
        if not r.headers['Link']:
            break

        m = re.search('<([^>]*)>; rel="next"', r.headers['Link'])
        if not m:
            break

        url = m.group(1)

    return sorted(issues, key=lambda k: k['number'])


def create_issues(issues, destination_url, destination, credentials, sameInstall, issues_log_file, issues_log):
    """Post issues to GitHub
    INPUT:
        issues: python list of dicts containing issue info to be POSTED to GitHub
        destination_url: the root url for the GitHub API
        destination_urlination: the team and repo '<team>/<repo>' to post issues to
        milestones: a boolean flag indicating that milestones were included in this migration
        labels: a boolean flag indicating that labels were included in this migration
    OUTPUT: Null
    """
    url = destination_url + "repos/" + destination + "/issues"
    issues_size = len(issues)
    issues_current = 0;
    for issue in issues:
        # create a new issue object containing only the data necessary for the creation of a new issue
        assignee = None
        #if (issue["assignee"] and sameInstall):
        #    assignee = issue["assignee"]["login"]
        issue_prime = {"title": issue["title"], "body": issue["body"],
                       "assignee": assignee, "state": issue["state"]}

        # if labels were migrated and the issue to be migrated contains labels
        if "labels" in issue:
            issue_prime["labels"] = list(map(lambda l : l["name"], issue["labels"]))

        if not issue["number"] in issues_log:
            limit_delay = 60;
            repeat = 10;
            while repeat > 0:
                r = post_req(url, json.dumps(issue_prime), credentials)
                status = check_res(r)
                # if adding the issue failed
                if not status:
                    # get the message from the response
                    message = json.loads(r.text)
                    # if the error message is for an invalid entry because of the assignee field, remove it and repost with no assignee
                    if 'errors' in message and message['errors'][0]['code'] == 'invalid' and message['errors'][0]['field'] == 'assignee':
                        sys.stderr.write("WARNING: Assignee " + message['errors'][0]['value'] + " on issue \"" + issue_prime['title'] +
                                "\" does not exist in the destination repository. Issue added without assignee field.\n\n")
                        issue_prime.pop('assignee')
                        post_req(url, json.dumps(issue_prime), credentials)
                        repeat = 0
                    if 'secondary rate limit' in message['message']:
                        limit_reset = int(r.headers['X-RateLimit-Reset'])
                        current_time = time.time()
                        header_delay = int(math.ceil(limit_reset - current_time))
                        if limit_delay > header_delay:
                            delay = header_delay
                        else:
                            delay = limit_delay
                        print 'Limit: ',r.headers['X-RateLimit-Limit'],' Used: ',r.headers['X-RateLimit-Used']
                        print 'Reset: ',time.strftime("%D %H:%M",time.localtime(limit_reset)),' Time to reset: {}'.format(header_delay),' seconds'
                        print 'Rate limit exceeded, waiting {} seconds before {} retry'.format(delay,issue["number"])
                        time.sleep(delay)
                        repeat -= 1
                        limit_delay *= 2
                    else:
                        repeat = 0
                else:
                    percent_done = float(issues_current) / float(issues_size)
                    issues_log_file.write(str(issue["number"]) + ',' + str(json.loads(r.text)["number"]) + '\n')
                    issues_log_file.flush()
                    print "[","{:.0%}".format(percent_done),"] Created ",issue["number"], "->", json.loads(r.text)["number"]
                    repeat = 0
            # Avoid secondary rate limit as much as possible
            time.sleep(2)
        else:
            percent_done = float(issues_current) / float(issues_size)
            print "[","{:.0%}".format(percent_done),"] Skipped ",issue["number"], "->", issues_log[issue["number"]]
        issues_current += 1

# Transfer log files directory
GITMOVE_DIR='.gitmove'

def gitmove_dir(home_dir):
    if home_dir.endswith('/'):
        dir = home_dir + GITMOVE_DIR
    else:
        dir = home_dir + '/' + GITMOVE_DIR
    if not os.path.exists(dir):
        print "Created issues log directory: ", dir
        os.makedirs(dir)
    return dir


def file_path(source_repo, destination_repo, gitmove_dir):
    return gitmove_dir + '/' + source_repo.replace('/','_') + ':' + destination_repo.replace('/','_')

def read_log(file_path):
    log = dict()
    print "Reading issues log file: ", file_path
    issues_log_file = open(file_path, 'r')
    exit = False
    while not exit:
        line = issues_log_file.readline()
        if len(line) == 0:
            exit = True
        else:
            if line.endswith('\n'):
                line = line[:-1]
            else:
                exit = True
            numbers = line.split(',')
            src_issue = int(numbers[0])
            dst_issue = int(numbers[1])
            print " - added ", src_issue, " -> ", dst_issue
            log[src_issue] = dst_issue
    issues_log_file.close()
    return log

def main():
    parser = argparse.ArgumentParser(
        description='Migrate Milestones, Labels, and Issues between two GitHub repositories. To migrate a subset of elements (Milestones, Labels, Issues), use the element specific flags (--milestones, --lables, --issues). Providing no flags defaults to all element types being migrated.')
    parser.add_argument('user_name', type=str,
                        help='Your GitHub (public or enterprise) username: name@email.com')
    parser.add_argument(
        'token', type=str, help='Your GitHub (public or enterprise) personal access token')
    parser.add_argument('source_repo', type=str,
                        help='the team and repo to migrate from: <team_name>/<repo_name>')
    parser.add_argument('destination_repo', type=str,
                        help='the team and repo to migrate to: <team_name>/<repo_name>')
    parser.add_argument('--destinationToken', '-dt', nargs='?', type=str,
                        help='Your personal access token for the destination account, if you are migrating between GitHub installations')
    parser.add_argument('--destinationUserName', '-dun', nargs='?', type=str,
                        help='Username for destination account, if you are migrating between GitHub installations')
    parser.add_argument('--sourceRoot', '-sr', nargs='?', default='https://api.github.com', type=str,
                        help='The GitHub domain to migrate from. Defaults to https://www.github.com. For GitHub enterprise customers, enter the domain for your GitHub installation.')
    parser.add_argument('--destinationRoot', '-dr', nargs='?', default='https://api.github.com', type=str,
                        help='The GitHub domain to migrate to. Defaults to https://www.github.com. For GitHub enterprise customers, enter the domain for your GitHub installation.')
    parser.add_argument('--numbers', '-n', type=str,
                        help="Comma separated numbers of specific issues to migrate (or explicitly pass --allIssues)")
    parser.add_argument('--allIssues', '-a', action="store_true", help='Migrate all issues.')
    parser.add_argument('--reset', '-r', action="store_true", help='Reset issues log.')
    args = parser.parse_args()

    if bool(args.allIssues) == bool(args.numbers):
        sys.stderr.write(
            'Please specify --allIssues or specific issues to migrate with --numbers\n')
        quit()

    destination_repo = args.destination_repo
    source_repo = args.source_repo
    source_credentials = {'user_name': args.user_name, 'token': args.token}

    if (args.sourceRoot != 'https://api.github.com'):
        args.sourceRoot += '/api/v3'

    if (args.destinationRoot != 'https://api.github.com'):
        args.destinationRoot += '/api/v3'

    if (args.sourceRoot != args.destinationRoot):
        if not (args.destinationToken):
            sys.stderr.write(
                "Error: Source and Destination Roots are different but no token was supplied for the destination repo.")
            quit()

    if not (args.destinationUserName):
        print('No destination User Name provided, defaulting to source User Name: ' + args.user_name)
        args.destinationUserName = args.user_name
    if not (args.destinationToken):
        print('No destination Token provided, defaulting to source Token: ' + args.token)
        args.destinationToken = args.token

    destination_credentials = {
        'user_name': args.destinationUserName, 'token': args.destinationToken}

    source_root = args.sourceRoot + '/'
    destination_root = args.destinationRoot + '/'

    home_dir = os.environ['HOME']
    issues_log_path = file_path(source_repo, destination_repo, gitmove_dir(home_dir))

    if bool(args.reset) and os.path.exists(issues_log_path):
        print "Deleted issues log file: ", issues_log_path
        os.remove(issues_log_path)

    if os.path.exists(issues_log_path):
        issues_log = read_log(issues_log_path)
        issues_log_file = open(issues_log_path, 'a')
    else:
        issues_log = dict()
        issues_log_file = open(issues_log_path, 'w')

    issues = download_issues(source_root, source_repo, source_credentials)
    if args.numbers:
        numbers = list(map(int, args.numbers.split(',')))
        issues = filter(lambda i : int(i["number"]) in numbers, issues)
    if issues:
        sameInstall = False
        if (args.sourceRoot == args.destinationRoot):
            sameInstall = True
        create_issues(issues, destination_root, destination_repo,
                      destination_credentials, sameInstall, issues_log_file, issues_log)
    elif issues is False:
        sys.stderr.write(
            'ERROR: Issues failed to be retrieved. Exiting...')
        quit()
    else:
        print("No Issues found. None migrated")


if __name__ == "__main__":
    main()

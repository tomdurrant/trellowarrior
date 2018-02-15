#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2015 Óscar García Amor <ogarcia@connectical.com>
#
# Distributed under terms of the MIT license.

import logging

from ConfigParser import RawConfigParser
from tasklib.task import Task
from tasklib.backends import TaskWarrior
from trello import TrelloClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# logger.basicConfig(level=logging.WARNING)

def parse_config(config_file):
    """Parse config file and return True if all OK.

    All config settings are stored in global vars.
    :config_file: config file name
    """
    global trello_api_key, trello_api_secret, trello_token, trello_token_secret
    global taskwarrior_taskrc_location, taskwarrior_data_location
    global sync_projects
    global link_projects
    sync_projects = {}
    link_projects = {}
    conf = RawConfigParser()
    try:
        conf.read(config_file)
    except Exception as e:
        logger.exception('Failed to read config', e)
        return False

    for required_key in ['trello_api_key',
                         'trello_api_secret',
                         'trello_token',
                         'trello_token_secret',
                         'sync_projects']:
        if not conf.has_option('DEFAULT', required_key):
            logger.error('Missing required config: %s' % required_key, e)
            return False

    for sync_project in conf.get('DEFAULT', 'sync_projects').split():
        if conf.has_section(sync_project):
            if (conf.has_option(sync_project, 'tw_project_name') and
                conf.has_option(sync_project, 'trello_board_name')):
                project = {}
                for key in ['trello_board_name', 'trello_doing_list',
                            'trello_done_list', 'trello_todo_list',
                            'tw_project_name', 'trello_member_id',
                            'create_trello_labels']:
                    if conf.has_option(sync_project, key):
                        project[key] = conf.get(sync_project, key)

                if not conf.has_option(sync_project, 'trello_done_list'):
                     project['trello_done_list'] = 'Done'
                if not conf.has_option(sync_project, 'trello_member_id'):
                     project['trello_member_id'] = None
                if not conf.has_option(sync_project, 'create_trello_labels'):
                     project['create_trello_labels'] = False
                if conf.has_option(sync_project, 'ignore_lists'):
                     project['ignore_lists'] = conf.get(sync_project, 'ignore_lists').split(',')
                else:
                     project['ignore_lists'] = []
                sync_projects.update({sync_project: project})
            else:
                logger.info('Skipping %s, missing tw_project_name or trello_board_name' % sync_project)
                return False
        else:
            logger.info('Missing config for %s' % sync_project)
            return False

    for link_project in conf.get('DEFAULT', 'link_projects').split():
        if conf.has_section(link_project):
            if (conf.has_option(link_project, 'tw_project_name') and
                conf.has_option(link_project, 'trello_board_name') and
                conf.has_option(link_project, 'link_to')
                ):
                project = {}
                for key in ['trello_board_name', 'trello_doing_list',
                            'trello_done_list', 'trello_todo_list',
                            'tw_project_name', 'trello_member_id',
                            'link_to', 'link_label']:
                    if conf.has_option(link_project, key):
                        project[key] = conf.get(link_project, key)

                if not conf.has_option(link_project, 'trello_done_list'):
                     project['trello_done_list'] = 'Done'
                link_projects.update({link_project: project})
            else:
                logger.info('Skipping %s, missing tw_project_name trello_board_name or link_to' % link_project)
                return False
        else:
            logger.info('Missing config for %s' % link_project)
            return False

    trello_api_key = conf.get('DEFAULT', 'trello_api_key')
    trello_api_secret = conf.get('DEFAULT', 'trello_api_secret')
    trello_token = conf.get('DEFAULT', 'trello_token')
    trello_token_secret = conf.get('DEFAULT', 'trello_token_secret')
    if conf.has_option('DEFAULT', 'taskwarrior_taskrc_location'):
        taskwarrior_taskrc_location = conf.get('DEFAULT', 'taskwarrior_taskrc_location')
    else:
        taskwarrior_taskrc_location = '~/.taskrc'
    if conf.has_option('DEFAULT', 'taskwarrior_data_location'):
        taskwarrior_data_location = conf.get('DEFAULT', 'taskwarrior_data_location')
    else:
        taskwarrior_data_location = '~/.task'
    return True


def get_trello_boards():
    """ Get all Trello boards """
    logger.info('Fetching Trello boards ...')
    trello_client = TrelloClient(
        api_key=trello_api_key,
        api_secret=trello_api_secret,
        token=trello_token,
        token_secret=trello_token_secret)
    logger.info('... done')
    return trello_client.list_boards()

def get_trello_board(board_name):
    """
    Returns Trello board from name
    If it does not exist, create it and return new board

    :board_name: the board name
    """
    trello_boards = get_trello_boards()
    for trello_board in trello_boards:
        if trello_board.name == board_name:
            logger.info('Fetched board %s' % board_name)
            return trello_board
    return create_trello_board(board_name)

def create_trello_board(board_name):
    """
    Create Trello board and returns it

    :board_name: the board name
    """
    trello_client = TrelloClient(
        api_key=trello_api_key,
        api_secret=trello_api_secret,
        token=trello_token,
        token_secret=trello_token_secret)
    logger.info('Created board %s' % board_name)
    return trello_client.add_board(board_name)

def get_trello_lists(board_name):
    """
    Returns a set of list objects

    :board_name: the board name
    """
    logger.info('Fetching Trello lists ...')
    return get_trello_board(board_name).open_lists()

def get_trello_list(board_name, trello_lists, list_name):
    """
    Returns a list object

    :board_name: the board name
    :trello_lists: the set of lists
    :list_name: the list name
    """
    for trello_list in trello_lists:
        if trello_list.name == list_name:
            logger.info('Fetched list %s' % list_name)
            return trello_list
    trello_list = create_trello_list(board_name, list_name)
    trello_lists.append(trello_list) # mutate the list, eek!
    return trello_list

def create_trello_list(board_name, list_name):
    """
    Returns a new list object from project name and listname

    :board_name: the board name
    :list_name: the list name
    """
    logger.info('Creating list %s' % list_name)
    trello_board = get_trello_board(board_name)
    return trello_board.add_list(list_name)

def get_trello_dic_cards(trello_lists):
    """
    Returns a dic of lists with a set of card objects in each element

    :trello_lists: the set of lists
    """
    trello_cards = {}
    for trello_list in trello_lists:
        trello_cards[trello_list.name] = trello_list.list_cards()
    return trello_cards

def delete_trello_card(trello_card_id):
    """
    Delete (forever) a Trello Card by ID

    :trello_card_id: Trello card ID
    """
    trello_client = TrelloClient(
        api_key=trello_api_key,
        api_secret=trello_api_secret,
        token=trello_token,
        token_secret=trello_token_secret)
    try:
        trello_card = trello_client.get_card(trello_card_id)
        trello_card.delete()
        logger.info('Deleted card %s' % trello_card_id)
    except Exception as e:
        logger.exception('Cannot find Trello card')
        print('Cannot find Trello card with ID {0} deleted in Taskwarrior. Maybe you deleted it in Trello too.'.format(trello_card_id))

def upload_tw_task(tw_task, trello_list, trello_member_id=None,
        create_trello_labels=False):
    """
    Upload all contents of task to list creating a new card and storing cardid

    :tw_task: TaskWarrior task object
    :trello_list: Trello list object
    :trello_member_id: Assign uploaded tasks to this member
    """
    new_trello_card = trello_list.add_card(tw_task['description'])
    if tw_task['due']:
        new_trello_card.set_due(tw_task['due'])
    if trello_member_id:
        new_trello_card.assign(trello_member_id)
    for tag in tw_task['tags']:
        label = get_label(new_trello_card, tag,
                create_missing_label=create_trello_labels)
        if label and label not in new_trello_card.labels:
            new_trello_card.add_label(label)
    # Save the Trello Card ID into Task
    tw_task['trelloid'] = new_trello_card.id
    tw_task.save()
    logger.info('Created Trello card %s' % tw_task['description'])

def download_trello_card(project_name, list_name, trello_card, task_warrior, doing_list_name, done_list_name):
    """Download all contents of Trello card, creating new Taskwarrior task

    :project_name: the name of project where the card is stored
    :list_name: the name of list where the card is stored
    :trello_card: a Trello Card object
    :task_warrior: Taskwarrior object
    :doing_list_name: name of doing list to set task active
    :done_list_name: name of done list to set task done
    """
    new_tw_task = Task(task_warrior)
    new_tw_task['project'] = project_name
    new_tw_task['description'] = trello_card.name
    if trello_card.due_date:
        new_tw_task['due'] = trello_card.due_date
    for label in trello_card.labels:
        new_tw_task['tags'].add(label.name)
    new_tw_task['trelloid'] = trello_card.id
    new_tw_task['trellolistname'] = list_name
    new_tw_task.save()
    if list_name == doing_list_name:
        new_tw_task.start()
    if list_name == done_list_name:
        new_tw_task.done()

def get_tw_task_by_trello_id(trello_id):
    """
    Get a task by Trello ID
    Trello ID must be unique, if not this raise an error

    :project_name: the project name
    :trello_id: Trello card ID
    """
    tw_tasks = TaskWarrior(
        taskrc_location=taskwarrior_taskrc_location,
        data_location=taskwarrior_data_location
    ).tasks.filter(trelloid=trello_id)
    if len(tw_tasks) == 0:
        return None
    elif len(tw_tasks) == 1:
        return tw_tasks[0]
    else:
        logger.error('Duplicated Trello ID {0} in Taskwarrior tasks. Trello IDs must be unique, please fix it before sync.'.format(trello_id))
        raise ValueError('Duplicated Trello ID {0} in Taskwarrior tasks. Trello IDs must be unique, please fix it before sync.'.format(trello_id))

def upload_new_tw_tasks(trello_lists, project_name, board_name, todo_list_name,
        doing_list_name, done_list_name, trello_member_id=None,
        create_trello_labels=False):
    """
    Upload new TaskWarrior tasks that never uploaded before

    :trello_lists: the set of lists
    :project_name: the project name
    :board_name: the name of Trello board
    :todo_list_name: name of list for todo taks
    :doing_list_name: name of list for active tasks
    :done_list_name: name of list for done tasks
    :trello_member_id: Assign uploaded tasks to this member
    """
    task_warrior = TaskWarrior(taskrc_location=taskwarrior_taskrc_location, data_location=taskwarrior_data_location)
    tw_pending_tasks   = task_warrior.tasks.pending().filter(project=project_name, trelloid=None)
    tw_completed_tasks = task_warrior.tasks.completed().filter(project=project_name, trelloid=None)
    for tw_pending_task in tw_pending_tasks:
        if tw_pending_task.active:
            upload_tw_task(tw_pending_task, get_trello_list(board_name,
                trello_lists, doing_list_name),
                trello_member_id=trello_member_id,
                create_trello_labels=create_trello_labels)
            tw_pending_task['trellolistname'] = doing_list_name
            tw_pending_task.save()
        else:
            if tw_pending_task['trellolistname']:
                upload_tw_task(tw_pending_task, get_trello_list(board_name,
                    trello_lists, tw_pending_task['trellolistname']),
                    trello_member_id=trello_member_id,
                    create_trello_labels=create_trello_labels)
            else:
                upload_tw_task(tw_pending_task, get_trello_list(board_name,
                    trello_lists, todo_list_name),
                    trello_member_id=trello_member_id,
                    create_trello_labels=create_trello_labels)
                tw_pending_task['trellolistname'] = todo_list_name
                tw_pending_task.save()
    for tw_completed_task in tw_completed_tasks:
        upload_tw_task(tw_completed_task, get_trello_list(board_name,
            trello_lists, done_list_name), trello_member_id,
            create_trello_labels=create_trello_labels)
        tw_completed_task['trellolistname'] = done_list_name
        tw_completed_task.save()
    logger.info('Uploaded new cards: %s pending, %s completed' % (len(tw_pending_tasks), len(tw_completed_tasks)))

def sync_trello_tw(trello_lists, project_name, board_name, todo_list_name,
        doing_list_name, done_list_name, trello_member_id=None,
        create_trello_labels=False, ignore_lists=[]):
    """
    Download from Trello all cards and sync with TaskWarrior tasks

    :trello_lists: the set of lists
    :project_name: the project name
    :board_name: the name of Trello board
    :todo_list_name: name of list for todo taks
    :doing_list_name: name of list for active tasks
    :done_list_name: name of list for done tasks
    :trello_member_id: Only sync cards assigned to this member
    """
    task_warrior = TaskWarrior(taskrc_location=taskwarrior_taskrc_location, data_location=taskwarrior_data_location)
    # Get all Taskwarrior deleted tasks and seek for ones that have trelloid (locally deleted)
    tw_deleted_tasks = task_warrior.tasks.filter(project=project_name,status='deleted')
    for tw_deleted_task in tw_deleted_tasks:
        if tw_deleted_task['trelloid']:
            delete_trello_card(tw_deleted_task['trelloid'])
            tw_deleted_task['trelloid'] = None
            tw_deleted_task.save()
    # Compare and sync Trello with Taskwarrior
    trello_dic_cards = get_trello_dic_cards(trello_lists)
    trello_cards_ids = []
    for list_name in trello_dic_cards:
        if list_name in ignore_lists:
            continue
        for trello_card in trello_dic_cards[list_name]:
            # Fetch all data from card
            trello_card.fetch(False)
            trello_cards_ids.append(trello_card.id)
            if trello_member_id:
                if trello_member_id not in trello_card.member_ids:
                    logging.debug("Not syncing as member does not match %s" % trello_member_id)
                    continue
            tw_task = get_tw_task_by_trello_id(trello_card.id)
            if tw_task:
                sync_task_card(tw_task, trello_card, board_name, trello_lists,
                        list_name, todo_list_name, doing_list_name,
                        done_list_name, create_trello_labels=create_trello_labels)
            else:
                # Download new Trello cards that not present in Taskwarrior
                download_trello_card(project_name, list_name, trello_card, task_warrior, doing_list_name, done_list_name)
    # Compare Trello and TaskWarrior tasks for remove deleted Trello tasks in Taskwarrior
    tw_pending_tasks_ids   = set((task['trelloid'] for task in task_warrior.tasks.pending().filter(project=project_name)))
    tw_completed_tasks_ids = set((task['trelloid'] for task in task_warrior.tasks.completed().filter(project=project_name)))
    tw_tasks_ids = tw_pending_tasks_ids | tw_completed_tasks_ids
    tw_tasks_ids.discard(None) # Remove None element if present (new tasks created with Taskwarrior)
    trello_cards_ids = set(trello_cards_ids)
    deleted_trello_tasks_ids = tw_tasks_ids - trello_cards_ids
    for deleted_trello_task_id in deleted_trello_tasks_ids:
        task_to_delete = get_tw_task_by_trello_id(deleted_trello_task_id)
        task_to_delete['trelloid'] = None
        task_to_delete.save()
        task_to_delete.delete()
    logger.info('Synced. Deleted (%s local, %s remote), updated or new: %s' % (len(tw_deleted_tasks), len(deleted_trello_tasks_ids), len(trello_dic_cards)))

def sync_task_card(tw_task, trello_card, board_name, trello_lists, list_name,
        todo_list_name, doing_list_name, done_list_name,
        create_trello_labels=False):
    """
    Sync existing Trello Card with existing Taskwarrior task

    :tw_task: the Taskwarrior task object
    :trello_card: the Trello card object
    :board_name: the name of Trello board
    :trello_lists: the set of lists
    :list_name: the name of list where the card is stored
    :todo_list_name: name of list for todo taks
    :doing_list_name: name of list for active tasks
    :done_list_name: name of list for done tasks
    """
    tw_task_modified = False
    # Task description - Trello card name
    if tw_task['description'] != trello_card.name:
        if tw_task['modified'] > trello_card.date_last_activity:
            trello_card.set_name(tw_task['description'])
        else:
            tw_task['description'] = trello_card.name
            tw_task_modified = True
    # Task due - Trello due
    if tw_task['due']:
        if trello_card.due_date:
            if tw_task['modified'] > trello_card.date_last_activity:
                trello_card.set_due(tw_task['due'])
            else:
                tw_task['due'] = trello_card.due_date
                tw_task_modified = True
        else:
            trello_card.set_due(tw_task['due'])
    else:
        if trello_card.due_date:
            tw_task['due'] = trello_card.due_date
            tw_task_modified = True
    # Task tags - Trello labels
    if (tw_task['tags'] or trello_card.labels):
        if tw_task['modified'] > trello_card.date_last_activity:
            for tag in tw_task['tags']:
                label = get_label(trello_card, tag, create_missing_label=create_trello_labels)
                if label and label not in trello_card.labels:
                    trello_card.add_label(label)
            for label in trello_card.labels:
                if label.name not in tw_task['tags']:
                    trello_card.remove_label(label)
        else:
            for label in trello_card.labels:
                if label.name not in tw_task['tags']:
                    tw_task['tags'].add(label.name)
                    tw_task_modified = True
            remove = set()
            for tag in tw_task['tags']:
                label = get_label(trello_card, tag, create_missing_label=create_trello_labels)
                if label not in trello_card.labels:
                    remove.add(tag)
                    tw_task_modified = True
            tw_task['tags'] = tw_task['tags'].difference_update(remove)
        tw_task.save()
        tw_task_modified = False # Set false cause just saved
    # Task List Name / Status - Trello List name
    if tw_task['trellolistname'] == doing_list_name or tw_task['trellolistname'] == done_list_name:
        if tw_task.pending and not tw_task.active and tw_task['modified'] > trello_card.date_last_activity:
            print ('Task %s kicked to To Do') % (tw_task['id'])
            trello_list = get_trello_list(board_name, trello_lists, todo_list_name)
            trello_card.change_list(trello_list.id)
            tw_task['trellolistname'] = todo_list_name
            list_name = todo_list_name
            tw_task_modified = True
    if tw_task['trellolistname'] != doing_list_name and tw_task.active and tw_task['modified'] > trello_card.date_last_activity:
        print ('Task %s kicked to Doing') % (tw_task['id'])
        trello_list = get_trello_list(board_name, trello_lists, doing_list_name)
        trello_card.change_list(trello_list.id)
        tw_task['trellolistname'] = doing_list_name
        list_name = doing_list_name
        tw_task_modified = True
    if tw_task['trellolistname'] != done_list_name and tw_task.completed and tw_task['modified'] > trello_card.date_last_activity:
        print ('Task %s kicked to Done') % (tw_task['id'])
        trello_list = get_trello_list(board_name, trello_lists, done_list_name)
        trello_card.change_list(trello_list.id)
        tw_task['trellolistname'] = done_list_name
        list_name = done_list_name
        tw_task_modified = True
    if tw_task['trellolistname'] != list_name:
        if tw_task['modified'] > trello_card.date_last_activity:
            print ('Task %s kicked to Trello list %s') % (tw_task['id'], tw_task['trellolistname'])
            trello_list = get_trello_list(board_name, trello_lists, tw_task['trellolistname'])
            trello_card.change_list(trello_list.id)
        else:
            tw_task['trellolistname'] = list_name
            if list_name == done_list_name:
                print ('Task %s kicked to Done') % (tw_task['id'])
                if tw_task.completed:
                    tw_task.save()
                    tw_task_modified = False # Set false cause just saved
                else:
                    tw_task.save()
                    tw_task.done()
                    tw_task_modified = False
            elif list_name == doing_list_name:
                print ('Task %s kicked to Doing') % (tw_task['id'])
                if tw_task.completed:
                    tw_task['status'] = 'pending'
                    tw_task.save()
                    tw_task.start()
                    tw_task_modified = False
                elif tw_task.active:
                    tw_task.save()
                    tw_task_modified = False
                else:
                    tw_task.save()
                    tw_task.start()
                    tw_task_modified = False
            else:
                print ('Task %s kicked to %s') % (tw_task['id'], list_name)
                if tw_task.completed:
                    tw_task['status'] = 'pending'
                    tw_task_modified = True
                elif tw_task.active:
                    tw_task.save()
                    tw_task.stop()
                    tw_task_modified = False
                else:
                    tw_task_modified = True
    # Save Task warrior changes (if any)
    if tw_task_modified:
        tw_task.save()

def link_tagged_cards(board_name, todo_list_name, doing_list_name, done_list_name,
                     link_label, create_trello_labels=False):
    trello_lists_src  = get_trello_lists(board_name['src'])
    trello_lists_dest = get_trello_lists(board_name['dest'])
    trello_dic_cards_src  = get_trello_dic_cards(trello_lists_src)
    trello_dic_cards_dest = get_trello_dic_cards(trello_lists_dest)
    trello_cards_ids = []
    #for list_name in trello_dic_cards_src:
    for list_name in [todo_list_name, doing_list_name, done_list_name]:
        for trello_card in trello_dic_cards_src[list_name['src']]:
            label = get_label(trello_card, link_label, create_missing_label=create_trello_labels)
            if not label or label not in trello_card.labels:
                continue
            logger.info("Linking %s" % trello_card.name)
            # Fetch all data from card
            trello_card.fetch(False)
            exists = False
            #for list_name_dest in trello_dic_cards_dest:
            for trello_card_dest in trello_dic_cards_dest[list_name['dest']]:
                if trello_card_dest.name == trello_card_dest.name:
                    logger.info("Card %s exists" % trello_card.name)
                    exists = True
            if not exists:
                logger.info("Creating new %s " % trello_card.name)
                trello_list_dest = get_trello_list(board_name['dest'], trello_lists_dest, list_name['dest'])
                new_trello_card = trello_list_dest.add_card(trello_card.name)
                new_trello_card.attach(url=trello_card.url)
                # Assign member of card to link
                for member_id in trello_card.member_ids:
                    new_trello_card.assign(member_id)
    #if  trello_card.date_last_activity > trello_card.date_last_activity:

def link_project_cards(src, dest, link_label):
    link_tagged_cards(
            {'src': src['trello_board_name'], 'dest': dest['trello_board_name']},
            {'src': src['trello_todo_list'], 'dest': dest['trello_todo_list']},
            {'src': src['trello_doing_list'], 'dest': dest['trello_doing_list']},
            {'src': src['trello_done_list'], 'dest': dest['trello_done_list']},
            link_label=link_label
            )

def get_label(trello_card, label, create_missing_label=False):
    for lab in trello_card.board.get_labels():
        if lab.name == label:
            return lab
    if create_missing_label:
        logger.info('Label %s does not exist, creating' % label)
        return trello_card.board.add_label(label, 'green')
    else:
        return None

def main():
    for dkey in sync_projects:
        # Get all Trello lists
        project = sync_projects[dkey]
        trello_lists = get_trello_lists(project['trello_board_name'])
        # Do sync Trello - Taskwarrior
        sync_trello_tw(trello_lists,
                       project['tw_project_name'],
                       project['trello_board_name'],
                       project['trello_todo_list'],
                       project['trello_doing_list'],
                       project['trello_done_list'],
                       project['trello_member_id'],
                       project['create_trello_labels'],
                       project['ignore_lists'],
                       )
        # Upload new Taskwarrior tasks
        upload_new_tw_tasks(trello_lists,
                            project['tw_project_name'],
                            project['trello_board_name'],
                            project['trello_todo_list'],
                            project['trello_doing_list'],
                            project['trello_done_list'],
                            project['trello_member_id'],
                            project['create_trello_labels'],
                            )

    for dkey in link_projects:
        project = link_projects[dkey]
        link_project_cards(project,
                           sync_projects[project['link_to']],
                           project['link_label'])

if __name__ == "__main__":
    if parse_config('/home/tdurrant/.trellowarrior.conf'):
        main()

import unittest
from trellowarrior import link_tagged_cards, parse_config

class TestSync(unittest.TestCase):

    def test(self):
        board_name = {'src': 'trellotest', 'dest': 'trellotest2'}
        todo_list_name = {'src': 'To Do', 'dest': 'To Do'}
        doing_list_name = {'src': 'Doing', 'dest': 'Doing'}
        done_list_name = {'src': 'Done', 'dest': 'Done'}
        sync_tag = 'sync'
        link_tagged_cards(board_name, todo_list_name, doing_list_name, done_list_name,
                     sync_tag)


if __name__ == "__main__":
    if parse_config('/home/tdurrant/.trellowarrior.conf'):
        unittest.main()


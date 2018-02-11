import unittest
from trellowarrior import sync_tagged_cards, parse_config

class TestSync(unittest.TestCase):

    def test(self):
        board_name_src='trellotest'
        board_name_dest='trellotest2'
        todo_list_name_src='To Do'
        doing_list_name_src='Doing'
        done_list_name_src='Done'
        todo_list_name_dest='To Do'
        doing_list_name_dest='Doing'
        done_list_name_dest='Done'
        sync_tag = 'sync'
        sync_tagged_cards(board_name_src, todo_list_name_src, doing_list_name_src, done_list_name_src,
                      board_name_dest, todo_list_name_dest, doing_list_name_dest, done_list_name_dest,
                     sync_tag)


if __name__ == "__main__":
    if parse_config('/home/tdurrant/.trellowarrior.conf'):
        unittest.main()


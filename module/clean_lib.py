import argparse
import os
import re
import sys


cur_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(cur_dir)
from Util import Logger



if __name__ == '__main__':
    # 1.parse args
    parser = argparse.ArgumentParser(description='run HiTE...')
    parser.add_argument('--tmp_output_dir', metavar='tmp_output_dir',
                        help='Please enter the directory for output. Use an absolute path.')
    parser.add_argument('--debug', metavar='recover',
                        help='Open debug mode, and temporary files will be kept, 1: true, 0: false.')

    args = parser.parse_args()

    tmp_output_dir = args.tmp_output_dir
    debug = int(args.debug)

    log = Logger(tmp_output_dir+'/HiTE_clean.log', level='debug')


    # remove temp files and directories
    if debug == 0:
        keep_files_temp = []
        keep_files = ['genome\.rename\.fa', 
                    'genome\.rename\.fa\.pass\.list', 
                    '.*\.scn',
                    'genome\.rename\.fa\.LTRlib\.fa', 
                    'confident_TE\.cons\.fa',
                    'confident_TE\.cons\.fa\.domain',
                    'confident_ltr_cut\.fa',
                    'confident_TE\.cons\.fa\.classified', 
                    'longest_repeats(_\d+)?\.flanked\.fa', 
                    'longest_repeats(_\d+)?\.fa',
                    'confident_tir(_\d+)?\.fa',
                    'confident_helitron(_\d+)?\.fa',
                    'confident_non_ltr(_\d+)?\.fa',
                    'confident_other(_\d+)?\.fa',
                    'repbase.out',
                    'HiTE.out',
                    'HiTE.tbl',
                    'HiTE.gff',
                    'HiTE_intact.sorted.gff3',
                    'BM_RM2.log',
                    'BM_EDTA.log',
                    'BM_HiTE.log']

        all_files = os.listdir(tmp_output_dir)
        for filename in all_files:
            is_del = True
            for keep_file in keep_files:
                is_match = re.match(keep_file+'$', filename)
                if is_match is not None:
                    is_del = False
                    break
            if is_del:
                os.system('rm -rf ' + tmp_output_dir + '/' + filename)



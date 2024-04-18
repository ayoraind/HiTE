import argparse
from datetime import datetime
import os
import re
import sys

cur_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(cur_dir)

from Util import Logger, read_fasta, multi_process_tsd, store_fasta, get_full_length_copies_RM

if __name__ == '__main__':
    # 1.parse args
    parser = argparse.ArgumentParser(description='run HiTE generating full-length TE annotation...')
    parser.add_argument('-t', metavar='threads number',
                        help='Input threads number.')
    parser.add_argument('--ltr_list', metavar='ltr_list',
                        help='The path of ltr list')
    parser.add_argument('--tir_lib', metavar='tir_lib',
                        help='The path of tir library')
    parser.add_argument('--helitron_lib', metavar='helitron_lib',
                        help='The path of helitron library')
    parser.add_argument('--other_lib', metavar='other_lib',
                        help='The path of other library')
    parser.add_argument('--chr_name_map', metavar='chr_name_map',
                        help='The path of chr_name_map')
    parser.add_argument('-r', metavar='reference',
                        help='Input reference Path')
    parser.add_argument('--tmp_output_dir', metavar='tmp_output_dir',
                        help='Please enter the directory for output. Use an absolute path.')
    parser.add_argument('--module_home', metavar='module_home',
                        help='HiTE module home.')
    parser.add_argument('--TRsearch_dir', metavar='TRsearch_dir',
                        help='Please enter the directory where the itrsearch tool is located. Please use the absolute path.')
    parser.add_argument('--search_struct', metavar='search_struct',
                        help='Is the structural information of full-length copies being searched?')

    args = parser.parse_args()
    threads = int(args.t)
    ltr_list = args.ltr_list
    tir_lib = args.tir_lib
    helitron_lib = args.helitron_lib
    other_lib = args.other_lib
    chr_name_map = args.chr_name_map
    reference = args.r
    tmp_output_dir = args.tmp_output_dir
    module_home = args.module_home
    TRsearch_dir = args.TRsearch_dir
    search_struct = int(args.search_struct)
    if search_struct == 1:
        search_struct = True
    else:
        search_struct = False

    reference = os.path.abspath(reference)

    log = Logger(tmp_output_dir+'/HiTE_full_length_annotation.log', level='debug')

    # hyperparameters
    divergence_threshold = 20
    full_length_threshold = 0.95

    # Step 1. 对于LTR来说，我们可以直接根据LTR_retriever生成的.pass.list生成全长LTR注释。
    generate_ltr_gff_command = 'perl ' + module_home + '/generate_gff_for_ltr.pl ' + ltr_list + ' ' + chr_name_map
    log.logger.debug(generate_ltr_gff_command)
    os.system(generate_ltr_gff_command)

    # Step 2. 寻找 TIR，Helitron，non-LTR 全长拷贝：
    # 使用FMEA算法尝试跨过gap.
    # 如果跨过 gap 后，拷贝与consensus的 coverage >= t (t=95%或99%)，则认为是候选全长拷贝。记录它们在染色体上的位置和序列。
    # 使用 cd-hit 过滤掉不满足条件（80-80-80 rule）的候选全长拷贝
    TE_lib = tmp_output_dir + '/TE_tmp.fa'
    os.system('cat ' + tir_lib + ' ' + helitron_lib + ' ' + other_lib + ' > ' + TE_lib)
    intact_dir = tmp_output_dir + '/intact_tmp'
    full_length_annotations, copies_direct = get_full_length_copies_RM(TE_lib, reference, intact_dir, threads, divergence_threshold,
                                                   full_length_threshold, search_struct)

    # Step 3. 获取TE的classification，并将其加入到注释中
    confident_TE_path = tmp_output_dir + '/confident_TE.fa'
    classified_TE_path = confident_TE_path + '.classified'
    contignames, contigs = read_fasta(classified_TE_path)
    TE_classifications = {}
    for name in contignames:
        parts = name.split('#')
        TE_classifications[parts[0]] = parts[1]

    TE_gff = tmp_output_dir + '/TE_tmp.gff3'
    intact_count = 0
    with open(TE_gff, 'w') as f_save:
        for query_name in full_length_annotations.keys():
            query_name = str(query_name)
            classification = TE_classifications[query_name]
            for copy_annotation in full_length_annotations[query_name]:
                chr_pos = copy_annotation[0]
                annotation = copy_annotation[1]
                parts = chr_pos.split(':')
                chr_name = parts[0]
                chr_pos_parts = parts[1].split('-')
                chr_start = str(int(chr_pos_parts[0])+1)
                chr_end = str(chr_pos_parts[1])
                if query_name.__contains__('TIR'):
                    type = 'TIR'
                elif query_name.__contains__('Helitron'):
                    type = 'Helitron'
                elif query_name.__contains__('Homology_Non_LTR'):
                    type = 'Non_LTR'
                intact_count += 1
                update_annotation = 'id=te_intact_'+str(intact_count)+';name='+query_name+';classification='+classification+';'+annotation
                f_save.write(chr_name+'\t'+'HiTE'+'\t'+type+'\t'+chr_start+'\t'+chr_end+'\t'+'.\t'+copies_direct[chr_pos]+'\t'+'.\t'+update_annotation+'\n')

    # Step 4. 合并LTR和其他转座子注释
    all_gff = tmp_output_dir + '/HiTE_intact.gff3'
    all_sorted_gff = tmp_output_dir + '/HiTE_intact.sorted.gff3'
    LTR_gff = ltr_list + '.gff3'
    os.system('cat ' + LTR_gff + ' ' + TE_gff + ' > ' + all_gff)
    os.system('sort -k1,1 -k4n ' + all_gff + ' > ' + all_sorted_gff)
    gff_lines = []
    with open(all_sorted_gff, 'r') as f_r:
        for line in f_r:
            if line.startswith('#'):
                continue
            gff_lines.append(line)

    date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    header = (
        "##gff-version 3\n"
        f"##date {date}\n"
        "##ltr_identity: Sequence identity (0-1) between the left and right LTR region.\n"
        "##tir_identity: Sequence identity (0-1) between the left and right TIR region.\n"
        "##tsd: target site duplication\n"
    )
    with open(all_sorted_gff, "w") as gff_file:
        gff_file.write(header)
        for line in gff_lines:
            gff_file.write(line)








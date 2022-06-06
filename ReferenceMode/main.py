import argparse
import codecs
import sys

import datetime
import json
import multiprocessing
import os
import threading
import time
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import math
import pysam

#from command import run_bwa
from Util import convertToUpperCase, read_fasta, getReverseSequence, \
    Logger, split_repeats, compute_identity, run_alignment, multi_line, generate_blastlike_output, \
    get_multiple_alignment_repeat, split2cluster, cut_repeat_v1, judgeReduceThreads, get_ltr_suppl_from_ltrfinder, \
    store_fasta, printClass, parse_ref_blast_output, filter_LTR_high_similarity, get_alignment_info_v3, compare_seq, \
    getRegionCombination, getCombineFragments, convertToUpperCase_v1, generate_candidate_repeats_v2, cut_repeat_v2, \
    get_candidate_repeats, connect_frags, get_alignment_info_v4

dict_encode = {'A': 0b001, 'C': 0b011, 'G': 0b010, 'T': 0b100, 'N': 0b101}
def three_bit_encode(str):
    bytes = 0b000
    for i in range(len(str)):
        bytes <<= 3
        base = str[i]
        if not dict_encode.__contains__(base):
            base = 'N'
        bytes += dict_encode[base]
    return bytes

def generate_candidate_repeats(cur_segments, k_num, unique_kmer_map, fault_tolerant_bases):
    cur_lines = []
    cur_masked_segments = []
    for line in cur_segments:
        cur_lines.append(line)
        masked_line = list(line)
        last_masked_pos = -1
        for i in range(len(line)-k_num+1):
            kmer = line[i: i+k_num]
            # get reverse complement kmer
            r_kmer = getReverseSequence(kmer)
            # filter invalid kmer, contains 'N'
            if "N" in r_kmer:
                continue
            unique_key = kmer if kmer < r_kmer else r_kmer

            if unique_kmer_map.__contains__(unique_key):
                # mask position
                if last_masked_pos == -1:
                    for j in range(i, i+k_num):
                        masked_line[j] = 'X'
                    last_masked_pos = i+k_num-1
                else:
                    # do not need to mask position which has been masked
                    start_mask_pos = i if i > last_masked_pos else last_masked_pos+1
                    end_mask_pos = i+k_num
                    for j in range(start_mask_pos, end_mask_pos):
                        masked_line[j] = 'X'
                    last_masked_pos = end_mask_pos - 1
        cur_masked_segments.append(masked_line)

    repeat_list = []
    cur_repeat_str = ''
    try_connect_str = ''
    last_end_pos = -1
    for seq_index, cur_masked_segment in enumerate(cur_masked_segments):
        for i in range(len(cur_masked_segment)):
            if cur_masked_segment[i] == 'X':
                if try_connect_str != '':
                    cur_repeat_str = try_connect_str
                    try_connect_str = ''
                cur_repeat_str = cur_repeat_str + cur_lines[seq_index][i]
                last_end_pos = i
            elif cur_repeat_str != '' and cur_masked_segment[i] != 'N':
                if (i - last_end_pos) <= fault_tolerant_bases:
                    if try_connect_str == '':
                        try_connect_str = cur_repeat_str
                    try_connect_str = try_connect_str + cur_lines[seq_index][i]
                else:
                    repeat_list.append(cur_repeat_str)
                    cur_repeat_str = ''
                    try_connect_str = ''
    return repeat_list

def generate_candidate_repeats_v1(contigs, k_num, unique_kmer_map, fault_tolerant_bases):
    cur_lines = []
    cur_masked_segments = {}
    for ref_name in contigs.keys():
        line = contigs[ref_name]
        cur_lines.append(line)
        masked_line = list(line)
        last_masked_pos = -1
        for i in range(len(line)-k_num+1):
            kmer = line[i: i+k_num]
            # get reverse complement kmer
            r_kmer = getReverseSequence(kmer)
            # filter invalid kmer, contains 'N'
            if "N" in r_kmer:
                continue
            unique_key = kmer if kmer < r_kmer else r_kmer

            if unique_kmer_map.__contains__(unique_key):
                # mask position
                if last_masked_pos == -1:
                    for j in range(i, i+k_num):
                        masked_line[j] = 'X'
                    last_masked_pos = i+k_num-1
                else:
                    # do not need to mask position which has been masked
                    start_mask_pos = i if i > last_masked_pos else last_masked_pos+1
                    end_mask_pos = i+k_num
                    for j in range(start_mask_pos, end_mask_pos):
                        masked_line[j] = 'X'
                    last_masked_pos = end_mask_pos - 1
        cur_masked_segments[ref_name] = masked_line

    repeat_dict = {}
    cur_repeat_str = ''
    try_connect_str = ''
    last_start_pos = -1
    last_end_pos = -1
    for seq_index, cur_masked_item in enumerate(cur_masked_segments.items()):
        ref_name = cur_masked_item[0]
        cur_masked_segment = cur_masked_item[1]
        if not repeat_dict.__contains__(ref_name):
            repeat_dict[ref_name] = []
        repeat_list = repeat_dict[ref_name]
        for i in range(len(cur_masked_segment)):
            if cur_masked_segment[i] == 'X':
                if last_start_pos == -1:
                    # record masked sequence start position
                    last_start_pos = i
                if try_connect_str != '':
                    # recover skip gap sequence
                    cur_repeat_str = try_connect_str
                    try_connect_str = ''
                cur_repeat_str = cur_repeat_str + cur_lines[seq_index][i]
                last_end_pos = i
            elif cur_repeat_str != '' and cur_masked_segment[i] != 'N':
                # meet unmasked base
                if (i - last_end_pos) <= fault_tolerant_bases:
                    # skip gap
                    if try_connect_str == '':
                        try_connect_str = cur_repeat_str
                    try_connect_str = try_connect_str + cur_lines[seq_index][i]
                else:
                    # can not skip gap
                    repeat_list.append((last_start_pos, last_end_pos, cur_repeat_str))
                    cur_repeat_str = ''
                    try_connect_str = ''
                    last_start_pos = -1
        # keep last masked sequence
        if cur_repeat_str != '':
            repeat_list.append((last_start_pos, last_end_pos, cur_repeat_str))
            cur_repeat_str = ''
            try_connect_str = ''
            last_start_pos = -1
        repeat_dict[ref_name] = repeat_list
    return repeat_dict, cur_masked_segments


def generate_kmer_map(cur_segments, k_num, unique_kmer_map, merged_repeats, partiton_index):
    log.logger.debug('partition %d process: %d segments' %(partiton_index, len(cur_segments)))
    kmer_info_map = {}
    cur_lines = []
    cur_masked_segments = []
    for line in cur_segments:
        parts = line.split("\t")
        contigName = parts[0].split(" ")[0]
        # remove ">"
        contigName = contigName[1:]
        start = int(parts[1])
        line = parts[2]
        cur_lines.append(line)
        masked_line = list(line)
        last_masked_pos = -1
        for i in range(len(line)-k_num+1):
            kmer = line[i: i+k_num]
            # get reverse complement kmer
            r_kmer = getReverseSequence(kmer)
            # filter invalid kmer, contains 'N'
            if "N" in r_kmer:
                continue
            # encode with binary
            kmer_num = three_bit_encode(kmer)
            r_kmer_num = three_bit_encode(r_kmer)
            unique_key = kmer_num if kmer_num < r_kmer_num else r_kmer_num

            pos = start + i
            if unique_kmer_map.__contains__(unique_key):
                # mask position
                if last_masked_pos == -1:
                    for j in range(i, i+k_num):
                        masked_line[j] = 'X'
                    last_masked_pos = i+k_num-1
                else:
                    # do not need to mask position which has been masked
                    start_mask_pos = i if i > last_masked_pos else last_masked_pos+1
                    end_mask_pos = i+k_num
                    for j in range(start_mask_pos, end_mask_pos):
                        masked_line[j] = 'X'
                    last_masked_pos = end_mask_pos - 1
        cur_masked_segments.append(masked_line)

    repeat_list = []
    cur_repeat_str = ''
    for seq_index, cur_masked_segment in enumerate(cur_masked_segments):
        for i in range(len(cur_masked_segment)):
            if cur_masked_segment[i] == 'X':
                cur_repeat_str = cur_repeat_str + cur_lines[seq_index][i]
            elif cur_repeat_str != '':
                repeat_list.append(cur_repeat_str)
                cur_repeat_str = ''
    merged_repeats[partiton_index] = repeat_list
    log.logger.debug('partition %d process finished' % (partiton_index))

def getUniqueKmer_v1(cur_segments, partiton_index):
    #print('partition %d process: %d segments' % (partiton_index, len(cur_segments)))
    unique_kmers = []
    for line in cur_segments:
        kmer = line.split(' ')[0]
        r_kmer = getReverseSequence(kmer)
        unique_key = kmer if kmer < r_kmer else r_kmer
        unique_kmers.append(unique_key)
    return unique_kmers

def getUniqueKmer(unique_kmer_path):
    unique_kmer_map = {}
    with open(unique_kmer_path, 'r') as f_r:
        for line in f_r:
            kmer = line.split(' ')[0]
            r_kmer = getReverseSequence(kmer)
            kmer_num = three_bit_encode(kmer)
            r_kmer_num = three_bit_encode(r_kmer)
            unique_key = kmer_num if kmer_num < r_kmer_num else r_kmer_num
            unique_kmer_map[unique_key] = 1
    return unique_kmer_map


# A sequence may include multiple align position, e.g.,
# Node_0-len_5109 Node_0-len_5109 100.000 4651    0       0       459     5109    1       4651    0.0     8589
# Node_0-len_5109 Node_30444-len_20481    100.000 217     0       0       1       217     20265   20481   1.37e-110       401

def parse_self_blast_output(blastnResults_path, repeats_path, candidate_repeats_path):
    repeatContigNames, repeatContigs = read_fasta(repeats_path)
    # To facilite searching
    # strcuture: {'Node_1': {'Node_1': [(),(),], 'Node_2':[(),(),], ...}}
    # step1. construct blast records clustering by query name
    query_records = {}
    with open(blastnResults_path, 'r') as f_r:
        for line in f_r:
            parts = line.split('\t')
            query_name = parts[0]
            target_name = parts[1]
            identity = float(parts[2])
            match_base = int(parts[3])
            query_length = int(query_name.split('-')[1].split('_')[1])
            q_start = int(parts[6])
            q_end = int(parts[7])
            t_start = int(parts[8])
            t_end = int(parts[9])

            if not query_records.__contains__(query_name):
                query_records[query_name] = {}
            records = query_records[query_name]
            if not records.__contains__(target_name):
                records[target_name] = []
            same_target_records = records[target_name]
            same_target_records.append((identity, match_base, query_length, q_start, q_end, t_start, t_end))
            records[target_name] = same_target_records
            query_records[query_name] = records

    # strcuture: {'Node_1': {'Node_1': [(),(),], 'Node_2':[(),(),], ...}}
    # Node_0-len_5109 Node_0-len_5109 100.000 4651    0       0       459     5109    1       4651    0.0     8589
    # Node_0-len_5109 Node_30444-len_20481    100.000 217     0       0       1       217     20265   20481   1.37e-110       401

    # step2. splice sequence
    # a map is used to avoid adding redudant sequence
    candidate_family_repeat = []
    stored_repeat = {}
    for query_name in query_records.keys():
        query_length = int(query_name.split('-')[1].split('_')[1])
        records = query_records[query_name]
        for target_name in records.keys():
            for record in records[target_name]:
                # self alignment, identity < 80% and segment length < 80bp should be neglected
                if (query_name == target_name and record[1] == query_length) \
                        or record[0] < 80:
                    continue
                # jugde direction
                q_start = record[3]
                q_end = record[4]
                if q_start > q_end:
                    q_tmp = q_start
                    q_start = q_end
                    q_end = q_tmp
                seg_seq1 = repeatContigs[query_name][q_start-1: q_end]

                t_start = record[5]
                t_end = record[6]
                if t_start > t_end:
                    t_tmp = t_start
                    t_start = t_end
                    t_end = t_tmp
                seg_seq2 = repeatContigs[target_name][t_start-1: t_end]

                if not stored_repeat.__contains__(query_name):
                    stored_repeat[query_name] = []
                query_pos_records = stored_repeat[query_name]
                queryIsNewSequence = True
                for pos_record in query_pos_records:
                    if q_start >= pos_record[0] and q_end <= pos_record[1]:
                        queryIsNewSequence = False
                        break
                if queryIsNewSequence:
                    candidate_family_repeat.append(seg_seq1)
                    query_pos_records.append((q_start, q_end))
                stored_repeat[query_name] = query_pos_records

                if not stored_repeat.__contains__(target_name):
                    stored_repeat[target_name] = []
                target_pos_records = stored_repeat[target_name]
                targetIsNewSequence = True
                for pos_record in target_pos_records:
                    if t_start >= pos_record[0] and t_end <= pos_record[1]:
                        targetIsNewSequence = False
                        break
                if targetIsNewSequence:
                    # if spliced segments is not exactly equal, add to set
                    if not math.isclose(record[0], 100.000, rel_tol=1e-5):
                        candidate_family_repeat.append(seg_seq2)
                    target_pos_records.append((t_start, t_end))
                stored_repeat[target_name] = target_pos_records


    # step3. generate candidate repeats
    node_index = 0
    with open(candidate_repeats_path, 'w') as f_save:
        for sequence in candidate_family_repeat:
            f_save.write('>Node_'+str(node_index)+'-len_'+str(len(sequence))+'\n'+sequence+'\n')
            node_index += 1


def run_LTR_retriever_v1(Genome_Tools_Home, LTR_retriever_Home, reference, tmp_output_dir, threads):
    starttime = time.time()
    log.logger.debug('start LTR_harvest detection...')
    ltrharvest_command1 = Genome_Tools_Home + '/bin/gt suffixerator -db ' + reference + ' -indexname ' \
                          + reference + ' -tis -suf -lcp -des -ssp -sds -dna'
    ltrharvest_command2 = Genome_Tools_Home + '/bin/gt ltrharvest -index ' + reference \
                          + ' -seed 20 -minlenltr 100 -maxlenltr 7000 -similar 85 -mintsd 4 -maxtsd 6 ' \
                            '-motif TGCA -motifmis 1 -vic 10 -seqids yes > ' + tmp_output_dir + '/genome.fa.harvest.scn'

    os.system(ltrharvest_command1)
    os.system(ltrharvest_command2)
    endtime = time.time()
    dtime = endtime - starttime
    log.logger.debug("LTR_harvest running time: %.8s s" % (dtime))

    starttime = time.time()
    log.logger.debug('start LTR_retriever detection...')
    LTR_retriever_command = 'cd ' + tmp_output_dir + ' && ' + LTR_retriever_Home + '/LTR_retriever -noanno -genome ' + reference \
                            + ' -inharvest ' + tmp_output_dir + '/genome.fa.harvest.scn -threads ' + str(threads)
    os.system(LTR_retriever_command)
    endtime = time.time()
    dtime = endtime - starttime
    log.logger.debug("LTR_retriever running time: %.8s s" % (dtime))


def run_LTR_retriever(LTR_retriever_Home, reference, tmp_output_dir, threads):
    starttime = time.time()
    log.logger.debug('start LTR_retriever detection...')
    LTR_retriever_command = 'cd ' + tmp_output_dir + ' && ' + LTR_retriever_Home + '/LTR_retriever -genome ' + reference \
                            + ' -inharvest ' + tmp_output_dir + '/genome.fa.harvest.scn -threads ' + str(threads)
    os.system(LTR_retriever_command)
    endtime = time.time()
    dtime = endtime - starttime
    log.logger.debug("LTR_retriever running time: %.8s s" % (dtime))

def run_LTR_harvest(Genome_Tools_Home, reference, tmp_output_dir):
    starttime = time.time()
    log.logger.debug('start LTR_harvest detection...')
    ltrharvest_command1 = Genome_Tools_Home + '/bin/gt suffixerator -db ' + reference + ' -indexname ' \
                          + reference + ' -tis -suf -lcp -des -ssp -sds -dna'
    ltrharvest_command2 = Genome_Tools_Home + '/bin/gt ltrharvest -index ' + reference \
                          + ' -seed 20 -minlenltr 100 -maxlenltr 7000 -similar 85 -mintsd 4 -maxtsd 6 ' \
                            '-motif TGCA -motifmis 1 -vic 10 -seqids yes > ' + tmp_output_dir + '/genome.fa.harvest.scn'

    os.system(ltrharvest_command1)
    os.system(ltrharvest_command2)
    endtime = time.time()
    dtime = endtime - starttime
    log.logger.debug("LTR_harvest running time: %.8s s" % (dtime))



def run_GRF(GRF_Home, reference, tmp_output_dir, threads):
    grf_tir_command = GRF_Home + '/bin/grf-main -i ' + reference + ' -o ' + tmp_output_dir + ' -c 0 --min_tr 10 -t ' + str(threads)
    os.system(grf_tir_command)

    grf_mite_command = 'sh ' + GRF_Home + '/script/run_mite_detection.sh ' + reference + ' ' + tmp_output_dir + ' ' + str(threads)
    os.system(grf_mite_command)



if __name__ == '__main__':
    # 1.parse args
    parser = argparse.ArgumentParser(description='run kmerRepFinder...')
    parser.add_argument('G', metavar='Genome assembly',
                        help='input genome assembly path')
    parser.add_argument('-k', metavar='kmer size',
                        help='input kmer size, default = [ 31 ]')
    parser.add_argument('-t', metavar='thread num',
                        help='input thread num')
    parser.add_argument('a', metavar='alias name',
                        help='input alias name')
    parser.add_argument('-s', metavar='sensitive mode',
                        help='sensitive mode, default = [ 0 ]')
    parser.add_argument('--fault_tolerant_bases', metavar='fault_tolerant_bases',
                        help='the base number of fault tolerant in repeated kmers masking, default = [ 50 ]')
    parser.add_argument('-o', metavar='output dir',
                        help='output dir')
    parser.add_argument('--tandem_region_cutoff', metavar='tandem_region_cutoff',
                        help='Cutoff of the raw masked repeat regarded as tandem region, default = [ 0.8 ]')

    args = parser.parse_args()

    reference = args.G
    k_num = args.k
    threads = args.t
    alias = args.a
    output_dir = args.o
    sensitive_mode = args.s
    fault_tolerant_bases = args.fault_tolerant_bases
    tandem_region_cutoff = args.tandem_region_cutoff

    log = Logger('kmerRepFinder.log', level='debug')

    if reference is None:
        log.logger.error('\nreference path can not be empty')
        exit(-1)
    if output_dir is None:
        output_dir = os.getcwd() + '/output'
        log.logger.warning('\noutput directory path is empty, set to: ' + str(output_dir))

    if not os.path.isabs(reference):
        reference = os.path.abspath(reference)
    if not os.path.isabs(output_dir):
        output_dir = os.path.abspath(output_dir)

    default_k_num = 31
    if k_num is None:
        k_num = int(default_k_num)
    else:
        k_num = int(k_num)

    default_threads = int(cpu_count())
    if threads is None:
        threads = int(default_threads)
    else:
        threads = int(threads)

    default_sensitive_mode = '0'
    if sensitive_mode is None:
        sensitive_mode = default_sensitive_mode
    is_sensitive = False
    if sensitive_mode == '1':
        is_sensitive = True

    default_fault_tolerant_bases = 200

    if fault_tolerant_bases is None:
        fault_tolerant_bases = default_fault_tolerant_bases


    default_tandem_region_cutoff = 0.5
    if tandem_region_cutoff is None:
        tandem_region_cutoff = default_tandem_region_cutoff


    skip_threshold = 50
    identity_threshold = 0.95
    length_similarity_cutoff = 0.95

    partitions_num = int(threads)

    if is_sensitive:
        alignment_tool = 'Blast'
        alignment_param = ''
        detect_mode = 'Sensitive'
    else:
        alignment_tool = 'Minimap2 + BWA'
        detect_mode = 'Normal'

    log.logger.info('\n-------------------------------------------------------------------------------------------\n'
                    'Copyright (C) 2022 Kang Hu ( kanghu@csu.edu.cn )\n'
                    'Hunan Provincial Key Lab on Bioinformatics, School of Computer Science and \n'
                    'Engineering, Central South University, Changsha 410083, P.R. China.\n'
                    '-------------------------------------------------------------------------------------------')

    log.logger.info('\nParameters configuration\n'
                    '====================================System settings========================================\n'
                    '  [Setting] The K-mer Size = [ ' + str(k_num) + 'bp]  Default( ' + str(default_k_num) + ' )\n'
                    '  [Setting] Threads = [ ' + str(threads) + ' ]  Default( ' + str(default_threads) + ' )\n'
                    '  [Setting] Detect Mode = [ ' + str(detect_mode) + ' ]  ( -s : 1 -> Sensitive, other -> Normal )\n'
                    '  [Setting] Reference sequences / assemblies path = [ ' + str(reference) + ' ]\n'
                    '  [Setting] Alias = [ ' + str(alias) + ' ]\n'
                    '  [Setting] Maximum base number of variants between repeats = [ ' + str(skip_threshold) + ' ]\n'
                    '  [Setting] Cutoff of the raw masked repeat regarded as tandem region = [ ' + str(tandem_region_cutoff) + ' ]\n'
                    '  [Setting] Output Directory = [' + str(output_dir) + ']'
                    )

    # preset steps, no needs to execute time-consuming job again
    # when the job is retried due to abnormal termination.


    # Step1. read configuration
    param_config_path = os.getcwd() + "/ParamConfig.json"
    # read param config
    with open(param_config_path, 'r') as load_f:
        param = json.load(load_f)
    load_f.close()

    chrom_seg_length = int(param['chrom_seg_length'])

    i = datetime.datetime.now()
    #tmp_output_dir = output_dir + '/CRD.' + str(i.date()) + '.' + str(i.hour) + '-' + str(i.minute) + '-' + str(i.second)
    tmp_output_dir = output_dir + '/CRD.2022-06-02.17-36-14'
    if not os.path.exists(tmp_output_dir):
        os.makedirs(tmp_output_dir)

    total_starttime = time.time()
    tools_dir = os.getcwd() + '/tools'

    (ref_dir, ref_filename) = os.path.split(reference)
    (ref_name, ref_extension) = os.path.splitext(ref_filename)
#
#
#     # --------------------------------------------------------------------------------------
#     # background job: get LTR sequences from LTR_retriever for supplementary
#     Genome_Tools_Home = param['Genome_Tools_Home']
#     LTR_retriever_Home = param['LTR_retriever_Home']
#     # run LTR_retriver background job for LTR supplementary
#     # output of LTR_retriever
# # backjob = multiprocessing.Process(target=run_LTR_retriever_v1, args=(Genome_Tools_Home, LTR_retriever_Home, reference, tmp_output_dir, threads,))
# # backjob.start()


    # -------------------------------Stage01: this stage is used to generate kmer coverage repeats-------------------------------
    # pipeline_starttime = time.time()
    #
    # starttime = time.time()
    # # --------------------------------------------------------------------------------------
    # # Step1. dsk get unique kmers, whose frequency >= 2
    # freq_threshold = 10
    # ref_size = os.path.getsize(reference)
    # ref_size = ref_size / float(1024 * 1024)
    # if ref_size > 1024:
    #     #freq_threshold = 5
    #     log.logger.debug('warning: reference is larger than 1G, increase kmer size to explicit the repeat boundary')
    #     k_num = 39
    # log.logger.debug('Start step1: get unique kmers')
    # dsk_h5_path = ref_name + '.h5'
    # unique_kmer_path = tmp_output_dir + '/kmer.txt'
    # dsk_cmd1 = 'cd ' + ref_dir + ' && ' + tools_dir + '/dsk -file ' + reference + ' -kmer-size ' + str(k_num) + ' -abundance-min ' + str(freq_threshold)
    # dsk_cmd2 = 'cd ' + ref_dir + ' && ' + tools_dir + '/dsk2ascii -file ' + dsk_h5_path + ' -out ' + unique_kmer_path
    # log.logger.debug(dsk_cmd1)
    # #os.system(dsk_cmd1)
    # log.logger.debug(dsk_cmd2)
    # #os.system(dsk_cmd2)
    #
    # #tmp_output_dir = '/public/home/hpc194701009/KmerRepFinder_test/library/KmerRepFinder_lib/dmel/CRD.2022-05-28.16-22-0'
    # # unique_kmer_path = tmp_output_dir + '/kmer.txt'
    # # --------------------------------------------------------------------------------------
    # unique_kmer_map = {}
    # with open(unique_kmer_path, 'r') as f_r:
    #     for line in f_r:
    #         line = line.replace('\n', '')
    #         kmer = line.split(' ')[0]
    #         r_kmer = getReverseSequence(kmer)
    #         unique_key = kmer if kmer < r_kmer else r_kmer
    #         if unique_key.__contains__('N'):
    #             continue
    #         unique_kmer_map[unique_key] = 1
    #
    # reduce_partitions_num = judgeReduceThreads(unique_kmer_path, partitions_num, log)
    #
    # # --------------------------------------------------------------------------------------
    # # Step3. get candidate repeats
    # log.logger.debug('Start step3: get candidate repeats from kmer coverage')
    # connected_repeats = get_candidate_repeats(reference, chrom_seg_length, k_num, reduce_partitions_num, unique_kmer_map, fault_tolerant_bases, tmp_output_dir)
    #
    # # # # single threads will ensure the accuracy
    # # # contigs = convertToUpperCase(reference)
    # # # repeat_dict, masked_ref = generate_candidate_repeats_v1(contigs, k_num, unique_kmer_map, fault_tolerant_bases)
    #
    #
    # # generate repeats.fa and connected_regions
    # repeats_path = tmp_output_dir + '/repeats.fa'
    # node_index = 0
    # with open(repeats_path, 'w') as f_save:
    #     for ref_name in connected_repeats.keys():
    #         repeat_list = connected_repeats[ref_name]
    #         for repeat_item in repeat_list:
    #             start_pos = repeat_item[0]
    #             end_pos = repeat_item[1]
    #             query_name = 'N' + str(node_index) + '-s_' + str(ref_name) + '-' + str(start_pos) + '-' + str(end_pos)
    #             repeat = repeat_item[2]
    #             f_save.write('>' + query_name + '\n' + repeat + '\n')
    #             node_index += 1

    # -------------------------------Stage02: this stage is used to filter segmental duplications, and connect fragment repeats-------------------------------
    repeats_path = tmp_output_dir + '/repeats.fa'
    RepeatMasker_Home = param['RepeatMasker_Home']
    rm_command = RepeatMasker_Home + '/RepeatMasker -pa 48 -q -no_is -norna -nolow -lib ' + repeats_path + ' ' + reference
    log.logger.debug(rm_command)
    #os.system(rm_command)
    rm_out = tmp_output_dir + '/repeats.out'
    #os.system('cp ' + reference + '.out ' + rm_out)

    rm_out_tab = tmp_output_dir + '/repeats.out.tab'
    convert_rm2tab = 'cat ' + rm_out + ' | tr -s \' \' | sed \'s/^ *//g\' | tr \' \' \'\t\' > ' +rm_out_tab
    #os.system(convert_rm2tab)

    # parse out file
    # 1. filter segmental duplication, freq <= 3
    frag_num = 0
    repeat_ref_pos = {}
    with open(rm_out_tab, 'r') as f_r:
        for i, line in enumerate(f_r):
            if i <= 2:
                continue
            parts = line.split('\t')
            chr_name = parts[4]
            chr_start = int(parts[5])
            chr_end = int(parts[6])
            direct = parts[8]
            repeat_name = parts[9]
            if direct == '+':
                repeat_start = int(parts[11])
                repeat_end = int(parts[12])
            else:
                repeat_start = int(parts[13])
                repeat_end = int(parts[12])

            if not repeat_ref_pos.__contains__(repeat_name):
                repeat_ref_pos[repeat_name] = []
            ref_pos = repeat_ref_pos[repeat_name]
            ref_pos.append((chr_name, chr_start, chr_end, repeat_start, repeat_end))
            frag_num += 1

    # masking reference
    ref_contigNames, ref_contigs = read_fasta(reference)
    ref_contigs_list = {}
    for k, repeat_name in enumerate(repeat_ref_pos.keys()):
        ref_pos = repeat_ref_pos[repeat_name]
        #print('total repeat size: %d, current index: %d' %(len(repeat_ref_pos), k))
        for pos_item in ref_pos:
            repeat_start = pos_item[3]
            repeat_end = pos_item[4]

            chr_name = pos_item[0]
            chr_start = pos_item[1]
            chr_end = pos_item[2]
            chr_seq = ref_contigs[chr_name]

            if not ref_contigs_list.__contains__(chr_name):
                ref_contigs_list[chr_name] = [0 for i in range(len(chr_seq))]
            ref_list = ref_contigs_list[chr_name]
            for j in range(chr_start-1, chr_end):
                ref_list[j] += 1

    # filter base freq <= 3, and connect all repeats
    # connected_repeats = {ref_name: [(start_pos, end_pos)]}
    connected_repeats = {}
    for ref_name in ref_contigs_list.keys():
        ref_list = ref_contigs_list[ref_name]

        if not connected_repeats.__contains__(ref_name):
            connected_repeats[ref_name] = []
        repeat_pos = connected_repeats[ref_name]

        start_pos = -1
        end_pos = -1
        for i in range(len(ref_list)):
            if ref_list[i] > 3:
                if start_pos == -1:
                    start_pos = i
                end_pos = i
            elif start_pos != -1:
                repeat_pos.append((start_pos, end_pos))
                start_pos = -1
                end_pos = -1

    # store connected_repeats for testing
    connected_repeats_file = tmp_output_dir + '/connected_repeats.csv'
    with codecs.open(connected_repeats_file, 'w', encoding='utf-8') as f:
        json.dump(connected_repeats, f)

    refNames, refContigs = read_fasta(reference)
    filter1_repeats_path = tmp_output_dir + '/repeats.filter1.fa'
    # connected_regions = {ref_name: {region_id: [(f1, start1, end1), (f2, start2, end2), (f3, start3, end3)], [(f4, start4, end4), (f5, start5, end5), (f6, start6, end6)]}}
    connected_regions = {}
    node_index = 0
    region_index = 0
    with open(filter1_repeats_path, 'w') as f_save:
        for ref_name in connected_repeats.keys():
            repeat_list = connected_repeats[ref_name]
            if not connected_regions.__contains__(ref_name):
                connected_regions[ref_name] = {}
            regions = connected_regions[ref_name]
            ref_seq = refContigs[ref_name]
            last_start_pos = -1
            last_end_pos = -1
            for repeat_item in repeat_list:
                start_pos = repeat_item[0]
                end_pos = repeat_item[1]
                query_name = 'N' + str(node_index) + '-s_' + str(ref_name) + '-' + str(start_pos) + '-' + str(
                    end_pos)
                repeat = ref_seq[start_pos: end_pos+1]
                f_save.write('>' + query_name + '\n' + repeat + '\n')
                node_index += 1
                # generate connected_regions
                if last_start_pos == -1:
                    regions[region_index] = [(query_name, start_pos, end_pos)]
                else:
                    if (start_pos - last_end_pos) < skip_threshold:
                        # close to current region
                        cur_region = regions[region_index]
                        cur_region.append((query_name, start_pos, end_pos))
                        regions[region_index] = cur_region
                    else:
                        # far from current region, start a new region
                        region_index += 1
                        cur_region = []
                        cur_region.append((query_name, start_pos, end_pos))
                        regions[region_index] = cur_region
                last_start_pos = start_pos
                last_end_pos = end_pos
            connected_regions[ref_name] = regions

    # store connected_regions for testing
    connected_regions_file = tmp_output_dir + '/connected_regions.csv'
    with codecs.open(connected_regions_file, 'w', encoding='utf-8') as f:
        json.dump(connected_regions, f)

    # new strategy by Kang Hu 2022/05/24
    # find longest path to skip gap between fragments
    connected_frags = connect_frags(connected_regions, filter1_repeats_path, reference, threads, tools_dir, tmp_output_dir, skip_threshold)

    repeats_connected_file = tmp_output_dir + '/repeats_connected.fa'
    repeats_connected = {}
    index = 0
    for region_index in connected_frags.keys():
        for connected_frag in connected_frags[region_index]:
            connected_frag_name = connected_frag[0]
            query_name = 'R' + str(index) + '-' + connected_frag_name
            frag_name = connected_frag_name.split(',')[0]
            ref_name = frag_name.split('-s_')[1].split('-')[0]
            seq = refContigs[ref_name][connected_frag[1]: connected_frag[2] + 1]
            index += 1
            repeats_connected[query_name] = seq
    sorted_repeats_connected = {k: v for k, v in sorted(repeats_connected.items(), key=lambda item: -len(item[1]))}
    store_fasta(sorted_repeats_connected, repeats_connected_file)


    # candidate_TE_fragments = tmp_output_dir + '/candidate_TE_fragments.fa'
    # node_index = 0
    # with open(candidate_TE_fragments, 'w') as f_save:
    #     for repeat_name in TE_frags.keys():
    #         frags = TE_frags[repeat_name]
    #         for frag in frags:
    #             f_save.write('>N_'+str(node_index)+'\n'+frag+'\n')
    #             node_index += 1
    #
    # candidate_TE_fragments_consensus = tmp_output_dir + '/candidate_TE_fragments.cons.fa'
    # cd_hit_command = tools_dir + '/cd-hit-est -aS ' + str(0.8) + ' -c ' + str(0.8) + ' -A 80 -i ' + candidate_TE_fragments + ' -o ' + candidate_TE_fragments_consensus + ' -T 0 -M 0'
    # # cd_hit_command = tools_dir + '/cd-hit-est -aS ' + str(0.8) + ' -c ' + str(0.8) + ' -G 0 -g 1 -A 80 -i ' + candidate_TE_fragments + ' -o ' + candidate_TE_fragments_consensus + ' -T 0 -M 0'
    # log.logger.debug(cd_hit_command)
    # #os.system(cd_hit_command)
    #

    #
    #
    # # remove complete TE freq <= 3
    # rm_output1 = tmp_output_dir + '/candidate_TE_fragments.cons.fa.out'
    # rm_output1_tab = tmp_output_dir + '/candidate_TE_fragments.cons.fa.out.tab'
    # convert_rm2tab = 'cat ' + rm_output1 + ' | tr -s \' \' | sed \'s/^ *//g\' | tr \' \' \'\t\' > ' + rm_output1_tab
    # os.system(convert_rm2tab)
    #
    # repeats_contigNames, repeats_contigs = read_fasta(candidate_TE_fragments_consensus)
    #
    # repeat_ref_pos = {}
    # with open(rm_output1_tab, 'r') as f_r:
    #     for i, line in enumerate(f_r):
    #         if i <= 2:
    #             continue
    #         parts = line.split('\t')
    #         # print(parts)
    #         chr_name = parts[4]
    #         chr_start = int(parts[5])
    #         chr_end = int(parts[6])
    #         direct = parts[8]
    #         repeat_name = parts[9]
    #         repeat_seq = repeats_contigs[repeat_name]
    #         if direct == '+':
    #             repeat_start = int(parts[11])
    #             repeat_end = int(parts[12])
    #         else:
    #             repeat_start = int(parts[13])
    #             repeat_end = int(parts[12])
    #
    #         if not repeat_ref_pos.__contains__(repeat_name):
    #             repeat_ref_pos[repeat_name] = []
    #         ref_pos = repeat_ref_pos[repeat_name]
    #         ref_pos.append((chr_name, chr_start, chr_end, repeat_start, repeat_end, len(repeat_seq)))
    #         frag_num += 1
    #
    # TE_frags = {}
    # for repeat_name in repeat_ref_pos.keys():
    #     ref_pos = repeat_ref_pos[repeat_name]
    #     complete_TE_num = 0
    #     for pos_item in ref_pos:
    #         repeat_start = pos_item[3]
    #         repeat_end = pos_item[4]
    #         repeat_len = pos_item[5]
    #
    #         chr_name = pos_item[0]
    #         chr_start = pos_item[1]
    #         chr_end = pos_item[2]
    #
    #         if float(repeat_end - repeat_start) / repeat_len >= 0.8:
    #             complete_TE_num += 1
    #
    #     if complete_TE_num > 10:
    #         # true TE fragment
    #         repeat_seq = repeats_contigs[repeat_name]
    #         TE_frags[repeat_name] = repeat_seq
    #
    # TE_frag_path = tmp_output_dir + '/TE_fragments.fa'
    # store_fasta(TE_frags, TE_frag_path)
    #
    # # --------------------------------------------------------------------------------------
    # # Step6. filter low_complexity and tandem
    # # >= tandem_region_cutoff region of the whole repeat region, then it should be filtered, since maybe false positive
    # # keep sequences >= 50bp
    # TRF_Path = param['TRF_Path']
    # trf_dir = tmp_output_dir + '/trf_temp'
    # os.system('rm -rf ' + trf_dir)
    # if not os.path.exists(trf_dir):
    #     os.makedirs(trf_dir)
    # (repeat_dir, repeat_filename) = os.path.split(TE_frag_path)
    # (repeat_name, repeat_extension) = os.path.splitext(repeat_filename)
    # trf_command = 'cd ' + trf_dir + ' && ' + TRF_Path + ' ' + TE_frag_path + ' 2 7 7 80 10 50 500 -f -d -m'
    # log.logger.debug(trf_command)
    # os.system(trf_command)
    # trf_masked_repeats = trf_dir + '/' + repeat_filename + '.2.7.7.80.10.50.500.mask'
    #
    # trf_contigNames, trf_contigs = read_fasta(trf_masked_repeats)
    # repeats_contigNames, repeats_contigs = read_fasta(TE_frag_path)
    # filter_TE_path = tmp_output_dir + '/TE-filtered.fa'
    # with open(filter_TE_path, 'w') as f_save:
    #     for name in trf_contigNames:
    #         seq = trf_contigs[name]
    #         if float(seq.count('N')) / len(seq) < tandem_region_cutoff and len(seq) >= 50:
    #             f_save.write('>' + name + '\n' + repeats_contigs[name] + '\n')




    # # --------------------------------------------------------------------------------------
    # # Step4. determine repeats boundary
    # use_align_tools = 'bwa'
    # sam_path_bwa = run_alignment(repeats_path, reference, use_align_tools, threads, tools_dir)
    # cut_repeats_path = tmp_output_dir + '/repeats.cut.fa'
    # cut_repeat_v2(sam_path_bwa, repeats_path, cut_repeats_path)
    #
    # # merge redundant sequences
    # cut_repeats_consensus = tmp_output_dir + '/repeats.cut.cons.fa'
    # cd_hit_command = tools_dir + '/cd-hit-est -aS ' + str(length_similarity_cutoff) + ' -c ' + str(identity_threshold) + ' -i ' + cut_repeats_path + ' -o ' + cut_repeats_consensus + ' -T 0 -M 0'
    # log.logger.debug(cd_hit_command)
    # os.system(cd_hit_command)
    #
    #
    # # --------------------------------------------------------------------------------------
    # # Step5. merge with LTR_retriever
    # merge_pure = tmp_output_dir + '/repeats.merge.fa'
    # merge_pure_consensus = tmp_output_dir + '/repeats.merge.consensus.fa'
    # os.system('cat ' + cut_repeats_consensus + ' > ' + merge_pure)
    # ltr_retriever_seq = tmp_output_dir + '/' + ref_filename + '.mod.LTRlib.fa'
    # backjob.join()
    # os.system('cat ' + ltr_retriever_seq + ' >> ' + merge_pure)
    # #cd_hit_command = tools_dir + '/cd-hit-est -s ' + str(length_similarity_cutoff) + ' -c ' + str(identity_threshold) + ' -i ' + merge_pure + ' -o ' + merge_pure_consensus + ' -T 0 -M 0'
    # cd_hit_command = tools_dir + '/cd-hit-est -aS ' + str(length_similarity_cutoff) + ' -c ' + str(identity_threshold) + ' -i ' + merge_pure + ' -o ' + merge_pure_consensus + ' -T 0 -M 0'
    # log.logger.debug(cd_hit_command)
    # os.system(cd_hit_command)
    #
    # # --------------------------------------------------------------------------------------
    # # Step6. filter low_complexity and tandem
    # # script_path = tools_dir + '/filter-stage-1.prl'
    # # filter_repeats_path = tmp_output_dir + '/repeats-filtered.fa'
    # # filter_command = 'cat ' + merge_pure_consensus + ' | ' + script_path + ' > ' + filter_repeats_path
    # # os.system(filter_command)
    #
    # # >= tandem_region_cutoff region of the whole repeat region, then it should be filtered, since maybe false positive
    # # keep sequences >= 50bp
    # TRF_Path = param['TRF_Path']
    #
    # trf_dir = tmp_output_dir + '/trf_temp'
    # if not os.path.exists(trf_dir):
    #     os.makedirs(trf_dir)
    # (repeat_dir, repeat_filename) = os.path.split(merge_pure_consensus)
    # (repeat_name, repeat_extension) = os.path.splitext(repeat_filename)
    # trf_command = 'cd ' + trf_dir + ' && ' + TRF_Path + ' ' + merge_pure_consensus + ' 2 7 7 80 10 50 500 -f -d -m'
    # log.logger.debug(trf_command)
    # os.system(trf_command)
    # trf_masked_repeats = trf_dir + '/' + repeat_filename + '.2.7.7.80.10.50.500.mask'
    #
    # trf_contigNames, trf_contigs = read_fasta(trf_masked_repeats)
    # repeats_contigNames, repeats_contigs = read_fasta(merge_pure_consensus)
    # filter_repeats_path = tmp_output_dir + '/repeats-filtered.fa'
    # with open(filter_repeats_path, 'w') as f_save:
    #     for name in trf_contigNames:
    #         seq = trf_contigs[name]
    #         if float(seq.count('N')) / len(seq) < tandem_region_cutoff and len(seq) >= 50:
    #             f_save.write('>' + name + '\n' + repeats_contigs[name] + '\n')
    #
    # # --------------------------------------------------------------------------------------
    # # Step7. run TE classification to classify TE family
    # starttime = time.time()
    # log.logger.debug('Start step8: get classified consensus sequence')
    # sample_name = alias
    # TEClass_home = os.getcwd() + '/classification'
    # TEClass_command = 'cd ' + TEClass_home + ' && python ' + TEClass_home + '/TEClass_parallel.py --sample_name ' + sample_name \
    #                   + ' --consensus ' + filter_repeats_path + ' --genome ' + reference \
    #                   + ' --thread_num ' + str(threads) + ' -o ' + tmp_output_dir
    # log.logger.debug(TEClass_command)
    # os.system(TEClass_command)
    #
    # # --------------------------------------------------------------------------------------
    # # Step11. assign a family name for each classified TE consensus
    # classified_consensus_path = filter_repeats_path + '.final.classified'
    # classified_contigNames, classified_contigs = read_fasta(classified_consensus_path)
    # sorted_classified_contigs = {k: v for k, v in sorted(classified_contigs.items(), key=lambda item: -len(item[1]))}
    # family_path = tmp_output_dir + '/family_' + sample_name + '.fasta'
    # with open(family_path, 'w') as f_save:
    #     for f_id, name in enumerate(sorted_classified_contigs.keys()):
    #         sequence = sorted_classified_contigs[name]
    #         class_name = name.split('#')[1]
    #         # if len(sequence) < 80 and class_name == 'Unknown':
    #         #     continue
    #         f_save.write('>family-' + str(f_id) + '#' + class_name + '\n' + sequence + '\n')
    # endtime = time.time()
    # dtime = endtime - starttime
    # log.logger.debug("module8: get classified consensus sequence running time: %.8s s" % (dtime))
    #
    # pipeline_endtime = time.time()
    # pipeline_dtime = pipeline_endtime - pipeline_starttime
    # log.logger.debug("Total pipeline running time (no including RepeatMasker): %.8s s" % (pipeline_dtime))
    #
    # # --------------------------------------------------------------------------------------
    # # Step12. invoke RepeatMasker to align TE family to genome
    # starttime = time.time()
    # RepeatMasker_Home = param['RepeatMasker_Home']
    # RepeatMasker_output_dir = tmp_output_dir + '/' + sample_name
    # RepeatMasker_command = 'cd ' + tmp_output_dir + ' && ' + RepeatMasker_Home + '/RepeatMasker -parallel ' + str(threads) \
    #                        + ' -lib ' + family_path + ' -nolow -x -html -gff -dir ' + RepeatMasker_output_dir + ' ' + reference
    # os.system('rm -rf ' + RepeatMasker_output_dir)
    # log.logger.debug(RepeatMasker_command)
    # os.system(RepeatMasker_command)
    # endtime = time.time()
    # dtime = endtime - starttime
    # log.logger.debug("module9: invoke RepeatMasker to annotate genome running time: %.8s s" % (dtime))





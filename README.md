# HiTE, a progressive Method for High-Precision Transposable Element Annotation
[![GitHub](https://img.shields.io/badge/python-3-blue)](https://www.python.org/)
[![GitHub](https://img.shields.io/badge/license-GPL--3.0-green)](https://github.com/CSU-KangHu/HiTE/blob/master/LICENSE)

## Table of Contents
- [Installation](#install)
  - [Run with Singularity](#install_singularity)
  - [Run with Docker](#install_docker)
  - [Run with Conda](#install_conda)
  - [Run with nextflow](#install_nextflow)
  <!-- - [Step-by-step installation](#step-step) -->
- [Quick start](#start)
- [Usage](#cmd)
- [Input](#inputs)
- [Output](#outputs)
- [Replace the Dfam library in RepeatMasker](#classified)
- [More tutorials](#QA)

## <a name="install"></a>Installation
### Recommended Hardware requirements
40 CPU processors, 128 GB RAM. 


### Dowload project
```sh
git clone https://github.com/CSU-KangHu/HiTE.git
```

### <a name="install_singularity"></a>Option 1. Run with Singularity (recommended)
```sh
# pull singularity image (once for all). There will be a HiTE.sif file.
singularity pull HiTE.sif docker://kanghu/hite:2.0.4

# run HiTE
singularity run -B ${host_path}:${container_path} --pwd /HiTE HiTE.sif python main.py \
 --genome ${genome} \
 --thread ${thread} \
 --outdir ${output_dir} \
 [other parameters]
 
 #e.g., my command: singularity run -B /home/hukang:/home/hukang --pwd /HiTE HiTE.sif python main.py 
 # --genome /home/hukang/HiTE/demo/genome.fa 
 # --thread 40 
 # --outdir /home/hukang/HiTE/demo/test/
```

### <a name="install_docker"></a>Option 2. Run with Docker
```sh
# pull docker image (once for all).
docker pull docker://kanghu/hite:2.0.4

# run HiTE
docker run -v ${host_path}:${container_path} kanghu/hite:2.0.4 python main.py \
 --genome ${genome} \
 --thread ${thread} \
 --outdir ${output_dir} \
 [other parameters]
 
 #e.g., my command: docker run -v /home/hukang:/home/hukang kanghu/hite:2.0.4 python main.py 
 # --genome /home/hukang/HiTE/demo/genome.fa 
 # --thread 40 
 # --outdir /home/hukang/HiTE/demo/test/
```

### <a name="install_conda"></a>Option 3. Run with conda
```sh
# Find the **yml** file in the project directory and run
cd HiTE
conda env create --name HiTE -f environment.yml
conda activate HiTE

# run HiTE
python main.py \
 --genome ${genome} \
 --thread ${thread} \
 --outdir ${output_dir} \
 [other parameters]
 
  #e.g., my command: python main.py 
 # --genome /home/hukang/HiTE/demo/genome.fa 
 # --thread 40 
 # --outdir /home/hukang/HiTE/demo/test/
```

#### Updating the Dfam library in RepeatMasker (optional)
* HiTE is ready to go!
* use `--classified 0` if you do not need classified TE models.
* If you require the TE library to be **comprehensively classified**, you need to configure RepeatMasker with the complete Dfam library.
[The simplest way to update the Dfam library](#classified)
* If you installed HiTE with Singularity or Docker, you can skip this step.

### <a name="install_nextflow"></a>Option 4. Run with nextflow
Nextflow is built on top of the popular programming language, Groovy, and supports the execution of workflows 
on a wide range of computing environments, including **local machines, clusters, cloud platforms, and HPC** systems.
It also provides advanced features such as **data provenance tracking, automatic parallelization, error handling**, 
and support for containerization technologies like **Docker** and **Singularity**.

We provide a [tutorial](https://github.com/CSU-KangHu/HiTE/wiki/Run-HiTE-with-Nextflow) on how to run HiTE with nextflow.

<!--
### <a name="step-step"></a>Option 4. Step-by-step installation
#### 1. Download project 
```
git clone https://github.com/CSU-KangHu/HiTE.git
```

#### 2. installing python3
HiTE requires python3, please ensure you run HiTE with python3.

#### 3. installing RMBlast
Please install  [RMBlast](https://www.repeatmasker.org/rmblast/).

#### <a name="genome_tools"></a>4. Installing genome tools
Download [Genome Tools](http://genometools.org/pub/binary_distributions/).

#### <a name="ltrretriever"></a>5. Installing LTR_retriever
Install the latest release of LTR_retriever
from the [LTR_retriever Github page](https://github.com/oushujun/LTR_retriever).

#### <a name="repeatmodeler"></a>6. Installing RepeatMasker and RepeatModeler2 (Optional)
It is recommended to download the [RepeatMasker](http://www.repeatmasker.org/RepeatMasker/) with the complete Dfam 3.6 library.

HiTE uses RepeatClassifier from [RepeatModeler2](https://www.repeatmasker.org/RepeatModeler/) to classify the TE models. 
Please follow the documentation to install RepeatModeler2 and configure RepeatMasker.

If you do not need classified TE models, you can skip this step and run HiTE with `--classified 0`.

#### <a name="configure"></a>7. Configuring dependencies
```
cd /your_path_to/HiTE
vim ParamConfig.json
```
Change
- Genome_Tools_Home
- LTR_retriever_Home
- RMBlast_Home
- RepeatModeler_Home

to the actual installation directories of RepeatMasker, Genome_Tools, LTR_retriever, and RMBlast, respectively.

Then, run

```
cd /your_path_to/HiTE
python configure.py
```
to validate all configurations.
-->

## <a name="start"></a>Quick start (Conda mode)
```
conda activate HiTE
cd /your_path_to/HiTE
python main.py --genome ./demo/genome.fa --thread 48 --outdir ./demo/test
```

If the following files exist in the **demo/test** directory, it means the program runs successfully: 
```text
demo/test/
├── confident_helitron.fa (1.4K)
├── confident_other.fa (14K)
├── confident_tir.fa (34K)
├── confident_ltr_cut.fa (47K)
├── confident_TE.cons.fa (92K)
└── confident_TE.cons.fa.classified (93K)
```

Note:
1. Please make sure you execute the **main.py** script under the **/your_path_to/HiTE** directory.
2. To avoid automatic deletion of files, set the output path parameter ```--outdir``` to an empty directory.

### Predicting conserved protein domains in TEs
To predict conserved protein domains in TEs, you need to add `--domain 1` parameter.

The output file is **confident_TE.cons.fa.domain**, which is shown as follows:
```sh
TE_name domain_name     TE_start        TE_end  domain_start    domain_end

N_111   Gypsy-50_SB_1p#LTR/Gypsy        164     4387    1       1410
...
```

## <a name="inputs"></a>Inputs
HiTE works with genome assemblies in **fasta**, **fa**, and **fna** formats using parameter `--genome`.


For other optional parameters, please refer to [Usage](#cmd).

## <a name="outputs"></a>Outputs
HiTE outputs many temporary files, which allow you to quickly restore the previous 
running state in case of any interruption during the running process. If
the pipeline completes successfully, the output directory should look like the following:
```shell
output_dir/
├── longest_repeats_*.fa
├── longest_repeats_*.flanked.fa
├── confident_tir_*.fa
├── confident_helitron_*.fa
├── confident_other_*.fa
├── confident_ltr_cut.fa
├── confident_TE.cons.fa
├── confident_TE.cons.fa.classified
├── HiTE.out (require `--annotate 1`)
├── HiTE.gff (require `--annotate 1`)
└── HiTE.tbl (require `--annotate 1`)
```

1. **confident_TE.cons.fa** and **confident_TE.cons.fa.classified** are the 
unclassified and classified TE libraries generated by HiTE, respectively.
2. **confident_TE.cons.fa.classified** can be used directly as TE library in RepeatMasker by `-lib`.
3. It is worth noting that **confident_TE.cons.fa.classified** is generated by RepeatClassifier from 
RepeatModeler2, which depends on the Dfam library in RepeatMasker.
4. Note that "*" represents the number of blocks that the genome is divided into.
For example, if the genome input is 400 MB and the chunk size input is set to 100,
then * is equal to 4 (400/100), and you can find 4 files: repeats_0.fa, repeats_1.fa,
repeats_2.fa, and repeats_3.fa in your output directory.
5. The **HiTE.out**, **HiTE.gff**, and **HiTE.tbl** files are generated using parameter `--annotate 1`. 
The **HiTE.out** and **HiTE.gff**, function as genome annotation files, with **HiTE.gff** being visualizable 
in the IGV (Integrative Genomics Viewer). Additionally, **HiTE.tbl** offers statistical information 
on the proportion of each transposon type within the genome.


## <a name="classified"></a>Replace the Dfam library in RepeatMasker (Only for Conda)
Since the Dfam library included in RepeatMasker by default is not complete, it will seriously affect the classification effect.
We recommend updating RepeatMasker with the complete Dfam 3.6 library as described at http://www.repeatmasker.org/RepeatMasker/, including download, unpack, and reconfiguration.
We also provide an optional method to avoid the big Dfam.h5.gz (15 GB) download and reconfiguration, as follows:
1. download **RepeatMasker_Lib.zip** from [google drive](https://drive.google.com/file/d/1vQLamfINdJ5iDwggYigWKe7Gor4t6JMK/view?usp=sharing) or [github](https://github.com/CSU-KangHu/TE_annotation):

2. upload **RepeatMasker_Lib.zip** to RepeatMasker/Libraries, where RepeatMasker is your installation directory of RepeatMasker.
   (e.g., ~/anaconda2/envs/HiTE/share/RepeatMasker)

3. `cd RepeatMasker/Libraries`

4. `unzip RepeatMasker_Lib.zip && mv RepeatMasker_Lib/* ./`


## <a name="cmd"></a>Usage
Type `python main.py -h` for help.
```
The simplest command:
python main.py --genome $genome_assembly --outdir $output_dir

Most frequently used commands:
python main.py --genome $genome_assembly --outdir $output_dir --thread 40 --chunk_size 400 --plant 0 --recover 1 --annotate 1

usage: main.py [-h] [--genome genome] [--thread thread_num]
               [--chunk_size chunk_size] [--miu miu] [--plant is_plant]
               [--classified is_classified] [--remove_nested is_remove_nested]
               [--domain is_domain] [--recover is_recover]
               [--annotate is_annotate] [--debug is_debug]
               [--outdir output_dir] [--flanking_len flanking_len]
               [--fixed_extend_base_threshold fixed_extend_base_threshold]
               [--tandem_region_cutoff tandem_region_cutoff]
               [--max_repeat_len max_repeat_len]
               [--chrom_seg_length chrom_seg_length]

########################## HiTE, version 2.0.4 ##########################

optional arguments:
  -h, --help            show this help message and exit
  --genome genome       Input genome assembly path
  --thread thread_num   Input thread num, default = [ 40 ]
  --chunk_size chunk_size
                        The chunk size of large genome, default = [ 400 MB ]
  --miu miu             The neutral mutation rate (per bp per ya), default = [1.3e-08 ]
  --plant is_plant      Is it a plant genome, 1: true, 0: false. default = [ 1 ]
  --classified is_classified
                        Whether to classify TE models, HiTE uses
                        RepeatClassifier from RepeatModeler to classify TEs,
                        1: true, 0: false. default = [ 1 ]
  --remove_nested is_remove_nested
                        Whether to remove nested TE, 1: true, 0: false. default = [ 1 ]
  --domain is_domain    Whether to obtain TE domains, HiTE uses RepeatPeps.lib
                        from RepeatMasker to obtain TE domains, 1: true, 0:
                        false. default = [ 0 ]
  --recover is_recover  Whether to enable recovery mode to avoid starting from
                        the beginning, 1: true, 0: false. default = [ 0 ]
  --annotate is_annotate
                        Whether to annotate the genome using the TE library
                        generated, 1: true, 0: false. default = [ 0 ]
  --debug is_debug      Open debug mode, and temporary files will be kept, 1:
                        true, 0: false. default = [ 0 ]
  --outdir output_dir   The path of output directory; It is recommended to use
                        an empty directory to avoid automatic deletion of
                        important files.
  --flanking_len flanking_len
                        The flanking length of candidates to find the true
                        boundaries, default = [ 50 ]
  --fixed_extend_base_threshold fixed_extend_base_threshold
                        The length of variation can be tolerated during
                        pairwise alignment, default = [ 1000 ]
  --tandem_region_cutoff tandem_region_cutoff
                        Cutoff of the candidates regarded as tandem region,
                        default = [ 0.5 ]
  --max_repeat_len max_repeat_len
                        The maximum length of a single repeat, default = [ 30000 ]
  --chrom_seg_length chrom_seg_length
                        The length of genome segments, default = [ 100000 ]
```

## <a name="QA"></a>More tutorials
You may want to check out this [Wiki](https://github.com/CSU-KangHu/HiTE/wiki) page for more tutorials.
* [Issues with installation and usage](https://github.com/CSU-KangHu/HiTE/wiki/Issues-with-installation-and-usage)
* [How to make HiTE into a Docker image](https://github.com/CSU-KangHu/HiTE/wiki/How-to-make-HiTE-into-a-Docker-image)
* [Run HiTE with Nextflow](https://github.com/CSU-KangHu/HiTE/wiki/Run-HiTE-with-Nextflow)
* [Experiment reproduction](https://github.com/CSU-KangHu/HiTE/wiki/Experiment-reproduction)

from collections import OrderedDict
import subprocess as sp
import os
from pathlib import Path
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext, ugettext_lazy as _

from .models import RNASeqModel
from analyses.tasks import cd
from analyses.models import ExecutionStatus, StageStatus

FASTQC_BIN = str(Path('~/miniconda3/envs/rnaseq/bin/fastqc').expanduser())
STAR_BIN = str(Path('~/miniconda3/envs/rnaseq/bin/STAR').expanduser())
SAMTOOLS_BIN = str(Path('~/miniconda3/envs/rnaseq/bin/samtools').expanduser())
CUFFLINKS_BIN = str(Path('~/miniconda3/envs/rnaseq/bin/cufflinks').expanduser())
CUFFMERGE_BIN = str(Path('~/miniconda3/envs/rnaseq/bin/cuffmerge').expanduser())
CUFFQUANT_BIN = str(Path('~/miniconda3/envs/rnaseq/bin/cuffquant').expanduser())
CUFFDIFF_BIN = str(Path('~/miniconda3/envs/rnaseq/bin/cuffdiff').expanduser())


def update_stage(job_detail, stage_name, new_status):
    setattr(job_detail, stage_name, new_status.name)
    job_detail.save(update_fields=[stage_name])


def run_fastqc(job: RNASeqModel, analysis_info):
    # Ensure java is available, update the PATH environment variable here
    env = os.environ.copy()
    env['PATH'] = str(Path('~/miniconda3/envs/rnaseq/bin').expanduser()) + ':' + env['PATH']

    data_sources = analysis_info['data_sources']
    with cd(str(job.result_dir)):
        for ds in data_sources:
            ds_pth, ds_info = next(iter(ds.items()))
            ds_pth = Path(ds_pth)
            ds_dir = Path('fastqc/{}'.format(ds_pth.stem))
            if not ds_dir.exists():
                ds_dir.mkdir()
            # Run FastQC
            p = sp.run([
                FASTQC_BIN,
                '-o', str(ds_dir),
                str(ds_pth)
            ], env=env)
            if p.returncode:
                return p.returncode
    return 0


def run_star(job: RNASeqModel, analysis_info, data_source_mapping):
    # Get genome annotation
    genome_root = job.genome_reference.full_dir_path
    genes_gtf = genome_root.joinpath('genes.gtf')
    sjdb_out = genome_root.joinpath('sjdbList.out.tab')
    # Iterate each sample under all conditions
    for condition in analysis_info['conditions']:
        cond, samples = next(iter(condition.items()))
        for sample in samples:
            sample_name, fastqs = next(iter(sample.items()))
            fastq_full_pths = [
                data_source_mapping[fastq]['path']
                for fastq in fastqs
            ]
            sample_dir = job.result_dir.joinpath('STAR', sample_name)
            if not sample_dir.exists():
                sample_dir.mkdir()
            with cd(str(job.result_dir)):
                # Run STAR
                p = sp.run([
                    STAR_BIN,
                    '--genomeDir', str(genome_root),
                    '--sjdbOverhang', '100',
                    '--sjdbGTFfile', str(genes_gtf),
                    '--sjdbFileChrStartEnd', str(sjdb_out),
                    '--readFilesIn', *fastq_full_pths,
                    '--runThreadN', '4',
                    '--outSAMstrandField', 'intronMotif',
                    '--outFilterIntronMotifs', 'RemoveNoncanonical',
                    '--outSAMtype', 'BAM', 'SortedByCoordinate',
                    '--outFileNamePrefix', str(sample_dir) + '/',
                ])
                if p.returncode:
                    return p.returncode

                # Run samtools index
                for fastq_pth in fastq_full_pths:
                    sp.run([SAMTOOLS_BIN, 'index', fastq_pth])
    return 0


def run_cufflinks(job: RNASeqModel, analysis_info):
    # Get genome annotation
    genome_root = job.genome_reference.full_dir_path
    genes_gtf = genome_root.joinpath('genes.gtf')

    # Get all samples
    sample_names = []
    for condition in analysis_info['conditions']:
        cond, samples = next(iter(condition.items()))
        for sample in samples:
            sample_name, _ = next(iter(sample.items()))
            sample_names.append(sample_name)

    for sample_name in sample_names:
        sample_dir = job.result_dir.joinpath('cufflinks', sample_name)
        sample_bam = job.result_dir.joinpath('STAR', sample_name, 'Aligned.sortedByCoord.out.bam')
        if not sample_dir.exists():
            sample_dir.mkdir()
        with cd(str(job.result_dir)):
            # Run Cufflinks
            p = sp.run([
                CUFFLINKS_BIN,
                '-p', '4',
                '-o', str(sample_dir),
                '--library-type', 'fr-firststrand',
                '--GTF', str(genes_gtf),
                '--no-update-check',
                str(sample_bam)
            ])
            if p.returncode:
                return p.returncode
    return 0


def run_cuffdiff(job: RNASeqModel, analysis_info):
    # Get genome annotation
    genome_root = job.genome_reference.full_dir_path
    genes_gtf = genome_root.joinpath('genes.gtf')
    genome_fa = genome_root.joinpath('genome.fa')

    # Get all samples and conditions
    sample_names = []
    conditions = OrderedDict()
    for condition in analysis_info['conditions']:
        cond, samples = next(iter(condition.items()))
        conditions[cond] = []
        for sample in samples:
            sample_name, _ = next(iter(sample.items()))
            sample_names.append(sample_name)
            conditions[cond].append(sample_name)

    # Result folders
    cuffmerge_dir = job.result_dir.joinpath('cuffmerge')
    cuffquant_dir = job.result_dir.joinpath('cuffquant')
    cuffdiff_dir = job.result_dir.joinpath('cuffdiff')

    # Since Cufflinks-related tools call external command,
    # update the PATH environment variable here
    env = os.environ.copy()
    env['PATH'] = (
        str(Path('~/miniconda3/envs/rnaseq/bin').expanduser()) +
        ':/usr/bin:' +  # Fix cuffmerge require /usr/bin/sort command
        env['PATH']
    )

    # Cuffmerge
    # generate the gtf list
    merged_gtf = cuffmerge_dir.joinpath('assembly_GTF_list.txt')
    with merged_gtf.open('w') as out:
        for sample_name in sample_names:
            print(
                str(job.result_dir.joinpath('cufflinks', sample_name, 'transcripts.gtf')),
                file=out
            )
    # Run Cuffmerge
    with cd(str(job.result_dir)):
        sp.run([
            CUFFMERGE_BIN,
            '-p', '4',
            '-o', str(cuffmerge_dir),
            '-g', str(genes_gtf),
            '-s', str(genome_fa),
            str(merged_gtf),
        ], env=env)

    # Run Cuffquant
    cuffmerge_merged_gtf = cuffmerge_dir.joinpath('merged.gtf')
    with cd(str(job.result_dir)):
        for sample_name in sample_names:
            sample_dir = cuffquant_dir.joinpath(sample_name)
            sample_bam = job.result_dir.joinpath('STAR', sample_name, 'Aligned.sortedByCoord.out.bam')
            if not sample_dir.exists():
                sample_dir.mkdir()
            sp.run([
                CUFFQUANT_BIN,
                '-p', '4',
                '--library-type', 'fr-firststrand',
                '--no-update-check',
                '-o', str(sample_dir),
                str(cuffmerge_merged_gtf),
                str(sample_bam)
            ], env=env)

    # Run Cuffdiff
    # TODO: support more than 2 conditions
    labels = ','.join(conditions.keys())
    samples_per_condition = [
        ','.join(
            str(cuffquant_dir.joinpath(sample_name, 'abundances.cxb'))
            for sample_name in sample_names
        )
        for cond, sample_names in conditions.items()
    ]
    with cd(str(job.result_dir)):
        sp.run([
            CUFFDIFF_BIN,
            '-p', '4',
            '-L', labels,
            '-o', str(cuffdiff_dir),
            '--library-type', 'fr-firststrand',
            '--no-update-check',
            str(cuffmerge_merged_gtf),
            *samples_per_condition,
        ], env=env)
    return 0


def run_pipeline(job_pk, job_url):
    job = RNASeqModel.objects.get(pk=job_pk)
    job_detail = job.execution_detail
    job.execution_status = ExecutionStatus.RUNNING.name
    job.save()
    analysis_info = job.generate_analysis_info()

    # Create a data_source mapping from its name so each stage can re-use this
    data_source_mapping = {}
    for data_source in analysis_info['data_sources']:
        ds_pth, ds_info = next(iter(data_source.items()))
        data_source_mapping[Path(ds_pth).name] = ds_info

    # Stage QC:
    fastqc_dir = job.result_dir.joinpath('fastqc')
    if not fastqc_dir.exists():
        fastqc_dir.mkdir()
    if job.quality_check:
        update_stage(job_detail, 'stage_qc', StageStatus.RUNNING)
        returncode = run_fastqc(job, analysis_info)
        if returncode:
            update_stage(job_detail, 'stage_qc', StageStatus.FAILED)
            # TODO: short circuit failure and notification
            # End the pipeline now and notify user about why
        else:
            update_stage(job_detail, 'stage_qc', StageStatus.SUCCESSFUL)
    else:
        update_stage(job_detail, 'stage_qc', StageStatus.SKIPED)

    # Stage Alignment:
    update_stage(job_detail, 'stage_alignment', StageStatus.RUNNING)
    if job.genome_aligner.startswith('STAR'):
        # STAR
        star_dir = job.result_dir.joinpath('STAR')
        if not star_dir.exists():
            star_dir.mkdir()
        returncode = run_star(job, analysis_info, data_source_mapping)
        if returncode:
            update_stage(job_detail, 'stage_alignment', StageStatus.FAILED)
        else:
            update_stage(job_detail, 'stage_alignment', StageStatus.SUCCESSFUL)
    else:
        # Tophat
        update_stage(job_detail, 'stage_alignment', StageStatus.FAILED)

    # Stage Cufflinks:
    update_stage(job_detail, 'stage_cufflinks', StageStatus.RUNNING)
    cufflinks_dir = job.result_dir.joinpath('cufflinks')
    if not cufflinks_dir.exists():
        cufflinks_dir.mkdir()
    returncode = run_cufflinks(job, analysis_info)
    if returncode:
        update_stage(job_detail, 'stage_cufflinks', StageStatus.FAILED)
    else:
        update_stage(job_detail, 'stage_cufflinks', StageStatus.SUCCESSFUL)

    # Stage Cuffdiff:
    update_stage(job_detail, 'stage_cuffdiff', StageStatus.RUNNING)
    cuffmerge_dir = job.result_dir.joinpath('cuffmerge')
    cuffquant_dir = job.result_dir.joinpath('cuffquant')
    cuffdiff_dir = job.result_dir.joinpath('cuffdiff')
    for cuff_dir in [cuffmerge_dir, cuffquant_dir, cuffdiff_dir]:
        if not cuff_dir.exists():
            cuff_dir.mkdir()
    returncode = run_cuffdiff(job, analysis_info)
    if returncode:
        update_stage(job_detail, 'stage_cuffdiff', StageStatus.FAILED)
    else:
        update_stage(job_detail, 'stage_cuffdiff', StageStatus.SUCCESSFUL)

    # generating report
    job_report = job.report
    # TODO: check if report is successfully generated
    sp.run([
        'bc_report',
        '-p', 'bc_pipelines.rna_seq.report.RNASeqReport',
        str(job.result_dir),
        str(job_report.full_path)
    ])

    # pipeline ends
    job.date_finished = timezone.now()
    job.execution_status = ExecutionStatus.SUCCESSFUL.name
    job.save()

    # sending notification email
    user = job.owner
    context = {
        'user': user,
        'job_url': job_url,
        'job': job,
        'type': job._meta.verbose_name,
        'name': job.name,
        'status': job.execution_status,
    }
    message = render_to_string(
        'rna_seq/analysis_complete_email.txt', context,
    )
    send_mail(
        ugettext(
            '[BioCloud] {type}: {name} has been complete ({status})'
            .format(**context)
        ),
        message,
        None,           # sender
        [user.email]    # receiver
    )

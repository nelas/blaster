#!/usr/bin/python
# -*- coding: utf-8 -*-

'''BLASTing batch script.

Algorithm:
    - Take several genes of interest.
    - BLAST them locally against a transcriptome assembly.
    - Filter and process results to extract relevant sequences.

Notes:
    - Read files with sequences from a folder (FASTA format).

Dependencies:
    - Python 2.7.1
    - Biopython 1.56
    - BLAST+ 2.2.25

Configuration (Linux):
    - Regular packages for Python and Biopython.
    - Add BLAST+ commands to path putting this code to .bashrc:

        PATH=$PATH:/home/nelas/Downloads/ncbi-blast-2.2.25+/bin
        export PATH

'''

import getopt
import logging
import os
import subprocess
import sys

from Bio import SeqIO
from Bio.Blast import NCBIWWW
from Bio.Blast import NCBIXML
from liblast import Sequence, Locus, blast

def prepare(candidates, candidates_folder):
    '''Check candidate gene files (convert to FASTA, if needed).'''
    for gene in candidates:
        gene_filepath = os.path.join(candidates_folder, gene)

        if gene.endswith('.gb'):
            # Create record object.
            record = SeqIO.read(gene_filepath, 'genbank')
            # Create FASTA file.
            try:
                fasta_file = open(gene_filepath.split('.')[0] + '.fasta', 'r')
            except IOError:
                fasta_file = open(gene_filepath.split('.')[0] + '.fasta', 'w')
                fasta_file.write(record.format('fasta'))
                fasta_file.close()
        elif gene.endswith('.fa'):
            continue
        else:
            logger.debug('File type not supported: %s', gene)

def usage():
    '''Explanation for arguments.'''

    print
    print 'USAGE: ./blaster.py -d Membranipora.fasta -b tblastn'
    print '  -c, --candidates \n\tFolder with `.fasta` or `.gb` files of candidate genes. One gene per file.'
    print '  -d, --database \n\tLocal database with new data (eg, transcriptome).'
    print '  -r, --results \n\tFolder where BLAST results will be written.'
    print '  -b, --blast \n\tBLAST command (blastn, blastp, blastx, tblastn, tblastx).'
    print

def main(argv):

    # Available BLASTs.
    blast_types = ['blastn', 'blastp', 'blastx', 'tblastn', 'tblastx']
    # Database name.
    database = None
    # BLAST command.
    blast_type = None

    # Folder with candidate-genes.
    candidates_folder = 'candidates'
    # Folder with candidate-genes BLASTs.
    candidates_results_folder = os.path.join(candidates_folder, 'results')

    # Folder with final results.
    final_results_folder = 'final_results'

    # Parse arguments.
    try:
        opts, args = getopt.getopt(argv, 'hc:d:b:', [
            'help',
            'candidates=',
            'database=',
            'blast=',
            ])
    except getopt.GetoptError:
        usage()
        logger.critical('Argument error: "%s". Aborting...',
                ' '.join(argv))
        sys.exit(2)

    # Argument handler.
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit()
        elif opt in ('-c', '--candidates'):
            candidates_folder = arg
        elif opt in ('-d', '--database'):
            database = arg
        elif opt in ('-b', '--blast'):
            blast_type = arg

    # Print summary of arguments.
    logger.debug('Arguments: candidates=%s, database=%s, blast=%s', candidates_folder, database, blast_type)


    # Check if BLAST command was specified.
    if not blast_type:
        logger.critical('BLAST command was not specified (use "-b"). Aborting...')
        sys.exit(2)
    else:
        if not blast_type in blast_types:
            logger.critical('Unknown BLAST command: %s', blast_type)
            logger.info('Available BLAST commands: %s', ', '.join(blast_types))
            sys.exit(2)

    # Check if results exists.
    if not os.path.isdir(candidates_results_folder):
        os.mkdir(candidates_results_folder)
    # Check if final results exists.
    if not os.path.isdir(final_results_folder):
        os.mkdir(final_results_folder)

    # Get candidate genes.
    try:
        candidates = os.listdir(candidates_folder)
    except OSError:
        logger.critical('Folder "%s" does not exist! Aborting...', candidates_folder)
        sys.exit(2)

    # Process candidate genes.
    prepare(candidates, candidates_folder)
    # Get proper genes, now.
    candidates = os.listdir(candidates_folder)
    # Only read FASTA files.
    candidates = [file for file in candidates if file.endswith('.fa')]

    # Print info before starting.
    logger.info('%d genes to be BLASTed against %s database!', len(candidates),
            database)


    # Main object to store genes.
    genes = {}

    # BLAST each gene against local database.
    for genefile in candidates:
        print
        logger.info('BLASTing %s against %s...', genefile, database)

        # Instantiate Sequence.
        gene_filepath = os.path.join(candidates_folder, genefile)
        candidate = Sequence(filepath=gene_filepath, database=database)

        # Define variables.
        output_filepath = os.path.join(candidates_results_folder, '%s.xml' % candidate.gene_name)
        candidate.blast_output = output_filepath

        # Only BLAST if needed.
        try:
            blastfile = open(candidate.blast_output)
            blastfile.close()
        except:
            arguments = {
                'query': candidate.filepath,
                'db': database,
                'out': candidate.blast_output,
                'outfmt': 5, # Export in XML
                }
            # Execute BLAST command.
            blast(blast_type, arguments)

        logger.info('Parsing XML...')
        candidate.blast_type = blast_type
        candidate.parse_blast()

        # Add to main dictionary.
        genes[candidate.gene_name] = candidate


    # Print loci equivalent to candidate genes.
    logger.info('Creating files at %s...', final_results_folder)
    for name, gene in genes.iteritems():
        final_file = open(os.path.join(final_results_folder, '%s.fa' % name), 'w')
        for seq in gene.loci:
            final_file.write('>%s\n' % seq.id)
            final_file.write('%s\n\n' % seq.sequence)
        final_file.close()

    logger.info('Done, bye!')


if __name__ == '__main__':
    # Create logger.
    logger = logging.getLogger('blaster')
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    # Define message format.
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s @ %(module)s %(funcName)s (l%(lineno)d): %(message)s')

    # Create logger console handler.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    # Format console output.
    console_handler.setFormatter(formatter)
    # Add console to logger.
    logger.addHandler(console_handler)

    # Create logger file handler.
    file_handler = logging.FileHandler('log_blaster.log')
    file_handler.setLevel(logging.DEBUG)
    # Format file output.
    file_handler.setFormatter(formatter)
    # Add file to logger.
    logger.addHandler(file_handler)

    # Initiates main function.
    logger.info('BLASTer is running...')
    main(sys.argv[1:])

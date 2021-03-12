#Author: Gracie Gordon 2019
#merge tables

import sys
import pandas as pd
import numpy as np

import math
import pickle

from Bio import SeqIO

import click


# options
@click.command()
@click.option('--counts',
              'counts_file',
              required=True,
              type=click.Path(exists=True, readable=True),
              help='Merged DNA and RNA counts.')
@click.option('--assignment',
              'assignment_file',
              required=True,
              type=click.Path(exists=True, readable=True),
              help='Assignment file in tsv format.')
@click.option('--minRNACounts',
              'minRNACounts',
              default=1,
              show_default=True,
              type=int,
              help='Minimum number of RNA counts required per barcode. If 0 pesudocounts are used.')
@click.option('--minDNACounts',
              'minDNACounts',
              default=0,
              show_default=True,
              type=int,
              help='Minimum number of DNA counts required per barcode. If 0 pesudocounts are used.')
@click.option('--output',
              'output_file',
              required=True,
              type=click.Path(writable=True),
              help='Output file.')
@click.option('--statistic',
              'statistic_file',
              required=True,
              type=click.Path(writable=True),
              help='Statistic output file.')
def cli(counts_file, assignment_file, minRNACounts, minDNACounts, output_file, statistic_file):
    # pseudocount = 1 if minRNACounts == 0 or minDNACounts == 0 else 0
    pseudocountDNA = 1 if minDNACounts == 0 else 0
    pseudocountRNA = 1 if minRNACounts == 0 else 0

    # statistic
    statistic = pd.DataFrame(data={'oligos design': [0], 'barcodes design' : [0],
                    'oligos dna/rna' : [0],  'barcodes dna/rna' : [0],
                    'matched barcodes' : [0], 'unknown barcodes dna/rna' : [0],
                    '% matched barcodes' : [0.0],
                    'total dna counts' : [0], 'total rna counts' : [0],
                    'avg dna counts per bc' : [0.0], 'avg rna counts per bc' : [0.0],
                    'avg dna/rna barcodes per oligo' : [0.0]})

    # process fastq
    click.echo("Read assignment file...")
    assoc = pd.read_csv(assignment_file, header=None, usecols=[0,1], sep="\t", names=['Barcode','Oligo'])
    assoc.set_index('Barcode',inplace=True)

    statistic['oligos design'] = assoc.Oligo.nunique()
    statistic[['barcodes design']] = assoc.shape[0]

    #get count df
    click.echo("Read count file...")
    counts=pd.read_csv(counts_file, sep='\t', header=None,names=['Barcode','dna_count','rna_count'])
    statistic['barcodes dna/rna'] = counts.shape[0]

    #fill in labels from dictionary
    click.echo("Fill count files with oligo names...")
    label=[]
    for i,row in counts.iterrows():
        if row.Barcode in assoc.index:
            label.append(assoc.loc[row.Barcode].Oligo)
        else:
            statistic[['unknown barcodes dna/rna']] += 1
            label.append('no_BC')
            
    statistic['matched barcodes'] = statistic['barcodes dna/rna'] - statistic['unknown barcodes dna/rna']
    statistic['% matched barcodes'] = (statistic['matched barcodes']/statistic['barcodes dna/rna'])*100.0

    # Insert the label of oligo
    counts.insert(0, 'name', label)

    # remove Barcorde. Not needed anymore
    counts.drop(['Barcode'], axis=1, inplace=True)

    # number of DNA and RNA counts
    total_dna_counts=sum(counts['dna_count'])
    total_rna_counts=sum(counts['rna_count'])

    statistic['total dna counts'] = total_dna_counts
    statistic['total rna counts'] = total_rna_counts
    statistic['avg dna counts per bc'] = statistic['total dna counts']/statistic['barcodes dna/rna']
    statistic['avg rna counts per bc'] = statistic['total rna counts']/statistic['barcodes dna/rna']

    # filter
    counts = counts[counts['dna_count']>=minDNACounts]
    counts = counts[counts['rna_count']>=minRNACounts]

    grouped_label = counts.groupby(counts['name']).agg({'dna_count' : ['sum', 'count'], 'rna_count' : ['sum', 'count']})

    grouped_label.reset_index(inplace=True)

    output = pd.DataFrame()

    click.echo(grouped_label.head())

    output['name'] = grouped_label['name']
    output['dna_counts'] = grouped_label.dna_count['sum']
    output['rna_counts'] = grouped_label.rna_count['sum']

    statistic['oligos dna/rna'] = len(grouped_label)-1
    statistic['avg dna/rna barcodes per oligo'] = sum(
                grouped_label[grouped_label['name']!='no_BC'].dna_count['count']
            )/statistic['oligos dna/rna']

    # scaling = 10**min([len(str(total_dna_counts))-1,len(str(total_rna_counts))-1])
    scaling = 10**6

    output['dna_normalized']=(grouped_label.dna_count['sum']+pseudocountDNA)/((grouped_label.dna_count['count']+pseudocountDNA))/total_dna_counts*scaling



    output['rna_normalized']=(grouped_label.rna_count['sum']+pseudocountRNA)/((grouped_label.rna_count['count']+pseudocountRNA))/total_rna_counts*scaling

    output['ratio'] = output.rna_normalized/output.dna_normalized
    output['log2'] = np.log2(output.ratio)

    output['n_obs_bc'] = grouped_label.dna_count['count']


    click.echo(output_file)

    output.to_csv(output_file, index=False,sep='\t', compression='gzip')

    statistic.to_csv(statistic_file, index=False,sep='\t', compression='gzip')

if __name__ == '__main__':
    cli()

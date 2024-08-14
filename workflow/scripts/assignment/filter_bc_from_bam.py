# usecase: python filter_bc_from_bam.py --identity_threshold 0.98 --mismatches_threshold 3 --use_expected_alignment_length True --expected_alignment_length 265 --bamfile /data/gpfs-1/users/kisa11_c/work/coding/MPRA/IGVF_Y1_design/experiment/standard_results/results/assignment/standardAssignIGVFDesignNoTemp/bam/bwa_merged.bam --verbose True
import pysam
import pandas
import sys
import click

# TODO: add options for calling from the command line
# TODO: add verbose option to only give warnings with verbose?
# TODO: What about length filter?
# TODO: remove debug
# TODO: add prints for snakemake => writes log (with summary: numbers in the end)

# import yaml
# # config usage:
# config_path = "/data/gpfs-1/users/kisa11_c/work/coding/80K_analysis/01_missing_sequences/config/filter_bc_from_bam_config.yml"
# with open(config_path) as conf:
#     config = yaml.load(conf, Loader=yaml.FullLoader)
#     conf.close()


# # Input:
# # use split as test data
# identity_threshold = config["general"]["identity_threshold"]
# mismatches_threshold = config["general"]["mismatches_threshold"]
# use_expected_alignment_length = config["general"]["use_expected_alignment_length"]
# expected_alignment_length = config["general"]["expected_alignment_length"]
# # code from /data/gpfs-1/users/kisa11_c/work/coding/MPRA/bin/removeSequenceErrors.py
# bamfile = config["files"]["merged_bam"]
# verbose = config["general"]["verbose"]
# logfile = config["files"]["output_log"]
# output_file = config["files"]["assignment_tbl"]
## with command line options:

@click.command()
@click.option('--identity_threshold',
                '-i',
                ('identity_threshold'),
                required = False,
                default = 0.98,
                type = float,
                help = 'Provide threshold for the alignment identity (default=0.98).')
@click.option('--mismatches_threshold',
                '-m',
                ('mismatches_threshold'),
                required = False,
                default = 3,
                type = int,
                help = 'Provide threshold for the number of missmatches without warning (default=3).')
@click.option('--use_expected_alignment_length',
                '-e',
                ('use_expected_alignment_length'),
                required = False,
                default = True,
                type = bool,
                help = 'Should a threshold for the expected alignment length be set (default=True).')
@click.option('--expected_alignment_length',
                '-a',
                ('expected_alignment_length'),
                required = False,
                default = 265,
                type = int,
                help = 'Provide the threshold for the expected alignment length (default=265).')
@click.option('--bamfile',
                '-b',
                ('bamfile'),
                required = True,
                type = click.Path(exists=True, readable=True),
                help = 'Path of the bam file to be parsed (.bam).')
@click.option('--verbose',
                '-v',
                ('verbose'),
                required = False,
                default = True,
                type = bool,
                help = 'Specify if you would like to receive a summary in standard output (default=True).')
@click.option('--output',
                '-o',
                ('output_path'),
                required = True,
                type = click.Path(writable=True),
                help = 'Specify path to output file (.tsv).')


def main(identity_threshold, mismatches_threshold, use_expected_alignment_length, expected_alignment_length, bamfile, verbose, output_path):
  # helpful functions
  def determine_MD_NM(differences,sequence,alnLength):
    NM = 0
    MD = ''
    lpos = -1
    for refPos,seqPos,edit in differences:
      if type(edit[1]) != type('T'):
        NM+=edit[1]
        if edit[0] == 'INS': pass
        else:
          if lpos+1 <= refPos:
            MD += "%d^%s"%(refPos-(lpos+1),edit[2])
            lpos = refPos-1+edit[1]
          else:
            MD += "^%s"%(edit[2])
            lpos += edit[1]
      else:
        if lpos+1 <= refPos:
          MD += "%d%s"%(refPos-(lpos+1),edit[1])
        else:
          MD += "%s"%(edit[1])
        lpos = refPos+len(edit[1])-1
        NM += len(edit[1])
    if lpos+1 <= alnLength:
      MD += "%d"%(alnLength-(lpos+1))
    return MD,NM


  def aln_length(cigarlist):
    tlength = 0
    for operation,length in cigarlist:
      if operation == 0 or operation == 2 or operation == 3 or operation >= 6: tlength += length
    return tlength


  def expected_length_filter(read, expected_length):
    """Filter reads that are of an expected length (AS tag is used because match gives 1 => if AS >= expected_length, then read is of expected length and quality)"""
    if read.get_tag('AS') >= expected_length:
      return True
    return False


  def calculate_sequence_identity(read):
    """Compute sequence identity form a read using cigar string, MD tag, and NM tag"""
    try:
      cigar = read.cigarstring
      MD = read.get_tag('MD')
      NM = read.get_tag('NM')
      alnLength = aln_length(read.cigartuples)
    except KeyError:
      sys.stderr.write("Error: No MD or NM tag found")
      return -1
    return (alnLength - NM)/alnLength, NM


  def get_number_of_matches_per_strand(read):
    """Get number of matches per forward and reverse strand assuming read has XA tag"""
    # split ";" on right side of XA tag
    xa_tag = read.get_tag('XA').rstrip(';')
    xa_list = xa_tag.split(';')
    forward_matches = 0
    reverse_matches = 0
    for xa in xa_list:
      if '+' in xa.split(",")[-3]: # because oligo name might include ";"
        forward_matches += 1
      elif '-' in xa.split(",")[-3]:
        reverse_matches += 1
      else:
        sys.stderr.write("Error: XA tag does not contain strand information")
        sys.exit()
    return forward_matches, reverse_matches


  def get_XA_information(read):
    """Select the XA information from the alternative alignment on the positive strand"""
    try:
      prepare_xa = read.get_tag("XA").split(",") # oligo name might include ";"
      reference_name = prepare_xa[0]
      next_elem = prepare_xa[1:] # remove first name
    except KeyError:
      sys.stderr.write("Error: No XA tag found")
      return -1
    while len(next_elem) > 0:
        next_elem = ",".join(next_elem) # join back
        next_elem = next_elem.split(";") # join back, split on ; in order to find one element
        elem = next_elem[0]
        if "+" in elem.split(",")[-3]:
            return f"{reference_name},{elem}"
        # join again with one less
        next_elem = ";".join(next_elem[1:])
        prepare_xa = next_elem.split(",")
        reference_name = prepare_xa[0]
        next_elem = prepare_xa[1:] # remove first name
    sys.stderr.write("Error: No forward alignment found in XA tag")
    return -1


  def get_barcode(read):
    """The barcode is stored in XI tag:XI:Z:<barcode>,YI:I:<unknown>"""
    # check if it does not include "N"
    try:
      barcode = read.get_tag("XI").split(",")[0]
    except:
      return "failed"
    if "N" in barcode.upper():
        sys.stderr.write("Error: Barcode of {read.query_name}")
        return "failed"
    return barcode


  def prepare_table_information(read, case="normal"):
    """Prepares the information of the association:
      @case:
        - normal: the information from the alignment are taken
        - fix_mapping_quality: the mapping quality is set to 1 but all information is taken from the alignment
        - rescue: we rescue a better alignment from the XA tag
        - failed: we write barcode without found assignment to the file ({barcode}\tother\tNA)
    """
    barcode = get_barcode(read)
    if case == "failed":
      return f"{barcode}\tother\tNA"
    reference_name = read.reference_name
    position=read.reference_start # 0-based
    cigarstring=read.cigarstring
    nm=read.get_tag("NM")
    md=read.get_tag("MD")
    if case == "normal":
      mapping_quality = read.mapping_quality

    if case == "fix_mapping_quality":
      mapping_quality = 1

    if case == "rescue":
      # if NM is 0, then we can rescue the alignment from XA tag
      xa_info = get_XA_information(read)
      reference_name = xa_info.split(",")[0]
      position = int(xa_info.split(",")[1])
      cigarstring = xa_info.split(",")[2]
      nm = int(xa_info.split(",")[3])
      md = read.get_tag("MD")
      mapping_quality = 1
      if nm != 0:
        md = "unknown" # if NM != 0: we don't know MD tag
    return f"{barcode}\t{reference_name}\t{position};{cigarstring};NM:i:{nm};MD:Z:{md};{mapping_quality}"


  input_file = pysam.Samfile(bamfile, "rb" )
  count = 0
  high_mismatches_count = 0
  high_identity_count = 0
  unmapped_count = 0
  reversed_read_count = 0
  rescued_read_count = 0
  not_rescuable_count = 0
  count_no_second_alignment = 0
  change_quality_count = 0
  high_quali_reversed_read_count = 0
  high_quality_same_as_xs = 0
  high_quality_alignment = 0
  high_mapping_quality_low_identity = 0
  low_quality_alignment = 0
  show_example = True
  print("start reading bam file ...")
  with open(output_path, "w") as output_file:
    for read in input_file:
      count += 1
      #### Counting of specific read properties and writing filtered alignments to file
      # skip reads with certain properties
      if read.is_unmapped:
        unmapped_count += 1
        continue # because of weird line (NB501960:812:HH53WAFX5:1:11101:13917:2374	4	*	0	0	None	*	0	0	GGTG)

      sequence_identity, num_mismatches = calculate_sequence_identity(read)
      # modify mapping quality for reads on forward with AS > XS
      if read.mapping_quality < 1:

        # filter for expected sequence length only if mapping quality is low
        if use_expected_alignment_length:
          if not expected_length_filter(read,expected_alignment_length):
            output_file.write(prepare_table_information(read, case="failed") + "\n")
            continue

        # check if read has low identity but high alignment score
        if not sequence_identity >= identity_threshold:
          output_file.write(prepare_table_information(read, case="failed") + "\n")
          continue
        # high alignment identity => potentially interesting alignments
        high_identity_count += 1

        if num_mismatches > mismatches_threshold: # throw warning
          high_mismatches_count += 1
          sys.stderr.write("WARNING: number of missmatches from %s is %d\n"%(read.query_name, num_mismatches))
          output_file.write(prepare_table_information(read, case="failed") + "\n")

        low_quality_alignment += 1
        if read.flag == 0: # check if it is a best alignment
          if read.get_tag("AS") > read.get_tag("XS"):
            change_quality_count += 1
            output_file.write(prepare_table_information(read, case="fix_mapping_quality") + "\n")


        # rescue reads with reversed read (flag == 16) with AS == XS and check if only on other alignment on forward strand is given
        if read.flag == 16:
          reversed_read_count += 1
          if read.get_tag("AS") == read.get_tag("XS"):
            try:
              read.get_tag("XA")
            except:
              sys.stderr.write("WARNING: read (%s) can not be rescued because XA tag is not given\n"%(read.query_name))
              count_no_second_alignment += 1
              output_file.write(prepare_table_information(read, case="failed") + "\n")
              continue
            # check if only one alignment on forward strand is given
            forward_matches, reverse_matches = get_number_of_matches_per_strand(read)
            if forward_matches == 1: # best alignment found on forward strand
              # change alignment to forward strand with the information from XA tag
              output_file.write(prepare_table_information(read, case="rescue") + "\n")
              rescued_read_count += 1
            elif forward_matches > 1:
              not_rescuable_count += 1
              #Throw warning that the read can not be rescued
              sys.stderr.write("WARNING: read (%s) can not be rescued because more than one alignment on forward strand is given\n"%(read.query_name))
              output_file.write(prepare_table_information(read, case="failed") + "\n")

      else: # mapping quality >= 1
        if not sequence_identity >= identity_threshold:
          sys.stderr.write("WARNING: read (%s) has mapping quality >=1 according to the aligner but the alignment does not match the identity threshold of %s and has an alignment length of %s\n"%(read.query_name, identity_threshold, aln_length(read.cigartuples)))
          high_mapping_quality_low_identity += 1
          # TODO: Should I trust the aligner or should I stick to the threshold?
        if not expected_length_filter(read,expected_alignment_length):
          sys.stderr.write("WARNING: read (%s) has mapping quality >=1 according to the aligner but does not match the expected alignment length (%s) and has an alignment length of %s\n"%(read.query_name, expected_alignment_length, aln_length(read.cigartuples)))
        high_quality_alignment += 1
        # # check if reversed read has AS = XS
        # if read.flag == 16:
        #   high_quali_reversed_read_count += 1
        #   if read.get_tag("AS") == read.get_tag("XS"):
        #     high_quality_same_as_xs += 1
        #     try:
        #       read.get_tag("XA")
        #     except:
        #       sys.stderr.write("WARNING: read (%s) can not be rescued because XA tag is not given\n"%(read.query_name))
        #       count_no_second_alignment += 1
        #       output_file.write(prepare_table_information(read, case="failed") + "\n")
        #       continue
        output_file.write(prepare_table_information(read, case="normal") + "\n")
    if verbose:
      print("------ List of alignment counts ------", file=sys.stderr)
      print("Number of processed Alignemnts: ", count, file=sys.stderr)
      print("Number of high mapping quality according to aligner: ", high_quality_alignment, file=sys.stderr)
      print("Number of low mapping quality according to aligner: ", low_quality_alignment, file=sys.stderr)
      print("Alignments above the user defined identity threshold: ", high_identity_count, file=sys.stderr)
      print("Alignment with more mismatches than allowed by the user: ", high_mismatches_count, file=sys.stderr)
      print("Number of high identity alignments with same best and second best alignment score: ", high_quality_same_as_xs, file=sys.stderr)
      print("Number of high identity alignments with reversed reads: ", high_quali_reversed_read_count, file=sys.stderr)
      print("Number of high alignment scores with low identity score ", high_mapping_quality_low_identity, file=sys.stderr)
      print("reversed_read_count: ", reversed_read_count, file=sys.stderr)
      print("-- Rescued alignments --", file=sys.stderr)
      print("All rescued reads: ", change_quality_count + rescued_read_count, file=sys.stderr)
      print("Found alignment on forward strand: ", rescued_read_count, file=sys.stderr)
      print("This alignment is a best alignment (score of second best alignment is lower): ", change_quality_count, file=sys.stderr)
      print("-- Not rescued alignments --", file=sys.stderr)
      print("Number of unmapped reads: ", unmapped_count, file=sys.stderr)
      print("Score of alignment on reverse strand equals second best alignment on forward strand but multiple alignments on the forward strand detected: ", not_rescuable_count, file=sys.stderr)
      print("Alignment score equals second best alignment score but no second best alignment is given: ", count_no_second_alignment, file=sys.stderr)

  input_file.close()
  output_file.close()

  # TODO: Sorting the dataframe by barcode, reference_name, and additional information (like sort -k1,1 -k2,2 -k3,3)
  # TODO: add checking how many rows the log file has and tell it to the user

if __name__=='__main__':
  main()


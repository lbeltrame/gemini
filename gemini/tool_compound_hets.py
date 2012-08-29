#!/usr/bin/env python
import sqlite3
import os
import sys
import numpy as np
import cPickle
import zlib
import collections
from copy import copy

import gemini_utils as util
from gemini_constants import *

class Site(object):
    def __init__(self, row):
        self.chrom     = row['chrom']
        self.start     = row['start']
        self.end       = row['end']
        self.ref       = row['ref']
        self.alt       = row['alt']
        self.gene      = row['gene']
        self.num_hets  = row['num_het']
        # self.exon      = row['exon']
        self.aaf       = row['aaf']
        self.dbsnp     = row['in_dbsnp']
        # self.impact    = row['impact']
        # specific to each sample
        self.phased    = None
        self.gt        = None
    
    def __repr__(self):
        return ','.join([self.chrom, str(self.start), str(self.end)])
        
    def __eq__(self, other):
        return self.start == other.start


def get_compound_hets(c, args):
    """
    Report the count of each genotype class
    observed for each sample.
    """
    # build a mapping of the numpy array index to the appropriate sample name
    # e.g. 0 == 109400005
    #     37 == 147800025
    idx_to_sample = util.map_indicies_to_samples(c)

    comp_hets = collections.defaultdict(lambda: collections.defaultdict(list))

    query = "SELECT * FROM variants \
             WHERE is_coding = 1" # is_exonic - what about splice?
    c.execute(query)

    for row in c:
        gt_types  = np.array(cPickle.loads(zlib.decompress(row['gt_types'])))
        gt_phases = np.array(cPickle.loads(zlib.decompress(row['gt_phases'])))
        gt_bases  = np.array(cPickle.loads(zlib.decompress(row['gts'])))
        
        site = Site(row)
        if site.num_hets > 1 and not args.allow_other_hets: continue
        
        for idx, gt_type in enumerate(gt_types):
            if gt_type == GT_HET:
                sample = idx_to_sample[idx]
                sample_site = copy(site)
                sample_site.phased = gt_phases[idx]
                sample_site.gt = gt_bases[idx]
                comp_hets[sample][site.gene].append(site)
    # report
    for sample in comp_hets:
        for gene in comp_hets[sample]:
            for site1 in comp_hets[sample][gene]:
                for site2 in comp_hets[sample][gene]:
                    if site1 == site2:
                        continue
                    print sample, gene, site1, site2


def run(parser, args):

    if os.path.exists(args.db):
        conn = sqlite3.connect(args.db)
        conn.isolation_level = None
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        # run the compound het caller
        get_compound_hets(c, args)


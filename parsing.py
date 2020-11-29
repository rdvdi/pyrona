#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This file contains a helper function to identify meeting table / config pairs
from the generated files saved in output/ folder. 
"""
import os

def find_table_config_pairs(tag, paths):
    """
    Args:
        str tag: part of filename to filter files to be used
        dict paths: hard-coded paths to output folders
    Out:
        dict path_pairs: keys "config" and "meet_table"
    """

    aa = os.listdir(paths[    "configs"])
    bb = os.listdir(paths["meet_tables"])
    
    path_pairs = []
    
    for a in aa: # only few files, so nested loop is ok
                 
        for b in bb:
            
            if tag in a and tag in b:
                
                # leave only "_usercomment_timestamp" part of filenames
                a_tag = a.split('.')[0][len('config_')    :]
                b_tag = b.split('.')[0][len('meet_table_'):]
                
                if a_tag == b_tag:
                    
                    path_pair = {
                        "config"    : os.path.join(paths[    "configs"], a),
                        "meet_table": os.path.join(paths["meet_tables"], b),
                        "tag"       : a_tag}
                    
                    path_pairs.append(path_pair)
    return path_pairs

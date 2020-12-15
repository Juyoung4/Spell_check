import pkg_resources
from spell.spellClass import SymSpell, Verbosity
from collections import defaultdict, namedtuple
from google.cloud import bigquery
import csv
import time
import pandas
from tqdm import tqdm
import datetime
from datetime import date
import re
import json

def question_check(request):
    request_json = request.get_json(silent=True)
    if request_json and 'questionTxt' in request_json and 'choice' in request_json :
        input_term = {
            'questionTxt': request_json['questionTxt'],
            'choice1': request_json['choice1'],
            'choice2': request_json['choice2'],
            'choice3': request_json['choice3'],
            'choice4': request_json['choice4']
            }
    else:
        return f'key error'

    sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
    
    dictionary_path = pkg_resources.resource_filename("spell", "frequency_dictionary_en_82_765.txt")
    bigram_path = pkg_resources.resource_filename("spell", "frequency_bigramdictionary_en_243_342.txt")

    sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1)
    sym_spell.load_bigram_dictionary(bigram_path, term_index=0, count_index=2)	

    ### excel file load ###
    fieldnames = {
        'result' : True,
        'error corpus' : '',
        'error count' : '',
    }

    for key,value in input_term.items():
        suggestions, corpus, num = sym_spell.lookup_compound(value, max_edit_distance=2)
        for i in suggestions:
            if num[0] > 0:
                fieldnames['result'] = False
                fieldnames['error corpus'] = dict(corpus)
                fieldnames['error count'] = len(dict(corpus).keys())
        input_term[key] = fieldnames
                

    return json.dumps(input_term), 200, {'Content-Type': 'application/json'}



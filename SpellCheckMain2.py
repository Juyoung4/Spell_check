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
from flask import Flask, Response, request, jsonify

app = Flask(__name__)

class SpellCheckMain():
    def __init__(self, input_term=''):
        self.input_term = input_term

    def question_check(self):
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

        for key,value in self.input_term.items():
            suggestions, corpus, num = sym_spell.lookup_compound(value, max_edit_distance=2)
            for i in suggestions:
                if num[0] > 0:
                    fieldnames['result'] = False
                    fieldnames['error corpus'] = dict(corpus)
                    fieldnames['error count'] = len(dict(corpus).keys())
            self.input_term[key] = fieldnames
                    

        return self.input_term


if __name__ == "__main__":
    SC = SpellCheckMain()
    SC.input_term = {
        'questionTxt': 'During puberty, chenge in voice is due to the growth of____.',
        'choice1': 'Neck bone',
        'choice2': 'None',
        'choice3': 'Yes',
        'choice4': 'Both',
    }
    print(SC.question_check())


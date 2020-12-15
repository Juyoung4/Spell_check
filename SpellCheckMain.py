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

class SpellCheckMain():
    def __init__(self, name='Compiled_AllQuestions_Grade8 (edited on july 31).xlsx', path='spell_check_output/question_check_07.29.csv'):
        self.execel_name = name
        self.path = path

    def question_check(self):
        sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        
        dictionary_path = pkg_resources.resource_filename("spell", "frequency_dictionary_en_82_765.txt")
        bigram_path = pkg_resources.resource_filename("spell", "frequency_bigramdictionary_en_243_342.txt")

        sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1)
        sym_spell.load_bigram_dictionary(bigram_path, term_index=0, count_index=2)	

        count1, count2 = 1, 1 #count1 = total / count2 = final

        ### excel file load ### 
        df = pandas.read_excel(self.execel_name)
        q_id, q_txt = list(df['No.']), list(df['Question Txt (y)'])
        
        q_txt = list(map(str, q_txt))

        with open(self.path, 'w') as file:
            fieldnames = ['No', 'error corpus', 'error count', 'original question', 'suggestion', 'number']
            wr = csv.writer(file, delimiter = ',')
            wr.writerow(fieldnames)

            for Id, txt in tqdm(zip(q_id[:5], q_txt[:5])):
                data = []
                input_term = txt
                # suggestions, corpus, num = sym_spell.lookup_compound(input_term, max_edit_distance=2)
                # suggestions는 change한 문장
                # corpus는 틀린 단어 corpus
                
                print(Id," input_term : ",input_term)
                suggestions, corpus, num = sym_spell.lookup_compound(input_term, max_edit_distance=2)
                for i in suggestions:
                    if num[0] > 0:
                        print(Id,"result suggestions : ",i.term)
                        print(Id, "num : ",num)
                        for k,v in dict(corpus).items():
                            print(k)
                            print(v[0])
                        print()
                        print()
                    

        #         for suggestion in suggestions:
        #             if num[0] > 0:
        #                 data.append(Id)
        #                 data.append(dict(corpus))
        #                 data.append(num.pop(0))#question 번호
        #                 data.append(input_term)
        #                 data.append(suggestion.term)
        #                 data.append(count1)
        #                 wr.writerow(data)
        #                 count2 += 1
        #         count1 += 1
        # return "total: "+str(count1),"final: "+str(count2),


if __name__ == "__main__":
    SC = SpellCheckMain()
    print(SC.question_check())


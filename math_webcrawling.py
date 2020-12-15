import requests
from bs4 import BeautifulSoup
import re

# BeautifulSoup: HTML 문서를 탐색해서 원하는 부분만 쉽게 뽑아낼 수 있음
def add_math_words():
    one_wordList = load_words('spell/frequency_dictionary_en_82_765.txt',1)
    multi_wordList = load_words('spell/frequency_bigramdictionary_en_243_342.txt',2)

    f1 = open('spell/frequency_dictionary_en_82_765.txt','a')
    f2 = open('spell/frequency_bigramdictionary_en_243_342.txt','a')

    for i in 'abcdefghijklmnopqrstuvwxyz':
        webpage = requests.get('https://www.mathsisfun.com/definitions/letter-'+i+'.html')
        soup = BeautifulSoup(webpage.content, 'html.parser')
        hostKeys = soup.select('div.ltrCol')

        for key in hostKeys:
            for math_term in key.text.split('\n')[1:]:
                math_term = math_term.lower()
                term = re.sub(r'\([^)]*\)', '', math_term)
                if len(term.split()) == 1:
                    if term not in one_wordList: f1.write(term + ' 1000000000\n')
                if len(term.split()) == 2:
                    if term not in multi_wordList: f2.write(term + ' 1000000000\n')

def add_science_words():
    one_wordList = load_words('spell/frequency_dictionary_en_82_765.txt',1)
    multi_wordList = load_words('spell/frequency_bigramdictionary_en_243_342.txt',2)

    f1 = open('spell/frequency_dictionary_en_82_765.txt','a')
    f2 = open('spell/frequency_bigramdictionary_en_243_342.txt','a')

    for i in 'abcdefghijklmnopqrstuvwxyz':
        if i == 'a':
            webpage = requests.get('https://sciencenotes.org/chemistry-dictionary-chemistry-definitions/')
        else:
            webpage = requests.get('https://sciencenotes.org/chemistry-dictionary-'+i+'-chemistry-definitions/')
        soup = BeautifulSoup(webpage.content, 'html.parser')
        hostKeys = soup.find('section', {'class': 'entry-content'})
        strong_terms = []
        for j in hostKeys:
            strong = j.find('strong')
            if strong and strong != -1:
                if len(strong.text.split()) <= 2:
                    term = re.sub(r'\([^)]*\)', '', strong.text)
                    strong_terms.append(term.lower())
        strong_terms = strong_terms[1:-1]
        for key in strong_terms:
            if len(key.split()) == 1:
                if key not in one_wordList:
                    try:
                        f1.write(key + ' 1000000000\n')
                    except:
                        print(key)
            if len(key.split()) == 2:
                if key not in multi_wordList:
                    try:
                        f2.write(key + ' 1000000000\n')
                    except:
                        print(key)
    

def load_words(file_name, num):
    f = open(file_name, 'r')
    word_list = []
    while True:
        line = f.readline()
        if not line: break
        if num == 1:
            if line.split(): word_list.append(line.split()[0])
        else:
            if line.split(): word_list.append((' ').join(line.split()[:-1]))
    return word_list


if __name__ == "__main__":
    #print(add_math_words())
    print(add_science_words())
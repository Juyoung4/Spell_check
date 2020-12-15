from difflib import SequenceMatcher
from itertools import zip_longest
import re


## 문자열로된 숫자를 64비트 부호 정수로 변환한다 
def try_parse_int64(string):
    try:
        ret = int(string)
    except ValueError:
        return None
    return None if ret < -2 ** 64 or ret >= 2 ** 64 else ret

## phrase로부터 non-unique한 wordlist를 생성한다(언어 무관)
def parse_words(phrase, preserve_case=False):
    if preserve_case: return re.findall(r"([^\W_]+['’]*[^\W_]*)", phrase)
    # re.sub(r'[{}@_*>()\\#%+=\[\]×,.!?/-]',' ', phrase)
    # re.sub(r'[0123456789]',' ', phrase)
    # (re.findall(r"([^\W_]+['’]*[^\W_]*)", phrase)))
    else:
        if phrase is not None:
            s_phrase = re.findall(r"([^\W_]+['’]*[^\W_]*)", phrase.lower())
            change_phrase = [re.sub("[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾`',!@#$%^&]",'',i) for i in s_phrase]
            return change_phrase # re.findall(r"([^\W_]+['’]*[^\W_]*)", phrase.lower())

## 단어는 모두 대문자(모자) 또는 숫자 포함하는지 체크함
def is_acronym(word):
    return re.match(r"\b[A-Z0-9]{2,}\b", word) is not None

## 비교할 두 string이 null일 경우(혹인 하나가) 적절한 edit distance의 값을 반환한다
def null_distance_results(string1, string2, max_distance):
    if string1 is None:
        if string2 is None:
            return 0
        else:
            return len(string2) if len(string2) <= max_distance else -1
    return len(string1) if len(string1) <= max_distance else -1

## 공통 접두사 및 접미사 하위 문자열이 제외되도록 두 문자열의 시작 위치와 길이를 계산한다.
def prefix_suffix_prep(string1, string2):
    len1 = len(string1)
    len2 = len(string2)

    # suffix common to both strings can be ignored
    while len1 != 0 and string1[len1 - 1] == string2[len2 - 1]:
        len1 -= 1
        len2 -= 1
    # prefix common to both strings can be ignored
    start = 0
    while start != len1 and string1[start] == string2[start]:
        start += 1
    if start != 0:
        len1 -= start
        # length of the part excluding common prefix and suffix
        len2 -= start
    return len1, len2, start

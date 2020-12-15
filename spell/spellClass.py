from collections import defaultdict, namedtuple
from enum import Enum
import gzip
from itertools import cycle
import math
import os.path
import pickle
import re
import sys

from spell.editDistance import EditDistance
import spell.spellHelpers as helpers

class Verbosity(Enum):
    """Controls the closeness/quantity of returned spelling
    suggestions.
    """
    TOP = 0  #: Top suggestion with the highest term frequency of the suggestions of smallest edit distance found.
    CLOSEST = 1  #: All suggestions of smallest edit distance found, suggestions ordered by term frequency.
    ALL = 2  #: All suggestions within maxEditDistance, suggestions ordered by edit distance, then by term frequency (slower, no early termination).

class SuggestItem(object):
    def __init__(self, term, distance, count):
        self._term = term
        self._distance = distance
        self._count = count
    
    def __eq__(self, other):
        if self._distance == other.distance:
            return self._count == other.count
        else:
            return self._distance == other.distance
    
    def __lt__(self, other):
        if self._distance == other.distance:
            return self._count > other.count
        else:
            return self._distance < other.distance
    
    def __str__(self): ##change
         return "{}, {}, {}".format(self._term, self._distance, self._count)#"{}".format(self._term)#

    @property
    def term(self):
        return self._term

    @term.setter
    def term(self, term):
        self._term = term

    @property
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, distance):
        self._distance = distance

    @property
    def count(self):
        return self._count

    @count.setter
    def count(self, count):
        self._count = count

class SymSpell(object):
    """
        파라미터
            - max_dictionary_edit_distance: 단어 조회할때 수정할 최대 길이 지정(int) -> optional
            - prefix_length: 단어의 prefix의 길이는 spell checking할때 사용한다(int) -> optional
            - count_threshold: 단어가 올바른 spelling인지 간주되는 사전 단어의 최소 빈도 수(int)
    """
    data_version = 2
    N = 1024908267229
    bigram_count_min = sys.maxsize

    def __init__(self, max_dictionary_edit_distance=2, prefix_length=7, count_threshold=1):
        if max_dictionary_edit_distance < 0:
            raise ValueError("max_dictionary_edit_distance cannot be negative")
        if (prefix_length < 1 or prefix_length <= max_dictionary_edit_distance):
            raise ValueError("prefix_length cannot be less than 1 or smaller than max_dictionary_edit_distance")
        if count_threshold < 0:
            raise ValueError("count_threshold cannot be negative")
        self._words = dict() # -> 고유하고 올바른 철자 단어 사전 및 각 단어의 빈도 수.
        self._below_threshold_words = dict() # -> 단어 사전 체크할 동안 count threshold보다 빈도수가 낮은 단어들의 사전
        self._bigrams = dict() 
        self._deletes = defaultdict(list) # -> 틀린 단어에 대한 제안된 수정 단어 목록과 해당 단어에서 파생된 삭제 목록을 포함
        self._max_dictionary_edit_distance = max_dictionary_edit_distance # 최대 사전 단어의 길이
        self._prefix_length = prefix_length # -> spelling check에 사용되는 단어 prefix길이
        self._count_threshold = count_threshold # -> 단어가 너무 자주 발생되면 해당 단어는 맞느 단어라 생각해야함. 그때 단어의 빈도수 threshold 
        self._max_length = 0 # -> 단어사전에서 가장 긴 단어의 길이
        self._replaced_words = dict() # -> 맞거나 수정된 단어들의 모음집

    ##### dictionary function loda/create/update #####
    def create_dictionary_entry(self, key, count):
        """
        - dictionary안에 entry(key, count)를 create/update하는 함수이다
        - 모든 단어들은 dictionary에서 create/add된 self.deletes가 있다(편집할 수 있는 길이: 1~max_edit_distance)
        - 모든 self.deletes entry는 원래단어에 대해 제안된 수정 단어들의 list를 가진다
        - dictionary는 create_dictionary_entry()이 함수가 불리면 언제나 동적으로 update 가능하다 -> 계속 추가 가능하다는 이야기
        """
        if count <= 0:
            if self._count_threshold > 0: #threshold count값이 0보다 큰데 단어의 빈도수가 0보다 작으면 추가 x
                return False
            count = 0 # threshold count값이 0보다 작으면  count 값은 0으로 지정
        

        if self._count_threshold > 1 and key in self._below_threshold_words:
            count_previous = self._below_threshold_words[key]
            count = (count_previous + count
                     if sys.maxsize - count_previous > count
                     else sys.maxsize)
            if count >= self._count_threshold:
                self._below_threshold_words.pop(key)
            else:
                self._below_threshold_words[key] = count
                return False
        elif key in self._words:
            count_previous = self._words[key]

            count = (count_previous + count
                     if sys.maxsize - count_previous > count
                     else sys.maxsize)
            self._words[key] = count
            return False
        elif count < self._count_threshold:
            self._below_threshold_words[key] = count
            return False

        self._words[key] = count

        if len(key) > self._max_length:
            self._max_length = len(key)

        edits = self._edits_prefix(key)
        for delete in edits:
            self._deletes[delete].append(key)
        return True
        
    def load_dictionary(self, corpus, term_index, count_index, separator=" ", encoding=None):
        # dictionary txt file lod : <word> <count> pairs
        """
            파라미터
                - corpus : path+filenmae
                - term_index : 단어의 열 위치 -> (ex) cm 100000000000 [0번임]
                - count_index : 단어의 빈도수 열 위치
                - separator: 단어와 단어개수 사이의 구분 문자 (있으면 쓰고 없으면 안써도 됨)
                - encoding : Text encoding of the dictionary file
        """
        if not os.path.exists(corpus):
            return False
        with open(corpus, "r", encoding=encoding) as infile: # dictionary file open and read
            for line in infile:
                line_parts = line.rstrip().split(separator) #현재 dictionary의 구분자 x(띄어쓰기임)
                if len(line_parts) >= 2: # 단어와 단어 개수가 pair로 있으면
                    key = line_parts[term_index] 
                    count = helpers.try_parse_int64(line_parts[count_index]) # 문자열 숫자를 변환
                    if count is not None:
                        self.create_dictionary_entry(key, count)
        return True
    
    def load_bigram_dictionary(self, corpus, term_index, count_index, separator=None, encoding=None):
        """
        파라미터
                - corpus : path+filenmae
                - term_index : 단어의 열 위치 -> (ex) cm 100000000000 [0번임]
                - count_index : 단어의 빈도수 열 위치
                - separator: 단어와 단어개수 사이의 구분 문자 (있으면 쓰고 없으면 안써도 됨)
                - encoding : Text encoding of the dictionary file
        """
        if not os.path.exists(corpus):
            return False
        with open(corpus, "r", encoding=encoding) as infile:
            for line in infile:
                line_parts = line.rstrip().split(separator)
                key = count = None
                if len(line_parts) >= 3 and separator is None:
                    key = "{} {}".format(line_parts[term_index],
                                         line_parts[term_index + 1])
                elif len(line_parts) >= 2 and separator is not None:
                    key = line_parts[term_index]
                if key is not None:
                    count = helpers.try_parse_int64(line_parts[count_index])
                if count is not None:
                    self._bigrams[key] = count
                    if count < self.bigram_count_min:
                        self.bigram_count_min = count
        return True

    ##### get suggestions #####
    def lookup(self, phrase, verbosity, max_edit_distance=None, include_unknown=False, ignore_token=None):
        """
            함수: 주어진 phrase에 대한 제안할 spellings를 찾아준다

            파라미터:
                - phrase: 문장
                - verbosity: (class:`Verbosity`) suggestions에서 빈도수가 높은 순서에서 몇개를 반환할 것인가
                - max_edit_distance: phrase와 제안된 단어들 사이의 최대 edit distance이다
                - include_unknown: suggestions 단어 안에 phrase 단어를 포함시킬지 선택[만약 edit distance에 포함되는 단어가 없을 경우]
                - ignore_token: 단어/문장에서 무시하거나 바꾸지 않을 regex 패턴
            
            반환:
                - suggestions_line = list로, Class 'SuggestItem'의 객체로써 'phrase'에 대한 올바른 spelling들을 제안된 것이다
        """        
        if max_edit_distance is None:
            max_edit_distance = self._max_dictionary_edit_distance
        if max_edit_distance > self._max_dictionary_edit_distance:
            raise ValueError("Distance too large")
        
        suggestions = list()
        phrase_len = len(phrase)
        
        def early_exit():
            if include_unknown and not suggestions: #suggestion할게 없는 경우
                suggestions.append(SuggestItem(phrase, max_edit_distance + 1, 0))
            return suggestions

        suggestion_count = 0
        if phrase in self._words:
            suggestion_count = self._words[phrase]
            suggestions.append(SuggestItem(phrase, 0, suggestion_count))
            if verbosity != Verbosity.ALL:
                return early_exit()

        considered_deletes = set()
        considered_suggestions = set()
        considered_suggestions.add(phrase)

        max_edit_distance_2 = max_edit_distance
        candidate_pointer = 0
        candidates = list()

        phrase_prefix_len = phrase_len
        if phrase_prefix_len > self._prefix_length:
            phrase_prefix_len = self._prefix_length
            candidates.append(phrase[: phrase_prefix_len])
        else:
            candidates.append(phrase)
        
        distance_comparer = EditDistance()
        while candidate_pointer < len(candidates):
            candidate = candidates[candidate_pointer]
            candidate_pointer += 1
            candidate_len = len(candidate)
            len_diff = phrase_prefix_len - candidate_len
            if len_diff > max_edit_distance_2:
                if verbosity == Verbosity.ALL:
                    continue
                break
            if candidate in self._deletes: #candidate가 틀린단어안에 포함되어 있으면
                dict_suggestions = self._deletes[candidate] #제안된 후보군들
                for suggestion in dict_suggestions:
                    if suggestion == phrase:
                        continue
                    suggestion_len = len(suggestion)
                    if (abs(suggestion_len - phrase_len) > max_edit_distance_2 or suggestion_len < candidate_len or (suggestion_len == candidate_len  and suggestion != candidate)):
                        continue
                    suggestion_prefix_len = min(suggestion_len, self._prefix_length)
                    if (suggestion_prefix_len > phrase_prefix_len and suggestion_prefix_len - candidate_len > max_edit_distance_2):
                        continue
                    distance = 0
                    min_distance = 0
                    if candidate_len == 0:
                        distance = max(phrase_len, suggestion_len)
                        if (distance > max_edit_distance_2 or suggestion in considered_suggestions):
                            continue
                    elif suggestion_len == 1:
                        distance = (phrase_len if phrase.index(suggestion[0]) < 0 else phrase_len - 1)
                        if (distance > max_edit_distance_2 or suggestion in considered_suggestions): continue
                    else:
                        if self._prefix_length - max_edit_distance == candidate_len:
                            min_distance = (min(phrase_len, suggestion_len) - self._prefix_length)
                        else: min_distance = 0
                        
                        if (self._prefix_length - max_edit_distance == candidate_len
                                and (min_distance > 1
                                     and phrase[phrase_len + 1 - min_distance :] != suggestion[suggestion_len + 1 - min_distance :])
                                or (min_distance > 0
                                    and phrase[phrase_len - min_distance] != suggestion[suggestion_len - min_distance]
                                    and (phrase[phrase_len - min_distance - 1] != suggestion[suggestion_len - min_distance]
                                         or phrase[phrase_len - min_distance] != suggestion[suggestion_len - min_distance - 1]))): continue
                        else:
                            if ((verbosity != Verbosity.ALL and not self._delete_in_suggestion_prefix(candidate, candidate_len, suggestion, suggestion_len)) or suggestion in considered_suggestions): continue
                            considered_suggestions.add(suggestion)
                            distance = distance_comparer.compare(phrase, suggestion, max_edit_distance_2)
                            if distance < 0: continue
                        
                        if distance <= max_edit_distance_2:
                            suggestion_count = self._words[suggestion]
                            si = SuggestItem(suggestion, distance, suggestion_count)
                            if suggestions:
                                if verbosity == Verbosity.CLOSEST:
                                    if distance < max_edit_distance_2: suggestions = list()
                                elif verbosity == Verbosity.TOP:
                                    if (distance < max_edit_distance_2 or suggestion_count > suggestions[0].count):
                                        max_edit_distance_2 = distance
                                        suggestions[0] = si
                                    continue
                            if verbosity != Verbosity.ALL: max_edit_distance_2 = distance
                            suggestions.append(si)
            if (len_diff < max_edit_distance and candidate_len <= self._prefix_length):
                if (verbosity != Verbosity.ALL and len_diff >= max_edit_distance_2): continue
                for i in range(candidate_len):
                    delete = candidate[: i] + candidate[i + 1 :]
                    if delete not in considered_deletes:
                        considered_deletes.add(delete)
                        candidates.append(delete)
        if len(suggestions) > 1: suggestions.sort()
        early_exit()
        return suggestions 
      
    def lookup_compound(self, phrase, max_edit_distance, ignore_non_words=False):
        """
            함수 : 
                (1) 이 함수는 input으로 아래 3개 조건인 문장(여러 단어가 포함된)을 자동적으로 spelling 오류 검증을 지원해준다

                [조건1] correct한 단어 사이에 공백으로 인해 incorrect한 두 단어로 인식됬을 경우
                [조건2] 두개의 correct한 단어사이에 공백이 없어 incorrect한 한 단어로 인식됬을 경우
                [조건3] 맞춤법 오류가 있는/없는 다중 독립 input words
            
                (2) 여러 단어가 포함된 input 문장을 위한 spelling을 제안한다(supports word splitting/merging)

            파라미터:
                - phrase: spell check할 문장
                - max_edit_distance: 입력 단어와 제안 단어 사이의 최대 edit할 거리
                - ignore_non_words: 철자 검사 과정에서 숫자와 두문자어를 그대로 둘건지 결정하는 플래그(optional)
            
            반환 값:
                - suggestions_line = list로, Class 'SuggestItem'의 객체로써 'phrase'에 대한 올바른 spelling들을 제안된 것이다
        """
        term_list_1 = helpers.parse_words(phrase) # input으로 받은 phrase 문장을 단어 단위로 쪼개줌
        
        suggestions = list()
        suggestion_parts = list()
        distance_comparer = EditDistance()# 우리가 사용할 알고리즘을 토대로 거리 계산

        is_last_combi = False # 모든 단어들을 best suggestion으로 변형할지 선택

        corpus = defaultdict(list) #dict()
        count = 0
        num = []
        if term_list_1 is not None : 
            for i, __ in enumerate(term_list_1):
                
                # self.lookup함수를 이용해서 phrase에 포함되는 단어들에 대한 suggestion된 단어들을 얻는다
                suggestions = self.lookup(term_list_1[i], Verbosity.TOP, max_edit_distance)

                # 여기는 첫번째 단어 다음 단어부터 조건1, 조건2에 대해 확인해야하는 부분이다
                #(ex) which, micro = > self.lookup함수에 phrase로 whichmicro로 줌
                if i > 0 and not is_last_combi:
                    suggestions_combi = self.lookup(term_list_1[i - 1] + term_list_1[i], Verbosity.TOP, max_edit_distance) 
                    if suggestions_combi and suggestion_parts:
                        best_1 = suggestion_parts[-1]
                        if suggestions: best_2 = suggestions[0]
                        else: best_2 = SuggestItem(term_list_1[i], max_edit_distance + 1, 10 // 10 ** len(term_list_1[i]))
                        
                        distance_1 = best_1.distance + best_2.distance

                        if (distance_1 >= 0
                                and (suggestions_combi[0].distance + 1 < distance_1
                                    or (suggestions_combi[0].distance + 1 == distance_1
                                        and (suggestions_combi[0].count > best_1.count / self.N * best_2.count)))):
                            suggestions_combi[0].distance += 1
                            suggestion_parts[-1] = suggestions_combi[0]
                            is_last_combi = True
                            continue
                is_last_combi = False
                if suggestions and (suggestions[0].distance == 0 or len(term_list_1[i]) == 1):
                    check = re.sub(r'[\d]','', term_list_1[i])
                    if check is not True and len(check) == len(term_list_1[i]):
                        suggestions[0]._term = term_list_1[i]
                        suggestion_parts.append(suggestions[0])
                else:
                    suggestion_split_best = None
                    if suggestions:
                        suggestion_split_best = suggestions[0]

                    if len(term_list_1[i]) > 1:
                        for j in range(1, len(term_list_1[i])):
                            part_1 = term_list_1[i][: j]
                            part_2 = term_list_1[i][j :]
                            suggestions_1 = self.lookup(part_1, Verbosity.TOP, max_edit_distance)
                            if suggestions_1:
                                suggestions_2 = self.lookup(part_2, Verbosity.TOP, max_edit_distance)
                                if suggestions_2:
                                    tmp_term = (suggestions_1[0].term + " " + suggestions_2[0].term)
                                    tmp_distance = distance_comparer.compare(term_list_1[i], tmp_term, max_edit_distance)
                                    if tmp_distance < 0:
                                        tmp_distance = max_edit_distance + 1
                                    if suggestion_split_best is not None:
                                        if tmp_distance > suggestion_split_best.distance:
                                            continue
                                        if tmp_distance < suggestion_split_best.distance:
                                            suggestion_split_best = None
                                    if tmp_term in self._bigrams:
                                        tmp_count = self._bigrams[tmp_term]
                                        if suggestions:
                                            best_si = suggestions[0]
                                            if suggestions_1[0].term + suggestions_2[0].term == term_list_1[i]:
                                                tmp_count = max(tmp_count, best_si.count + 2)
                                            elif (suggestions_1[0].term == best_si.term or suggestions_2[0].term == best_si.term):
                                                tmp_count = max(tmp_count, best_si.count + 1)
                                            elif suggestions_1[0].term + suggestions_2[0].term == term_list_1[i]:
                                                tmp_count = max(tmp_count, max(suggestions_1[0].count, suggestions_2[0].count) + 2)
                                            else:
                                                tmp_count = min(self.bigram_count_min, int(suggestions_1[0].count / self.N * suggestions_2[0].count))
                                            suggestion_split = SuggestItem(tmp_term, tmp_distance, tmp_count)
                                            if (suggestion_split_best is None or suggestion_split.count > suggestion_split_best.count):
                                                suggestion_split_best = suggestion_split
                        if suggestion_split_best is not None:
                            check = re.sub(r'[\d]','', term_list_1[i])
                            if check is not True and len(check) == len(term_list_1[i]):
                                if term_list_1[i] != '':
                                    self._replaced_words[term_list_1[i]] = term_list_1[i]
                                    suggestion_parts.append(suggestion_split_best)
                                    corpus[term_list_1[i]].append(suggestion_split_best._term)
                                    count += 1                                       
                            else:
                                suggestion_split_best._term = term_list_1[i]
                                suggestion_parts.append(suggestion_split_best)
                        else:
                            si = SuggestItem(term_list_1[i], max_edit_distance + 1, int(10 / 10 ** len(term_list_1[i])))
                            check = re.sub(r'[\d]','', term_list_1[i])
                            if check is not True and len(check) == len(term_list_1[i]):
                                if term_list_1[i] != '':
                                    self._replaced_words[term_list_1[i]] = term_list_1[i] 
                                    suggestion_parts.append(si)
                                    corpus[term_list_1[i]].append(si._term)
                                    count += 1
                            else:
                                si._term = term_list_1[i]
                                suggestion_parts.append(si)
                    else:
                        si = SuggestItem(term_list_1[i], max_edit_distance + 1, int(10 / 10 ** len(term_list_1[i])))
                        check = re.sub(r'[\d]','', term_list_1[i])
                        if check is not True and len(check) == len(term_list_1[i]):
                            if term_list_1[i] != '':
                                self._replaced_words[term_list_1[i]] = term_list_1[i]
                                suggestion_parts.append(si)  
                                corpus[term_list_1[i]].append(si._term)
                                count += 1                      
                        else:
                            si._term = term_list_1[i]
                            suggestion_parts.append(si)
        num.append(count)
        joined_term=""
        joined_count = self.N
        for si in suggestion_parts:
            joined_term += si.term + " "
            joined_count *= si.count / self.N
        joined_term = joined_term.rstrip()

        suggestion = SuggestItem(joined_term, distance_comparer.compare(phrase, joined_term, 2 ** 31 - 1), int(joined_count))
        suggestions_line = list()
        suggestions_line.append(suggestion)

        return suggestions_line, corpus, num

                    

        
    def _delete_in_suggestion_prefix(self, delete, delete_len, suggestion, suggestion_len):
        """
            함수: 모든 delete 문자가 suggestion_prefix에 반영되었는지 확인한다
        """
        if delete_len == 0:
            return True
        if self._prefix_length < suggestion_len:
            suggestion_len = self._prefix_length
        j = 0
        for i in range(delete_len):
            del_char = delete[i]
            while j < suggestion_len and del_char != suggestion[j]:
                j += 1
            if j == suggestion_len:
                return False
        return True

    ##### edit function #####
    def _edits(self, word, edit_distance, delete_words):
        """Inexpensive and language independent: only deletes,
        no transposes + replaces + inserts replaces and inserts are
        expensive and language dependent
        """
        edit_distance += 1
        word_len = len(word)
        if word_len > 1:
            for i in range(word_len):
                delete = word[: i] + word[i + 1 :]
                if delete not in delete_words:
                    delete_words.add(delete)
                    # recursion, if maximum edit distance not yet
                    # reached
                    if edit_distance < self._max_dictionary_edit_distance:
                        self._edits(delete, edit_distance, delete_words)
        return delete_words

    def _edits_prefix(self, key):
        hash_set = set()
        if len(key) <= self._max_dictionary_edit_distance:
            hash_set.add("")
        if len(key) > self._prefix_length:
            key = key[: self._prefix_length]
        hash_set.add(key)
        return self._edits(key, 0, hash_set)


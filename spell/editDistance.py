from enum import Enum
import numpy as np

import spell.spellHelpers as helpers

class EditDistance(object):
    """
        edit distance 알고리즘

        파라미터:
            - algorithm : 사용할 distance 알고리즘
    """
    def __init__(self):
        """
            _algorithm: 사용할 distance 알고리즘
            _distance_comparer: class:`AbstractDistanceComparer`
                                상대적은 두 string사이의 거리를 계산한다(사용할 알고리즘에 따라 지정)
                                
        """
        self._distance_comparer = DamerauOsa()

    def compare(self, string_1, string_2, max_distance):
        """
            base string(string1)과 string(String2) 비교 => edit distance거리를 계산하기 위해서(알고리즘을 통해)
        """
        return self._distance_comparer.distance(string_1, string_2, max_distance)

# DamerauOsa 알고리즘 class
class DamerauOsa():
    def __init__(self):
        self._base_char_1_costs = np.zeros(0, dtype=np.int32)
        self._base_prev_char_1_costs = np.zeros(0, dtype=np.int32)

    def distance(self, string_1, string_2, max_distance):
        """
            함수: 두 단어 사이의 최적의 정렬 edit distance를 계산하여 반환한다
        """
        if string_1 is None or string_2 is None: return helpers.null_distance_results(string_1, string_2, max_distance)
        if max_distance <= 0: return 0 if string_1 == string_2 else -1

        max_distance = int(min(2 ** 31 - 1, max_distance))

        # 계산을 빠르게 하기 위해서 string_1은 두 문자열 중 짧은 길이를 가진 string으로 배치 
        if len(string_1) > len(string_2):
            string_2, string_1 = string_1, string_2
        if len(string_2) - len(string_1) > max_distance:
            return -1
        
        len_1, len_2, start = helpers.prefix_suffix_prep(string_1, string_2)

        if len_1 == 0:
            return len_2 if len_2 <= max_distance else -1
        if len_2 > len(self._base_char_1_costs):
            self._base_char_1_costs = np.zeros(len_2, dtype=np.int32)
            self._base_prev_char_1_costs = np.zeros(len_2, dtype=np.int32)
        if max_distance < len_2:
            return self._distance_max(string_1, string_2, len_1, len_2, start, max_distance, self._base_char_1_costs, self._base_prev_char_1_costs)
        return self._distance(string_1, string_2, len_1, len_2, start, self._base_char_1_costs, self._base_prev_char_1_costs)

    def _distance(self, string_1, string_2, len_1, len_2, start, char_1_costs, prev_char_1_costs):
        """
            핵심 Damerau-Levenshtein의 내부 구현, 최적의 문자열 정렬 알고리즘.
        """
        char_1_costs = np.asarray([j + 1 for j in range(len_2)])
        char_1 = " "
        current_cost = 0
        for i in range(len_1):
            prev_char_1 = char_1
            char_1 = string_1[start + i]
            char_2 = " "
            left_char_cost = above_char_cost = i
            next_trans_cost = 0
            for j in range(len_2):
                this_trans_cost = next_trans_cost
                next_trans_cost = prev_char_1_costs[j]

                prev_char_1_costs[j] = current_cost = left_char_cost

                left_char_cost = char_1_costs[j]

                prev_char_2 = char_2
                char_2 = string_2[start + j]

                if char_1 != char_2:
                    if above_char_cost < current_cost:
                        current_cost = above_char_cost
                if left_char_cost < current_cost:
                    current_cost = left_char_cost
                current_cost += 1
                if (i != 0 and j != 0
                        and char_1 == prev_char_2
                        and prev_char_1 == char_2
                        and this_trans_cost + 1 < current_cost):
                    # transposition
                    current_cost = this_trans_cost + 1
            char_1_costs[j] = above_char_cost = current_cost
        return current_cost

    def _distance_max(self, string_1, string_2, len_1, len_2, start, max_distance, char_1_costs, prev_char_1_costs):
        char_1_costs = np.asarray([j + 1 if j < max_distance else max_distance + 1 for j in range(len_2)])
        len_diff = len_2 - len_1
        j_start_offset = max_distance - len_diff
        j_start = 0
        j_end = max_distance
        char_1 = " "
        current_cost = 0
        for i in range(len_1):
            prev_char_1 = char_1
            char_1 = string_1[start + i]
            char_2 = " "
            left_char_cost = above_char_cost = i
            next_trans_cost = 0
            j_start += 1 if i > j_start_offset else 0
            j_end += 1 if j_end < len_2 else 0
            for j in range(j_start, j_end):
                this_trans_cost = next_trans_cost
                next_trans_cost = prev_char_1_costs[j]
                # cost of diagonal (substitution)
                prev_char_1_costs[j] = current_cost = left_char_cost
                # left now equals current cost (which will be diagonal
                # at next iteration)
                left_char_cost = char_1_costs[j]
                prev_char_2 = char_2
                char_2 = string_2[start + j]
                if char_1 != char_2:
                    # substitution if neither of two conditions below
                    if above_char_cost < current_cost:
                        current_cost = above_char_cost
                    if left_char_cost < current_cost:
                        current_cost = left_char_cost
                    current_cost += 1
                    if (i != 0 and j != 0 and char_1 == prev_char_2
                            and prev_char_1 == char_2
                            and this_trans_cost + 1 < current_cost):
                        # transposition
                        current_cost = this_trans_cost + 1
                char_1_costs[j] = above_char_cost = current_cost
            if char_1_costs[i + len_diff] > max_distance:
                return -1
        return current_cost if current_cost <= max_distance else -1
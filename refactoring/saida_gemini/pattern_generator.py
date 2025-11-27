from utils import Utils
import re
import string
import numpy as np
from sklearn.cluster import KMeans

class PatternGenerator:

    def __init__(self, data, coverage_threshold, sampling_size=None, constrained_temp=True):
        self.coverage_threshold = coverage_threshold
        if sampling_size is None:
            self.sampling_size = int(np.ceil((1.96**2 * 0.5 * (1-0.5)) / (0.05**2)))
        else:
            self.sampling_size = sampling_size
        self.splits, self.indices_train = Utils.split_and_validate(data, self.sampling_size)
        self.digits = set(str(i) for i in range(10))
        self.upper_letters = set(string.ascii_uppercase)
        self.lower_letters = set(string.ascii_lowercase)
        self.type_mapping = {d:'\\\d' for d in self.digits}
        self.type_mapping.update({l:'[A-Z]' for l in self.upper_letters})
        self.type_mapping.update({l:'[a-z]' for l in self.lower_letters})
        self.template_information = {}
        self.patterns = []
        self.pattern_coverage = {}
        self.constrained_temp = constrained_temp

    def information_gathering(self, symbols, column, coverage):
        self.template_information = {}
        if self.constrained_temp:
            max_length = Utils.symbol_length(symbols, column, coverage)
        else:
            max_length = Utils.symbol_length(symbols, column, 1)
        for i in range(len(column)):
            template, token_length_bag, token_char_bag, token_bag = Utils.token_info(symbols, column[i], max_length)
            for token, length in token_length_bag.items():
                token_chars = token_char_bag[token]
                current_token = token_bag[token]
                if template in self.template_information:
                    if token not in self.template_information[template]:
                        self.template_information[template][token] = {'length':{}, 'chars': {}, 'token': {}}
                    if length in self.template_information[template][token]['length']:
                        self.template_information[template][token]['length'][length] += 1
                    else:
                        self.template_information[template][token]['length'][length] = 1
                    if current_token in self.template_information[template][token]['token']:
                        self.template_information[template][token]['token'][current_token] += 1
                    else:
                        self.template_information[template][token]['token'][current_token] = 1
                    for j, char in enumerate(token_chars):
                        if 'pos_%d'%j not in self.template_information[template][token]['chars']:
                            self.template_information[template][token]['chars']['pos_%d'%j] = {char:1}
                        else:
                            if char not in self.template_information[template][token]['chars']['pos_%d'%j]:
                                self.template_information[template][token]['chars']['pos_%d'%j][char] = 1
                            else:
                                self.template_information[template][token]['chars']['pos_%d'%j][char] += 1
                else:
                    self.template_information[template] = {token: {'length': {length:1}, 
                                                                   'chars': {'pos_%d'%j: {c:1} for j, c in enumerate(token_chars)}, 
                                                                   'token': {current_token:1}}}
    
    def _categorize_tokens(self, coverages, categories, column):
        if len(coverages) > 1:
            coverages.append(1)
            coverages.append(1/len(column))
            X = np.array(coverages).reshape(-1, 1)
            kmeans = KMeans(n_clusters=2, n_init='auto', random_state=0, n_init='auto')
            kmeans.fit(X)
            cluster_labels = kmeans.labels_
            label_select = np.argmax(kmeans.cluster_centers_)
            categories_selected = [categories[i] for i in range(len(categories)) if cluster_labels[i]==label_select]
            categories_coverage = sum([coverages[i] for i in range(len(coverages)-2) if cluster_labels[i]==label_select])
            if categories_coverage >= self.coverage_threshold:
                return [re.escape(token) for token in categories_selected]
        return None
    
    def _process_char_stats(self, char_stats, symbols, minimum_constraint, pos, last_type, token_char):
        filtered = Utils.rank_and_threshold(char_stats, self.coverage_threshold)
        coverages = list([value/sum(char_stats.values()) for value in char_stats.values()])
        chars = list(char_stats.keys())
        coverages.append(1)
        coverages.append(1/len(chars))
        X = np.array(coverages).reshape(-1, 1)
        kmeans = KMeans(n_clusters=2, n_init='auto', random_state=0, n_init='auto')
        kmeans.fit(X)
        cluster_labels = kmeans.labels_
        label_select = np.argmax(kmeans.cluster_centers_)
        chars_selected = [chars[i] for i in range(len(chars)) if cluster_labels[i]==label_select]
        chars_coverage = sum([coverages[i] for i in range(len(chars)) if cluster_labels[i]==label_select])
        if chars_coverage >= self.coverage_threshold and int(pos[4:]) < minimum_constraint:
            if last_type != '':
                token_char += '%s{%d}'%(last_type, type_count)
            char_list = sorted([re.escape(token) for token in chars_selected])
            if len(char_list) > 1:
                token_char += '(' + '|'.join(char_list) + ')'
            elif len(char_list) == 1:
                token_char += char_list[0]
            last_type = ''
        else:
            mapped = np.unique([self.type_mapping[key] for key in filtered.keys()])
            if len(mapped) == 1:
                if mapped[0] == last_type:
                    type_count += 1
                else:
                    if last_type != '':
                        if int(pos[4:]) > minimum_constraint:
                            token_char += '%s*'%(last_type)
                        else:
                            token_char += '%s{%d}'%(last_type, type_count)
                    last_type = mapped[0]
                    type_count = 1
            elif all(m for m in mapped if m not in symbols):
                current_type = '['
                for item in sorted(mapped):
                    if item == '\\\d':
                        current_type += '0-9'
                    elif item == '[a-z]':
                        current_type += 'a-z'
                    else:
                        current_type += 'A-Z'
                current_type += ']'
                if current_type == last_type:
                    type_count += 1
                else:
                    if last_type != '':
                        if int(pos[4:]) > minimum_constraint:
                            token_char += '%s*'%(last_type)
                        else:
                            token_char += '%s{%d}'%(last_type, type_count)
                    last_type = current_type
                    type_count = 1
            else:
                if '.' == last_type:
                    type_count += 1
                else:
                    if last_type != '':
                        if int(pos[4:]) > minimum_constraint:
                            token_char += '%s*'%(last_type)
                        else:
                            token_char += '%s{%d}'%(last_type, type_count)
                    last_type = '.'
                    type_count = 1
        return last_type, token_char

    def pattern_generation(self, symbols, column):
        self.information_gathering(symbols, column, self.coverage_threshold)
        for template, token_stats in self.template_information.items():
            composed_template = template
            for _, stats in token_stats.items():
                token_char = ''
                coverages = [value/sum(stats['token'].values()) for value in stats['token'].values()]
                categories = list(stats['token'].keys())
                categorized_tokens = self._categorize_tokens(coverages, categories, column)
                if categorized_tokens:
                    token_list = sorted(categorized_tokens)
                    if len(token_list) > 1:
                        composed_template = re.sub('TOKEN', '(' + '|'.join(token_list) + ')', composed_template, 1)
                    elif len(token_list) == 1:
                        composed_template = re.sub('TOKEN', token_list[0], composed_template, 1)
                    continue
                else:
                    composed_template = re.sub('TOKEN', re.escape(categories[0]), composed_template, 1)
                    continue
                filtered = Utils.rank_and_threshold(stats['length'], self.coverage_threshold)
                if len(filtered.keys()) == 1:
                    length_constraint = list(filtered.keys())[0]
                    minimum_constraint = length_constraint
                else:
                    length_constraint = '+'
                    minimum_constraint = min(list(filtered.keys()))
                last_type = ''
                type_count = 0
                force_dumped = False
                for pos, char_stats in stats['chars'].items():
                    if int(pos[4:]) >= minimum_constraint:
                        if length_constraint != '+':
                            break
                        elif not force_dumped:
                            if last_type != '':
                                token_char += '%s{%d}'%(last_type, type_count)
                                last_type = ''
                                force_dumped = True
                    last_type, token_char = self._process_char_stats(char_stats, symbols, minimum_constraint, pos, last_type, token_char)
                if last_type != '':
                    if force_dumped:
                        token_char += '%s*'%(last_type)
                    else:
                        token_char += '%s{%d}'%(last_type, type_count)
                composed_template = re.sub('TOKEN', r'%s'%token_char, composed_template, 1)
            self.patterns.append(composed_template)

    def pattern_coverage_statictics(self):
        (train_data, test_data) = self.splits
        boc_summary = Utils.bag_of_characters_summary(train_data)
        symbols = set(item for item in boc_summary.keys() if (item not in self.digits and item not in self.upper_letters and item not in self.lower_letters))
        self.type_mapping.update({l:'[a-z]' for l in symbols})
        self.pattern_generation(symbols, train_data)
        for template in self.patterns:
            if template not in self.pattern_coverage:
                self.pattern_coverage[template] = {}
            pattern = re.compile(template)
            cov_train = len(Utils.find_exact_match_elements(pattern, train_data))
            cov_test = len(Utils.find_exact_match_elements(pattern, test_data))
            cov_whole = (cov_train+cov_test)/(len(train_data)+len(test_data))
            self.pattern_coverage[template] = cov_whole

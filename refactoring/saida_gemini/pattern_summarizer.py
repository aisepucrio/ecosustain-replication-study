from utils import Utils
import re
import string
import numpy as np
from sklearn.cluster import KMeans

class PatternGenerator:

    def __init__(self, data, coverage_threshold):
        self.coverage_threshold = coverage_threshold
        self.sampling_size = int(0.2*len(data))
        self.splits, self.indices_train = Utils.split_and_validate(data, self.sampling_size)
        self.test = self.splits[1]
        self.test_size = len(self.splits[1])
        self.digits = set(str(i) for i in range(10))
        self.upper_letters = set(string.ascii_uppercase)
        self.lower_letters = set(string.ascii_lowercase)
        self.type_mapping = {d:'\\\d' for d in self.digits}
        self.type_mapping.update({l:'[A-Z]' for l in self.upper_letters})
        self.type_mapping.update({l:'[a-z]' for l in self.lower_letters})
        self.template_information = {}
        self.patterns = []
        self.pattern_coverage = {}
    
    def information_gathering(self, symbols, column, coverage):
        self.template_information = {}
        max_length = Utils.symbol_length(symbols, column, coverage)
        for i in range(len(column)):
            template, token_length_bag, token_char_bag, token_bag = Utils.token_info(symbols, column[i], max_length)
            if template not in self.template_information:
                self.template_information[template] = {}
            for token, length in token_length_bag.items():
                token_chars = token_char_bag[token]
                current_token = token_bag[token]
                if token not in self.template_information[template]:
                    self.template_information[template][token] = {'length': {}, 'chars': {}, 'token': {}}
                self._update_token_info(self.template_information[template][token]['length'], length)
                self._update_token_info(self.template_information[template][token]['token'], current_token)
                for j, char in enumerate(token_chars):
                    pos_key = f'pos_{j}'
                    if pos_key not in self.template_information[template][token]['chars']:
                        self.template_information[template][token]['chars'][pos_key] = {}
                    self._update_token_info(self.template_information[template][token]['chars'][pos_key], char)

    def _update_token_info(self, data_dict, key):
        if key in data_dict:
            data_dict[key] += 1
        else:
            data_dict[key] = 1

    def _categorize_tokens(self, coverages, categories, column, composed_template):
        if len(coverages) > 1:
            X = np.array(coverages + [1, 1/len(column)]).reshape(-1, 1)
            kmeans = KMeans(n_clusters=2, random_state=0, n_init=10)
            kmeans.fit(X)
            cluster_labels = kmeans.labels_
            label_select = np.argmax(kmeans.cluster_centers_)
            categories_selected = [categories[i] for i in range(len(categories)) if cluster_labels[i] == label_select]
            categories_coverage = sum(coverages[i] for i in range(len(coverages)) if cluster_labels[i] == label_select)
            if categories_coverage >= self.coverage_threshold:
                token_list = sorted([re.escape(token) for token in categories_selected])
                if len(token_list) > 1:
                    composed_template = re.sub('TOKEN', '(' + '|'.join(token_list) + ')', composed_template, 1)
                elif len(token_list) == 1:
                    composed_template = re.sub('TOKEN', token_list[0], composed_template, 1)
                return composed_template, True
        else:
            composed_template = re.sub('TOKEN', re.escape(categories[0]), composed_template, 1)
            return composed_template, True
        return composed_template, False

    def _generate_token_char(self, stats, symbols, minimum_constraint, last_type, type_count, token_char, force_dumped):
        for pos, char_stats in stats['chars'].items():
            if int(pos[4:]) >= minimum_constraint:
                if last_type != '':
                    token_char += f'{last_type}{{ {type_count} }}'
                    last_type = ''
                    force_dumped = True
                break

            coverages = [value / sum(char_stats.values()) for value in char_stats.values()]
            chars = list(char_stats.keys())
            X = np.array(coverages + [1, 1/len(chars)]).reshape(-1, 1)
            kmeans = KMeans(n_clusters=2, random_state=0, n_init=10)
            kmeans.fit(X)
            cluster_labels = kmeans.labels_
            label_select = np.argmax(kmeans.cluster_centers_)
            chars_selected = [chars[i] for i in range(len(chars)) if cluster_labels[i] == label_select]
            chars_coverage = sum(coverages[i] for i in range(len(coverages)) if cluster_labels[i] == label_select)

            if chars_coverage >= self.coverage_threshold and int(pos[4:]) < minimum_constraint:
                if last_type != '':
                    token_char += f'{last_type}{{ {type_count} }}'
                char_list = sorted([re.escape(token) for token in chars_selected])
                token_char += '(' + '|'.join(char_list) + ')' if len(char_list) > 1 else char_list[0]
                last_type = ''
            else:
                mapped = np.unique([self.type_mapping[key] for key in char_stats.keys()])
                if len(mapped) == 1:
                    if mapped[0] == last_type:
                        type_count += 1
                    else:
                        if last_type != '':
                            token_char += f'{last_type}*' if int(pos[4:]) > minimum_constraint else f'{last_type}{{ {type_count} }}'
                        last_type = mapped[0]
                        type_count = 1
                elif all(m for m in mapped if m not in symbols):
                    current_type = '[' + ''.join(sorted(item.replace('\\', '') for item in mapped if item != '\\d')) + ']'
                    if current_type == last_type:
                        type_count += 1
                    else:
                        if last_type != '':
                            token_char += f'{last_type}*' if int(pos[4:]) > minimum_constraint else f'{last_type}{{ {type_count} }}'
                        last_type = current_type
                        type_count = 1
                else:
                    if '.' == last_type:
                        type_count += 1
                    else:
                        if last_type != '':
                            token_char += f'{last_type}*' if int(pos[4:]) > minimum_constraint else f'{last_type}{{ {type_count} }}'
                        last_type = '.'
                        type_count = 1
        return token_char, last_type, type_count, force_dumped
    
    def pattern_generation(self, symbols, column):
        self.information_gathering(symbols, column, self.coverage_threshold)
        for template, token_stats in self.template_information.items():
            composed_template = template
            for _, stats in token_stats.items():
                token_char = ''
                coverages = [value / sum(stats['token'].values()) for value in stats['token'].values()]
                categories = list(stats['token'].keys())
                composed_template, continue_flag = self._categorize_tokens(coverages, categories, column, composed_template)
                if continue_flag:
                    continue

                filtered = Utils.rank_and_threshold(stats['length'], self.coverage_threshold)
                length_constraint = list(filtered.keys())[0] if len(filtered.keys()) == 1 else '+'
                minimum_constraint = list(filtered.keys())[0] if len(filtered.keys()) == 1 else min(filtered.keys())

                last_type = ''
                type_count = 0
                force_dumped = False
                token_char, last_type, type_count, force_dumped = self._generate_token_char(
                    stats, symbols, int(minimum_constraint), last_type, type_count, token_char, force_dumped
                )

                if last_type != '':
                    token_char += f'{last_type}*' if force_dumped else f'{last_type}{{ {type_count} }}'
                composed_template = re.sub('TOKEN', r'%s' % token_char, composed_template, 1)
            self.patterns.append(composed_template)

    def pattern_coverage_statictics(self):
        train_data, test_data = self.splits
        boc_summary = Utils.bag_of_characters_summary(train_data)
        symbols = set(item for item in boc_summary.keys() if (item not in self.digits and item not in self.upper_letters and item not in self.lower_letters))
        self.type_mapping.update({l:'[a-z]' for l in symbols})
        self.pattern_generation(symbols, train_data)
        for template in self.patterns:
            if template not in self.pattern_coverage:
                self.pattern_coverage[template] = {}
            pattern = re.compile(template)
            cov_whole = len(Utils.find_exact_match_elements(template, train_data + test_data))
            self.pattern_coverage[template] = cov_whole / (len(train_data) + len(test_data))
        print(self.pattern_coverage)

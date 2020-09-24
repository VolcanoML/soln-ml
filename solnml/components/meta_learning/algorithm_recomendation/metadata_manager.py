import os
import pickle
import numpy as np
from solnml.datasets.utils import calculate_metafeatures


def get_feature_vector(dataset, dataset_id, data_dir='./', task_type=None):
    meta_dir = os.path.dirname(__file__)
    meta_dir = os.path.join(meta_dir, '..')
    meta_dir = os.path.join(meta_dir, 'meta_resource')
    dataset_meta_feat_filename = meta_dir + 'meta_feature_dataset_%s.pkl' % dataset
    if os.path.exists(dataset_meta_feat_filename):
        with open(dataset_meta_feat_filename, 'rb') as f:
            feature_vec = pickle.load(f)
        return feature_vec
    else:
        feature_dict = calculate_metafeatures(dataset, dataset_id, data_dir, task_type=task_type)
        sorted_keys = sorted(feature_dict.keys())
        return [feature_dict[key] for key in sorted_keys]


def fetch_algorithm_runs(meta_dir, dataset, metric, total_resource, rep, buildin_algorithms):
    median_score = list()
    for algo in buildin_algorithms:
        scores = list()
        for run_id in range(rep):
            meta_folder = os.path.join(meta_dir, 'meta_runs')
            meta_folder = os.path.join(meta_folder, metric)
            save_path = os.path.join(meta_folder + '%s-%s-%s-%d-%d.pkl' % (
                dataset, algo, metric, run_id, total_resource))
            if not os.path.exists(save_path):
                continue

            with open(save_path, 'rb') as f:
                res = pickle.load(f)
                scores.append(res[2])

        if len(scores) >= 1:
            median_score.append(np.median(scores))
        else:
            median_score.append(-1)
    return median_score


class MetaDataManager(object):
    def __init__(self, metadata_dir, builtin_algorithms, builtin_datasets, metric, resource_n,
                 task_type=None, rep=3):
        self.task_type = task_type
        self.rep_num = rep
        self.metadata_dir = metadata_dir
        self.builtin_algorithms = builtin_algorithms
        self.builtin_datasets = builtin_datasets
        self.metric = metric
        self.resource_n = resource_n

        self._task_ids = list()
        self._dataset_embedding = list()
        self._dataset_perf4algo = list()

    def load_meta_data(self):
        X, perf4algo, task_ids = list(), list(), list()
        meta_dataset_dir = os.path.join(self.metadata_dir, 'meta_dataset_vec')
        save_path1 = os.path.join(meta_dataset_dir, 'meta_dataset_embedding.pkl')
        save_path2 = os.path.join(meta_dataset_dir, 'meta_dataset_algo2perf.pkl')

        if os.path.exists(save_path1) and os.path.exists(save_path2):
            with open(save_path1, 'rb') as f:
                data1 = pickle.load(f)
            with open(save_path2, 'rb') as f:
                data2 = pickle.load(f)
            self._dataset_embedding = data1['dataset_embedding']
            self._task_ids = data1['task_ids']
            self._dataset_perf4algo = data2['perf4algo']
        else:
            for _dataset in self.builtin_datasets:
                print('Creating embedding for dataset - %s.' % _dataset)
                # Calculate metafeature for datasets.
                try:
                    feature_dict = calculate_metafeatures(_dataset, task_type=self.task_type)
                except Exception as e:
                    print(e)
                    continue
                sorted_keys = sorted(feature_dict.keys())
                meta_instance = [feature_dict[key] for key in sorted_keys]

                X.append(meta_instance)

                task_ids.append('init_%s' % _dataset)
                # Extract the performance for each algorithm on this dataset.
                scores = fetch_algorithm_runs(self.metadata_dir, _dataset, self.metric,
                                              self.resource_n, self.rep_num, self.builtin_algorithms)
                perf4algo.append(scores)

            with open(save_path1, 'wb') as f:
                data = dict()
                data['task_ids'] = task_ids
                data['dataset_embedding'] = X
                pickle.dump(data, f)

            with open(save_path2, 'wb') as f:
                data = dict()
                data['algorithms_included'] = self.builtin_algorithms
                data['perf4algo'] = np.asarray(perf4algo)
                pickle.dump(data, f)
        self._dataset_embedding = np.asarray(X)
        self._dataset_perf4algo = np.asarray(perf4algo)
        self._task_ids = task_ids
        return self._dataset_embedding, self._dataset_perf4algo, self._task_ids

    def add_meta_runs(self, task_id, dataset_vec, algo_perf):
        pass

    def update2file(self):
        pass

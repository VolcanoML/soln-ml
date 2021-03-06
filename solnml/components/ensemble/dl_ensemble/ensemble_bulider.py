import os
import torch
from sklearn.metrics.scorer import _BaseScorer
from solnml.components.ensemble.dl_ensemble.bagging import Bagging
from solnml.components.ensemble.dl_ensemble.blending import Blending
from solnml.datasets.base_dl_dataset import DLDataset
from solnml.components.ensemble.dl_ensemble.ensemble_selection import EnsembleSelection
from solnml.components.evaluators.base_dl_evaluator import TopKModelSaver, get_estimator

ensemble_list = ['bagging', 'blending', 'ensemble_selection']


class EnsembleBuilder:
    def __init__(self, stats, ensemble_method: str,
                 ensemble_size: int,
                 task_type: int,
                 max_epoch: int,
                 metric: _BaseScorer,
                 timestamp: float,
                 output_dir=None,
                 device='cpu', **kwargs):
        self.model = None
        self.device = device
        self.task_type = task_type
        self.max_epoch = max_epoch
        if ensemble_method == 'bagging':
            self.model = Bagging(stats=stats,
                                 ensemble_size=ensemble_size,
                                 task_type=task_type,
                                 max_epoch=max_epoch,
                                 metric=metric,
                                 timestamp=timestamp,
                                 output_dir=output_dir,
                                 device=device, **kwargs)
        elif ensemble_method == 'blending':
            self.model = Blending(stats=stats,
                                  ensemble_size=ensemble_size,
                                  task_type=task_type,
                                  max_epoch=max_epoch,
                                  metric=metric,
                                  timestamp=timestamp,
                                  output_dir=output_dir,
                                  device=device, **kwargs)
        elif ensemble_method == 'ensemble_selection':
            self.model = EnsembleSelection(stats=stats,
                                           ensemble_size=ensemble_size,
                                           task_type=task_type,
                                           max_epoch=max_epoch,
                                           metric=metric,
                                           timestamp=timestamp,
                                           output_dir=output_dir,
                                           device=device, **kwargs)
        else:
            raise ValueError("%s is not supported for ensemble!" % ensemble_method)

    def fit(self, data):
        return self.model.fit(data)

    def predict(self, dataset: DLDataset, mode='test'):
        return self.model.predict(dataset, mode=mode)

    def refit(self, dataset: DLDataset):
        for algo_id in self.model.stats['include_algorithms']:
            for model_config in self.model.stats[algo_id]:
                config_dict = model_config.get_dictionary().copy()
                model_path = self.model.output_dir + TopKModelSaver.get_configuration_id(model_config) + '.pt'
                # Remove the old models.
                if os.path.exists(model_path):
                    os.remove(model_path)

                # Refit the models.
                _, clf = get_estimator(self.task_type, config_dict, max_epoch=self.max_epoch, device=self.device)
                # TODO: if train ans val are two parts, we need to merge it into one dataset.
                clf.fit(dataset.train_dataset)
                # Save to the disk.
                torch.save(clf.model.state_dict(), model_path)
        return self.model.refit()

    def get_ens_model_info(self):
        return self.model.get_ens_model_info()

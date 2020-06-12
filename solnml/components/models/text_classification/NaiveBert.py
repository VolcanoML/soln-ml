import numpy as np
import torch
from ConfigSpace.configuration_space import ConfigurationSpace
from ConfigSpace.conditions import EqualsCondition
from ConfigSpace.hyperparameters import UniformFloatHyperparameter, \
    UniformIntegerHyperparameter, CategoricalHyperparameter, UnParametrizedHyperparameter

from solnml.components.models.base_nn import BaseImgClassificationNeuralNetwork
from solnml.components.utils.constants import DENSE, SPARSE, UNSIGNED_DATA, PREDICTIONS


class NaiveBertClassifier(BaseImgClassificationNeuralNetwork):
    def __init__(self, learning_rate, beta1, batch_size, epoch_num,
                 lr_decay, step_decay, random_state=None, device='cpu', config=None):
        self.learning_rate = learning_rate
        self.beta1 = beta1
        self.batch_size = batch_size
        self.epoch_num = epoch_num
        self.lr_decay = lr_decay
        self.step_decay = step_decay
        self.random_state = random_state
        self.model = None
        self.device = torch.device(device)
        self.time_limit = None
        self.config = config

    def fit(self, X, y, sample_weight=None):
        from .nn_utils.naivebert import Base_Model

        self.model = Base_Model(num_classes=len(set(y)), config=self.config)

        self.model.to(self.device)
        super().fit(X, y)
        return self

    @staticmethod
    def get_properties(dataset_properties=None):
        return {'shortname': 'NaiveBertNet',
                'name': 'NaiveBertNet Classifier',
                'handles_regression': False,
                'handles_classification': True,
                'handles_multiclass': True,
                'handles_multilabel': False,
                'is_deterministic': False,
                'input': (DENSE, SPARSE, UNSIGNED_DATA),
                'output': (PREDICTIONS,)}

    @staticmethod
    def get_hyperparameter_search_space(dataset_properties=None, optimizer='smac'):
        if optimizer == 'smac':
            cs = ConfigurationSpace()
            optimizer = CategoricalHyperparameter('optimizer', ['SGD', 'Adam'], default_value='SGD')
            sgd_learning_rate = UniformFloatHyperparameter(
                "sgd_learning_rate", lower=1e-5, upper=1e-3, default_value=2e-4, log=True)
            sgd_momentum = UniformFloatHyperparameter(
                "sgd_momentum", lower=0, upper=0.9, default_value=0, log=False)
            adam_learning_rate = UniformFloatHyperparameter(
                "adam_learning_rate", lower=1e-6, upper=1e-4, default_value=2e-5, log=True)
            beta1 = UniformFloatHyperparameter(
                "beta1", lower=0.5, upper=0.999, default_value=0.9, log=False)
            batch_size = CategoricalHyperparameter(
                "batch_size", [8, 16, 32], default_value=16)
            lr_decay = UnParametrizedHyperparameter("lr_decay", 0.8)
            step_decay = UnParametrizedHyperparameter("step_decay", 10)
            epoch_num = UnParametrizedHyperparameter("epoch_num", 100)
            cs.add_hyperparameters(
                [optimizer, sgd_learning_rate, adam_learning_rate, sgd_momentum, beta1, batch_size, epoch_num, lr_decay,
                 step_decay])
            sgd_lr_depends_on_sgd = EqualsCondition(sgd_learning_rate, optimizer, "SGD")
            adam_lr_depends_on_adam = EqualsCondition(adam_learning_rate, optimizer, "Adam")
            sgd_momentum_depends_on_sgd = EqualsCondition(sgd_momentum, optimizer, "SGD")
            cs.add_conditions([sgd_lr_depends_on_sgd, adam_lr_depends_on_adam, sgd_momentum_depends_on_sgd])
            return cs
        elif optimizer == 'tpe':
            from hyperopt import hp
            space = {'batch_size': hp.choice('naive_bert_batch_size', [8, 16, 32]),
                     'optimizer': hp.choice('naive_bert_optimizer',
                                            [("SGD", {'sgd_learning_rate': hp.loguniform('naive_bert_sgd_learning_rate',
                                                                                         np.log(1e-4), np.log(1e-2)),
                                                      'sgd_momentum': hp.uniform('naive_bert_sgd_momentum', 0, 0.9)}),
                                             ("Adam",
                                              {'adam_learning_rate': hp.loguniform('naive_bert_adam_learning_rate',
                                                                                   np.log(1e-5), np.log(1e-3)),
                                               'beta1': hp.uniform('naive_bert_beta1', 0.5, 0.999)})]),
                     'epoch_num': 100,
                     'lr_decay': 10,
                     'step_decay': 10
                     }
            return space
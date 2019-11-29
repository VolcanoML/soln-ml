import time
from components.transformation_graph import *
from components.optimizers.base_optimizer import Optimizer
from components.transformers.generator.polynomial_generator import PolynomialTransformation
from components.transformers.selector.extra_trees_based_selector import ExtraTreeBasedSelector
from components.optimizers.transformer_manager import TransformerManager


class EvaluationBasedOptimizer(Optimizer):
    def __init__(self, input_data: DataNode, evaluator, seed):
        super().__init__(str(__class__.__name__), input_data, seed)
        self.evaluator = evaluator
        self.incumbent_score = -1.
        self.start_time = time.time()
        self.transformer_manager = TransformerManager()

    def optimize(self):
        # Evaluate the original features.
        root_score = self.evaluator(self.root_node)
        self.incumbent_score = root_score
        self.incumbent = self.root_node

        num_limit = self.maximum_evaluation_num if self.maximum_evaluation_num is not None else 10000000
        budget_limit = self.time_budget
        max_depth = 8
        beam_width = 3

        cnt = 0
        self.root_node.depth = 1

        # The implementation of Beam Search (https://en.wikipedia.org/wiki/Beam_search).
        is_ended = False
        beam_set = [self.root_node]
        while len(beam_set) > 0 and not is_ended:
            nodes = list()
            for node_ in beam_set:
                self.logger.info('='*50)
                # Limit the maximum depth in graph.
                if node_.depth > max_depth or is_ended:
                    continue

                # Fetch available transformations for this node.
                trans_types = [0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19]
                if node_.depth > 1 and 17 in trans_types:
                    trans_types.remove(17)
                trans_set = self.transformer_manager.get_transformations(node_, trans_types=trans_types)

                for transformer in trans_set:
                    # Avoid repeating the same transformation multiple times.
                    if transformer.type in node_.trans_hist:
                        continue

                    error_msg = None
                    try:
                        self.logger.info(transformer.name)
                        output_node = transformer.operate(node_)
                        output_node.depth = node_.depth + 1
                        output_node.trans_hist.append(transformer.type)

                        # Evaluate this node.
                        _score = self.evaluator(output_node)
                        output_node.score = _score
                        if _score > self.incumbent_score:
                            self.incumbent_score = _score
                            self.incumbent = output_node

                        nodes.append(output_node)
                        self.graph.add_node(output_node)
                        self.graph.add_trans_in_graph(node_, output_node, transformer)
                    except ValueError as e:
                        error_msg = '%s: %s' % (transformer.name, str(e))
                    except MemoryError as e:
                        error_msg = '%s: %s' % (transformer.name, str(e))
                    except RuntimeError as e:
                        error_msg = '%s: %s' % (transformer.name, str(e))
                    except IndexError as e:
                        error_msg = '%s: %s' % (transformer.name, str(e))
                    finally:
                        if error_msg is not None:
                            self.logger.error(error_msg)

                    cnt += 1
                    if cnt > num_limit or (budget_limit is not None and time.time() >= self.start_time + budget_limit):
                        self.logger.info('==> Budget runs out: %d, %d\n' % (num_limit, budget_limit))
                        is_ended = True
                        break

            beam_set = list()
            for node_ in TransformationGraph.sort_nodes_by_score(nodes)[:beam_width]:
                beam_set.append(node_)
            beam_set.append(self.root_node)
            self.logger.info('\n==> Current incumbent: %.4f, Improvement: %f'
                             % (self.incumbent_score, self.incumbent_score - root_score))

        # 1. Apply cross transformations on the categorical features.
        # 2. Conduct feature selection.
        input_node = self.incumbent
        if input_node.cat_num > 1:
            transformer = PolynomialTransformation()
            transformer.compound_mode = 'concatenate'
            transformer.input_type = CATEGORICAL
            transformer.output_type = CATEGORICAL
            try:
                output_node = transformer.operate(input_node)
                print('Shape ==>', input_node.shape, output_node.shape)
                self.graph.add_node(output_node)
                self.graph.add_trans_in_graph(input_node, output_node, transformer)

                _score = self.evaluator(output_node)

                if _score > self.incumbent_score:
                    self.incumbent_score = _score
                    self.incumbent = output_node

                input_node = output_node
                transformer = ExtraTreeBasedSelector()
                output_node = transformer.operate(input_node)
                print('Shape ==>', input_node.shape, output_node.shape)
                self.graph.add_node(output_node)
                self.graph.add_trans_in_graph(input_node, output_node, transformer)

                _score = self.evaluator(output_node)

                if _score > self.incumbent_score:
                    self.incumbent_score = _score
                    self.incumbent = output_node
            except ValueError as e:
                print(transformer.name, str(e))
            except MemoryError as e:
                print(transformer.name, str(e))

        return self.incumbent
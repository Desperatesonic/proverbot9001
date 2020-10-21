#!/usr/bin/env python3.7
##########################################################################
#
#    This file is part of Proverbot9001.
#
#    Proverbot9001 is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Proverbot9001 is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Proverbot9001.  If not, see <https://www.gnu.org/licenses/>.
#
#    Copyright 2019 Alex Sanchez-Stern and Yousef Alhessi
#
##########################################################################

import argparse
import time
import math
import pickle
import sys
from typing import Dict, Any, List, Tuple, Iterable, cast, Union

from sklearn import svm

import torch
from torch import nn
from torch.autograd import Variable

from models.tactic_predictor import TacticPredictor, Prediction

from tokenizer import tokenizers
from data import get_text_data, encode_bag_classify_data, encode_bag_classify_input
from util import *
from format import TacticContext
from serapi_instance import get_stem

class WordBagSVMClassifier(TacticPredictor):
    def load_saved_state(self, filename : str) -> None:
        with open(filename, 'rb') as checkpoint_file:
            checkpoint = pickle.load(checkpoint_file)
        assert checkpoint['stem-embeddings']
        assert checkpoint['tokenizer']
        assert checkpoint['classifier']
        assert checkpoint['options']

        self.embedding = checkpoint['stem-embeddings']
        self.tokenizer = checkpoint['tokenizer']
        self.tokenizer.use_unknowns = False
        self.classifier = checkpoint['classifier']
        self.options = checkpoint['options']
        pass

    def getOptions(self) -> List[Tuple[str, str]]:
        return self.options

    def __init__(self, options : Dict[str, Any]) -> None:
        assert options["filename"]
        self.load_saved_state(options["filename"])
        self.criterion = nn.NLLLoss()

    def predictDistribution(self, in_data : TacticContext) \
        -> torch.FloatTensor:
        feature_vector = encode_bag_classify_input(in_data.goal, self.tokenizer)
        distribution = self.classifier.predict_log_proba([feature_vector])[0]
        return distribution

    def predictKTactics(self, in_data : TacticContext, k : int) \
        -> List[Prediction]:
        distribution = self.predictDistribution(in_data)
        indices, probabilities = list_topk(list(distribution), k)
        return [Prediction(self.embedding.decode_token(idx) + ".",
                           math.exp(certainty))
                for certainty, idx in zip(probabilities, indices)]

    def predictKTacticsWithLoss(self, in_data : TacticContext, k : int,
                                correct : str) -> Tuple[List[Prediction], float]:
        distribution = self.predictDistribution(in_data)
        correct_stem = get_stem(correct)
        if self.embedding.has_token(correct_stem):
            loss = self.criterion(torch.FloatTensor(distribution).view(1, -1), Variable(torch.LongTensor([self.embedding.encode_token(correct_stem)]))).item()
        else:
            loss = float("+inf")
        indices, probabilities = list_topk(list(distribution), k)
        predictions = [Prediction(self.embedding.decode_token(idx) + ".",
                                  math.exp(certainty))
                       for certainty, idx in zip(probabilities, indices)]
        return predictions, loss

Checkpoint = Tuple[svm.SVC, float]

def main(args_list : List[str]) -> None:
    parser = argparse.ArgumentParser(description=
                                     "A second-tier predictor which predicts tactic "
                                     "stems based on word frequency in the goal")
    parser.add_argument("--context-filter", dest="context_filter",
                        type=str, default="default")
    parser.add_argument("--num-keywords", dest="num_keywords",
                        type=int, default=100)
    parser.add_argument("--max-tuples", dest="max_tuples",
                        type=int, default=None)
    parser.add_argument("scrape_file")
    parser.add_argument("save_file")
    args = parser.parse_args(args_list)
    dataset = get_text_data(args)
    samples, tokenizer, embedding = encode_bag_classify_data(dataset,
                                                             tokenizers["no-fallback"],
                                                             args.num_keywords, 2)

    classifier, loss = train(samples, embedding.num_tokens())

    state = {'stem-embeddings': embedding,
             'tokenizer':tokenizer,
             'classifier': classifier,
             'options': [
                 ("dataset size", str(len(samples))),
                 ("context filter", args.context_filter),
                 ("training loss", loss),
                 ("# stems", embedding.num_tokens()),
                 ("# tokens", args.num_keywords),
             ]}
    with open(args.save_file, 'wb') as f:
        pickle.dump(state, f)

def train(dataset, num_stems: int) -> Checkpoint:
    curtime = time.time()
    print("Training SVM...", end="")
    sys.stdout.flush()

    inputs, outputs = zip(*dataset)
    model = svm.SVC(gamma='scale', probability=True)
    model.fit(inputs, outputs)
    print(" {:.2f}s".format(time.time() - curtime))
    loss = model.score(inputs, outputs)
    print("Training loss: {}".format(loss))
    return model, loss

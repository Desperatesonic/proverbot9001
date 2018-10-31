#!/usr/bin/env python3

from typing import Dict, Any, List

class SimpleEmbedding:
    def __init__(self) -> None:
        self.tokens_to_indices = {} #type: Dict[str, int]
        self.indices_to_tokens = {} #type: Dict[int, str]
    def encode_token(self, token : str) -> int :
        if token in self.tokens_to_indices:
            return self.tokens_to_indices[token]
        else:
            new_idx = len(self.tokens_to_indices)
            self.tokens_to_indices[token] = new_idx
            self.indices_to_tokens[new_idx] = token
            return new_idx

    def decode_token(self, idx : int) -> str:
        return self.indices_to_tokens[idx]
    def num_tokens(self) -> int:
        return len(self.indices_to_tokens)
    def has_token(self, token : str) -> bool :
        return token in self.tokens_to_indices

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
from util import *

class ClassifierDNN(nn.Module):
    def __init__(self, input_size : int, hidden_size : int, output_vocab_size : int,
                 num_layers : int, batch_size : int=1) -> None:
        super(ClassifierDNN, self).__init__()
        self.num_layers = num_layers
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.batch_size = batch_size
        self.in_layer = maybe_cuda(nn.Linear(input_size, hidden_size))
        self.layers = [maybe_cuda(nn.Linear(hidden_size, hidden_size))
                       for _ in range(1, num_layers)]
        self.out_layer = maybe_cuda(nn.Linear(hidden_size, output_vocab_size))
        self.softmax = maybe_cuda(nn.LogSoftmax(dim=1))
        pass

    def forward(self, input : torch.FloatTensor) -> torch.FloatTensor:
        layer_values = input.view(self.batch_size, -1)
        layer_values = self.in_layer(layer_values)
        for i in range(self.num_layers - 1):
            layer_values = F.relu(layer_values)
            layer_values = self.layers[i](layer_values)
        return self.softmax(self.out_layer(layer_values))

    def run(self, sentence : torch.FloatTensor) -> torch.FloatTensor:
        result = self(maybe_cuda(Variable(sentence)))
        return result

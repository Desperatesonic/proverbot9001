#!/usr/bin/env python3

from tokenizer import Tokenizer, TokenizerState, get_topk_keywords
from format import read_pair
from models.components import SimpleEmbedding
import re

from typing import Tuple, List, Callable

Sentence = List[int]
Bag = List[int]
RawDataset = List[Tuple[str, str]]
ClassifySequenceDataset = List[Tuple[Sentence, int]]
SequenceSequenceDataset = List[Tuple[Sentence, Sentence]]
ClassifyBagDataset = List[Tuple[Bag, int]]

def getTokenbagVector(goal : Sentence) -> Bag:
    tokenbag: List[int] = []
    for t in goal:
        if t >= len(tokenbag):
            wordbag = extend(tokenbag, t+1)
        wordbag[t] += 1
    return tokenbag

def extend(vector : List[int], length : int):
    assert len(vector) <= length
    return vector + [0] * (length - len(vector))

def read_text_data(data_path : str,  max_size:int=None) -> RawDataset:
    data_set = []
    with open(data_path, mode="r") as data_file:
        pair = read_pair(data_file)
        counter = 0
        while pair and (not max_size or counter < max_size):
            context, tactic = pair
            counter += 1
            data_set.append((context, tactic))
            pair = read_pair(data_file)
    assert len(data_set) > 0
    return data_set

def encode_seq_seq_data(data : RawDataset,
                        context_tokenizer_type : Callable[[List[str], int], Tokenizer],
                        tactic_tokenizer_type : Callable[[List[str], int], Tokenizer],
                        num_keywords : int,
                        num_reserved_tokens : int) \
    -> Tuple[SequenceSequenceDataset, Tokenizer, Tokenizer]:
    context_keywords = get_topk_keywords([context for context, tactic in data],
                                         num_keywords)
    tactic_keywords = get_topk_keywords([tactic for context, tactic in data],
                                        num_keywords)
    context_tokenizer = context_tokenizer_type(context_keywords, num_reserved_tokens)
    tactic_tokenizer = tactic_tokenizer_type(tactic_keywords, num_reserved_tokens)
    result = [(context_tokenizer.toTokenList(context),
               tactic_tokenizer.toTokenList(tactic))
              for context, tactic in data
              if (not re.match("[\{\}\+\-\*].*", tactic) and
                  not re.match(".*;.*", tactic))]
    context_tokenizer.freezeTokenList()
    tactic_tokenizer.freezeTokenList()
    return result, context_tokenizer, tactic_tokenizer

def encode_seq_classify_data(data : RawDataset,
                             tokenizer_type : Callable[[List[str], int], Tokenizer],
                             num_keywords : int,
                             num_reserved_tokens : int) \
    -> Tuple[ClassifySequenceDataset, Tokenizer, SimpleEmbedding]:
    embedding = SimpleEmbedding()
    keywords = get_topk_keywords([context for context, tactic in data], num_keywords)
    tokenizer = tokenizer_type(keywords, num_reserved_tokens)
    result = [(tokenizer.toTokenList(context), embedding.encode_token(tactic))
              for context, tactic in data
              if (not re.match("[\{\}\+\-\*].*", tactic) and
                  not re.match(".*;.*", tactic))]
    tokenizer.freezeTokenList()
    return result, tokenizer, embedding

def encode_bag_classify_data(data : RawDataset,
                             tokenizer_type : Callable[[List[str], int], Tokenizer],
                             num_keywords : int,
                             num_reserved_tokens : int) \
    -> Tuple[ClassifyBagDataset, Tokenizer, SimpleEmbedding]:
    seq_data, tokenizer, embedding = encode_seq_classify_data(data, tokenizer_type,
                                                              num_keywords,
                                                              num_reserved_tokens)
    return [(getTokenbagVector(context), tactic)
            for context, tactic in seq_data],\
        tokenizer, embedding

def encode_bag_classify_input(context : str, tokenizer : Tokenizer ):
    return extend(getTokenbagVector(tokenizer.toTokenList(context)), tokenizer.numTokens())
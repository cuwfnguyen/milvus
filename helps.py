from pyvi.ViTokenizer import tokenize
import re, os, string

def clean_text(text):
    text = re.sub('<.*?>', '', text).strip()
    text = re.sub('(\s)+', r'\1', text)
    return text

def word_segment(sent):
    sent = tokenize(sent.encode('utf-8').decode('utf-8'))
    return sent

def normalize_text(text):
    listpunctuation = string.punctuation.replace('_', '')
    for i in listpunctuation:
        text = text.replace(i, '')
    return text.lower()

def preprocess(text):
    text = clean_text(text)
    text = word_segment(text)
    text = normalize_text(text)
    return text

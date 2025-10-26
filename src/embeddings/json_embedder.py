import torch.nn.functional as F
import torch
import json
from torch import Tensor
from transformers import AutoTokenizer, AutoModel

MODEL = "intfloat/e5-base"
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModel.from_pretrained(MODEL)


def average_pool(last_hidden_states: Tensor,
                 attention_mask: Tensor) -> Tensor:
    # Mask out padding tokens and average all vectors 
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

def compute_embeddings(texts):

    # Tokenize the input texts
    texts = [f"passage: {text}" for text in texts]
    batch_dict = tokenizer(texts, max_length=512, padding=True, truncation=True, return_tensors='pt')

    with torch.inference_mode():
    # Get model outputs
        outputs = model(**batch_dict)
        embeddings = average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])

        # Normalize embeddings
        passage_embeddings = F.normalize(embeddings, p=2, dim=1)
    return passage_embeddings


def convert_embeddings_to_vectors(embeddings):
    return embeddings.detach().cpu().numpy().tolist()



        


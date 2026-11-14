"""Dense local model adapter; explicit failures and no mock fallback."""
import torch
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, name, revision, local_only=True):
        torch.manual_seed(42)
        torch.set_num_threads(4)
        self.model = SentenceTransformer(name, revision=revision, device="cpu", local_files_only=local_only)
        self.dimensions = self.model.get_embedding_dimension()

    def encode(self, texts):
        if not texts:
            return []
        lengths = [len(ids) for ids in self.model.tokenizer(texts, truncation=False)["input_ids"]]
        if max(lengths) > self.model.max_seq_length:
            raise ValueError("Input exceeds context; refusing silent truncation")
        # BGE-M3 needs no instruction prefix; query and document use identical dense encoding.
        return self.model.encode(texts, batch_size=8, normalize_embeddings=True,
                                 show_progress_bar=True).tolist()

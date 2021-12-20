from torch.utils.data import Dataset, DataLoader
from pathlib import Path
import numpy as np
import random
from symbols import tokenizer
class SynthesisDataset(Dataset):
    def __init__(self, data_root: Path, use_raw_embedding: bool = True):
        self.data_root = data_root
        self.use_raw_embedding = use_raw_embedding
        self.metafile = data_root.joinpath('_metafile.txt')
        if not self.metafile.exists():
            raise Exception("_metafile.txt not exists in %s" % data_root)
        self.metadata_cycler = RandomCycler(self._get_metadata(self.metafile))

    def _get_metadata(self, metafile: Path):
        with open(metafile, 'r') as f:
            metadata = [line.strip().split('|') for line in f]
        return metadata

    def __getitem__(self, item):
        return next(self.metadata_cycler)

    def __len__(self):
        return int(1e10)

class SynthesisDataLoader(DataLoader):
    def __init__(self, dataset: SynthesisDataset, batch_size, sampler=None,
                 batch_sampler=None, num_workers=0, pin_memory=False, timeout=0, worker_init_fn=None):
        self.data_root = dataset.data_root
        self.use_raw_embedding = dataset.use_raw_embedding
        super(SynthesisDataLoader, self).__init__(
            dataset=dataset,
            batch_size=batch_size,
            sampler=sampler,
            batch_sampler=batch_sampler,
            num_workers=num_workers,
            pin_memory=pin_memory,
            timeout=timeout,
            worker_init_fn=worker_init_fn,
            collate_fn=self.collate_fn
        )

    def collate_fn(self, batches):
        mel_fpath = [self.data_root.joinpath('mel', x[0]) for x in batches]
        if self.use_raw_embedding:
            embedding_fpath = [self.data_root.joinpath('embedding', x[4], x[2]) for x in batches]
        else:
            embedding_fpath = [random.sample(list(self.data_root.joinpath('embedding', x[4]).glob("*")), 1) for x in batches]

        text = [x[3] for x in batches]

        return SynthesisBatchData(mel_fpath, embedding_fpath, text)

class SynthesisBatchData:
    def __init__(self, mel_fpath, embedding_fpath, text):
        self.mel_data = np.array([np.load(mel) for mel in mel_fpath])
        self.embedding = np.array([np.load(embedding) for embedding in embedding_fpath])
        self.tokens = np.array([tokenizer(t) for t in text])

class RandomCycler:
    """
    无限循环随机序列生成器，对输入进来的list，进行打乱。
    抽过的item，只有在其他的所有的items都抽完之后，才再有可能抽到。
    """
    def __init__(self, source):

        if len(source) == 0:
            raise Exception("Can't create RandomCycler from an empty collection")

        self.all_item = list(source)
        self.next_item = []

    def sample(self, count: int):
        shuffle = lambda l: random.sample(l, len(l))
        samples = []

        while count > 0:
            if count > len(self.all_item):
                samples.extend(shuffle(list(self.all_item)))
                count -= len(self.all_item)
            n = min(count, len(self.next_item))
            samples.extend(self.next_item[:n])
            count -= n
            self.next_item = self.next_item[n:]
            if len(self.next_item) == 0:
                self.next_item = shuffle(list(self.all_item))

        return samples

    def __next__(self):
        return self.sample(1)[0]

if __name__ == '__main__':
    data_root = Path('./postdata/aidatatang_200zh')
    dataset = SynthesisDataset(data_root)
    dataloader = SynthesisDataLoader(dataset, 10)
    it = iter(dataloader)
    data =next(it)

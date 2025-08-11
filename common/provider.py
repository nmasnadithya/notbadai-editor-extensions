import re
import time
from typing import List, Optional, Dict, Any

from .api import File
from .completions import get_suggestions

MAX_PREDICTIONS = 8


class BaseModel:
    def __init__(self, **kwargs):
        ann = self.__class__.__annotations__

        for name, _ in ann.items():
            setattr(self, name, kwargs[name])

    def to_dict(self) -> Dict[str, Any]:
        return {name: getattr(self, name) for name in self.__class__.__annotations__}


class CompletionContext(BaseModel):
    cursor_pos: int
    line_number: int
    line_from: int
    current_content: str
    current_path: str

    @property
    def line_text(self):
        lines = self.current_content.splitlines()
        if len(lines) < self.line_number:
            return ''

        return lines[self.line_number - 1]


class Completion(BaseModel):
    text: str
    label: str


class CompletionResults(BaseModel):
    suggestions: List[str]


class Prediction(BaseModel):
    text: str
    log_prob: float


class AutoCompleteProvider:
    def __init__(self):
        self.predictions: List[Prediction] = []
        self.curr_line_number: int = -1
        self.last_fetched = None

    def _clear_cache(self):
        self.predictions = []

    @staticmethod
    def _filter_predictions(predictions: List[Prediction], line_prefix: str, line_text: str) -> List[Prediction]:
        line_text = line_text.strip()
        line_prefix = line_prefix.strip()

        seen: set[str] = set()

        res = []
        for pred in predictions:
            pred_text = pred.text.strip()
            if pred_text == line_text:
                continue

            if pred.text in seen:
                continue

            if not pred.text.startswith(line_prefix):
                continue

            seen.add(pred.text)
            res.append(pred)

        return res

    @staticmethod
    def _split_python_context(prefix: str) -> Dict[str, str]:
        pattern = r'([A-Za-z_][A-Za-z0-9_]*\s*|[A-Za-z_][A-Za-z0-9_]*\.)$'
        m = re.search(pattern, prefix)

        ctx = m.group(0) if m else ''
        rest = prefix[:-len(ctx)] if ctx else prefix

        return {"ctx": ctx, "rest": rest}

    def get_completions(self,
                        data: Dict[str, Any],
                        current_file: 'File',
                        open_files: Optional[List['File']] = None
                        ):
        cc = CompletionContext(**data)

        line_text = cc.line_text
        line_prefix = cc.current_content[cc.line_from: cc.cursor_pos].lstrip()

        if self.last_fetched is not None and time.time() - self.last_fetched < 0.2:
            return {'suggestions': [], 'time_elapsed': -1}

        self.last_fetched = time.time()

        ret = get_suggestions(
            offset=cc.cursor_pos,
            open_files=open_files,
            current_file=current_file,
        )

        if self.curr_line_number != cc.line_number:
            self._clear_cache()
        self.curr_line_number = cc.line_number

        for suggestion, log_prob in zip(ret['suggestions'], ret['log_probs']):
            self.predictions.append(Prediction(text=suggestion, log_prob=log_prob))

        self.predictions = self._filter_predictions(self.predictions, line_prefix, line_text)

        display_prefix = self._split_python_context(line_prefix)['ctx']

        options: List[Completion] = []
        for prediction in self.predictions:
            if prediction.text.startswith(line_prefix):
                suffix = prediction.text[len(line_prefix):]
            elif prediction.text.startswith(display_prefix):
                suffix = prediction.text[len(display_prefix):]
            else:
                suffix = prediction.text

            label = display_prefix + suffix
            if label.strip() == '':
                continue

            options.append(Completion(label=label, text=prediction.text))

        return {'suggestions': [option.to_dict() for option in options][:MAX_PREDICTIONS],
                'time_elapsed': ret['time_elapsed']
                }

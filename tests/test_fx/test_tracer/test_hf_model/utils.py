from numpy import isin
import torch
from colossalai.fx import ColoTracer
from torch.fx import GraphModule
from torch.utils._pytree import tree_flatten


def trace_model_and_compare_output(model, data_gen):
    tracer = ColoTracer()
    # make sure that the model is traceable
    try:
        kwargs = data_gen()
        meta_args = {k: v.to('meta') for k, v in kwargs.items()}
        graph = tracer.trace(root=model, meta_args=meta_args)
    except Exception as e:
        raise RuntimeError(f"Failed to trace {model.__class__.__name__}, error: {e}")
    gm = GraphModule(model, graph, model.__class__.__name__)
    gm.recompile()

    # check output
    inputs = data_gen()

    # must turn on eval mode to ensure the output is consistent
    gm.eval()
    model.eval()

    # run forward
    non_fx_out = model(**inputs)
    fx_out = gm(**inputs)

    for k in non_fx_out.keys():
        if torch.is_tensor(fx_out[k]):
            assert torch.equal(fx_out[k], non_fx_out[k]), f'{model.__class__.__name__} has incorrect output {k}'

import mxnet as mx

def try_gpu():
    try:
        ctx = mx.gpu()
        _ = mx.nd.zeros((1,), ctx=ctx)
    except mx.base.MXNetError:
        ctx = mx.cpu()
    return ctx

ctx = try_gpu()
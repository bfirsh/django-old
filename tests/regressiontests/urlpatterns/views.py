from django.http import HttpResponse, Http404

def callable_view(request):
    return HttpResponse('callable_view')

def string_view(request):
    return HttpResponse('string_view')

class OneTimeView(object):
    """
    A view that will 404 the second time it is called.
    """
    
    def __init__(self, *args, **kwargs):
        super(OneTimeView, self).__init__(*args, **kwargs)
        self.call_count = 0
    
    def __call__(self, request):
        if self.call_count > 0:
            raise Http404
        self.call_count += 1
        return HttpResponse(self.__class__.__name__)


class StringView(OneTimeView):
    pass

